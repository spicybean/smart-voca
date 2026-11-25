#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 테스트 공통 설정 (임시 SQLite DB 로 앱을 만든다)
# 파일 위치: tests/conftest.py

import pytest

from app import create_app
from app.models import db


@pytest.fixture
def app(tmp_path, monkeypatch):
    """테스트마다 새 임시 DB 를 쓴다. 실제 data/ 는 건드리지 않는다."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    # 화면 흐름 테스트는 CSRF를 끈다. CSRF 자체는 test_csrf.py 에서 켜서 확인한다.
    application = create_app({"TESTING": True, "CSRF_ENABLED": False, "SEED_WORDS": False})
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def sign_up(client, username="tester", password="password123"):
    """테스트 클라이언트를 새 계정으로 로그인시킨다 (CSRF는 이 fixture에서 꺼져 있음)."""
    client.post("/signup", data={"username": username, "password": password, "confirm": password})
    return client


@pytest.fixture
def client(app):
    return sign_up(app.test_client())


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


WORDS = [
    ("apple", "사과"),
    ("book", "책"),
    ("river", "강"),
    ("garden", "정원"),
    ("window", "창문"),
    ("pencil", "연필"),
]


@pytest.fixture
def seeded(ctx):
    """단어 6개를 미리 넣는다."""
    from app.word_service import add_word

    for english, meaning in WORDS:
        add_word(english, meaning)
    return [english for english, _ in WORDS]


def memorize_all(app, username="tester", day_no=1):
    """계정이 모든 단어를 '외웠어요'로 표시해 둔다 (시험은 외운 단어에서만 나온다)."""
    from app.models import User, Word
    from app.study_service import record_card

    with app.app_context():
        user_id = db.session.scalar(db.select(User.id).where(User.username == username)) or 1
        for word_id in db.session.scalars(db.select(Word.id)).all():
            record_card(word_id, day_no, "known", user_id=user_id)


@pytest.fixture
def memorized(app, seeded):
    """단어 6개를 모두 외운 상태 (기본 계정 또는 tester 계정)."""
    memorize_all(app)
    return seeded
