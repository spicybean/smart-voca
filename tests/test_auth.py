#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 로그인, 계정별 기록 분리, 통계 공개 테스트 (VOCA-FR-041~043, 051~053, 이슈 #10·#11)
# 파일 위치: tests/test_auth.py

from app import exam_service, study_service
from app.models import User, db
from tests.conftest import sign_up


def test_signup_creates_hashed_password_and_logs_in(client):
    with client.application.app_context():
        user = db.session.scalar(db.select(User).where(User.username == "tester"))
        assert user is not None
        assert user.password_hash != "password123"
    assert client.get("/words").status_code == 200


def test_signup_rejects_short_password_and_duplicate_name(app):
    client = app.test_client()
    client.post("/signup", data={"username": "abc", "password": "short", "confirm": "short"})
    assert client.get("/words").status_code == 302

    sign_up(client, "dup")
    other = app.test_client()
    response = other.post("/signup", data={"username": "dup", "password": "password123", "confirm": "password123"},
                          follow_redirects=True)
    assert "이미 있는 아이디".encode() in response.data


def test_login_with_wrong_password_is_rejected(app):
    sign_up(app.test_client(), "alice")
    client = app.test_client()

    response = client.post("/login", data={"username": "alice", "password": "wrongpass"}, follow_redirects=True)

    assert "맞지 않습니다".encode() in response.data
    assert client.get("/words").status_code == 302


def test_logout_requires_post_and_ends_session(client):
    client.post("/logout")

    assert client.get("/words").status_code == 302


def test_pages_redirect_to_login_when_signed_out(app):
    client = app.test_client()

    assert client.get("/memorize").status_code == 302
    assert client.get("/stats").status_code == 302
    assert client.get("/").status_code == 200  # 처음 화면은 로그인 안내


def test_records_are_separated_per_account(app, seeded):
    alice = sign_up(app.test_client(), "alice")
    bob = sign_up(app.test_client(), "bobby")
    with app.app_context():
        study_service.set_daily_amount(5)
        from app.models import Word
        word_id = db.session.scalar(db.select(Word.id).order_by(Word.id))
        study_service.record_card(word_id, 1, "known", user_id=_user_id(app, "alice"))
        assert study_service.memorized_word_count(_user_id(app, "alice")) == 1
        assert study_service.memorized_word_count(_user_id(app, "bobby")) == 0
    assert alice.get("/stats").status_code == 200
    assert bob.get("/stats").status_code == 200


def _user_id(app, username):
    with app.app_context():
        return db.session.scalar(db.select(User.id).where(User.username == username))


def test_exam_session_belongs_to_its_owner(app, seeded):
    alice = sign_up(app.test_client(), "alice")
    bob = sign_up(app.test_client(), "bobby")
    response = alice.post("/exam/start", data={"count": "2", "direction": "en_ko", "formats": ["short"]})
    session_url = response.headers["Location"]

    assert alice.get(session_url).status_code == 200
    assert bob.get(session_url).status_code == 404


def test_private_stats_are_hidden_and_public_stats_are_read_only(app, seeded):
    alice = sign_up(app.test_client(), "alice")
    bob = sign_up(app.test_client(), "bobby")
    alice_id = _user_id(app, "alice")

    assert bob.get(f"/users/{alice_id}/stats").status_code == 404
    assert "공개 통계".encode() in bob.get("/users").data
    assert b"alice" not in bob.get("/users").data

    alice.post("/settings", data={"daily_amount": "20", "review_percent": "20", "exam_count": "10",
                                  "exam_direction": "en_ko", "exam_formats": ["short"], "stats_public": "1"})

    page = bob.get(f"/users/{alice_id}/stats")
    assert page.status_code == 200
    assert "alice 님의 학습 통계".encode() in page.data
    assert b"alice" in bob.get("/users").data
