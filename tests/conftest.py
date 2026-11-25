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
    application = create_app({"TESTING": True})
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


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
