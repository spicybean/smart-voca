#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - CSRF 토큰 검사 테스트 (이슈 #14)
# 파일 위치: tests/test_csrf.py

import re

import pytest

from app import create_app
from app.models import Word, db


@pytest.fixture
def secured(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "csrf.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    application = create_app({"TESTING": True, "CSRF_ENABLED": True})
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _token_from(client) -> str:
    html = client.get("/words").get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_post_without_token_is_rejected(secured):
    client = secured.test_client()

    response = client.post("/words", data={"english": "apple", "meaning": "사과"})

    assert response.status_code == 400
    with secured.app_context():
        assert db.session.scalar(db.select(Word).where(Word.english == "apple")) is None


def test_post_with_wrong_token_is_rejected(secured):
    client = secured.test_client()
    _token_from(client)

    response = client.post("/words", data={"english": "apple", "meaning": "사과", "csrf_token": "forged"})

    assert response.status_code == 400


def test_post_with_session_token_is_accepted(secured):
    client = secured.test_client()
    token = _token_from(client)

    response = client.post("/words", data={"english": "apple", "meaning": "사과", "csrf_token": token})

    assert response.status_code == 302
    with secured.app_context():
        assert db.session.scalar(db.select(Word).where(Word.english == "apple")) is not None


def test_every_form_carries_a_token_field(secured):
    """화면의 모든 form 은 csrf_token 필드를 가져야 한다."""
    from pathlib import Path

    templates = Path(__file__).resolve().parent.parent / "app" / "templates"
    for path in templates.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        forms = len(re.findall(r"<form\b", text))
        tokens = text.count('name="csrf_token"')
        assert tokens == forms, path.name
