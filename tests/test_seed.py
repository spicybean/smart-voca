#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 처음 실행 때 단어 CSV 자동 등록 테스트
# 파일 위치: tests/test_seed.py

from app import create_app
from app.models import db
from app.word_service import count_words, delete_word


def test_first_run_loads_sample_words_once(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "seed.db"))
    monkeypatch.setenv("SECRET_KEY", "x")
    app = create_app({"TESTING": True})
    with app.app_context():
        assert count_words() == 1999

        first_word = db.session.execute(db.text("SELECT english FROM word ORDER BY id LIMIT 1")).scalar()
        delete_word(db.session.execute(db.text("SELECT id FROM word ORDER BY id LIMIT 1")).scalar())
        db.engine.dispose()

    app_again = create_app({"TESTING": True})
    with app_again.app_context():
        assert count_words() == 1998  # 삭제한 단어는 다시 들어오지 않는다
        assert first_word is not None
        db.engine.dispose()
