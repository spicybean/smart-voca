#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 앱 진입점 연결 테스트 (탭 구성, 화면 간 이동, DB 준비) (화면 없이 실행)
# 파일 위치: tests/test_main.py

import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

import config  # noqa: E402
import main  # noqa: E402
from services.settings_service import save_settings  # noqa: E402
from services.word_service import add_word  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_window_has_four_tabs_in_order(db_engine, qapp):
    window = main.create_main_window(on_close=lambda: None)

    assert window.tab_titles() == ["홈", "퀴즈", "단어", "설정"]


def test_home_start_button_switches_to_quiz_tab(db_engine, qapp):
    for english, korean in [("apple", "사과"), ("banana", "바나나"), ("cherry", "체리"), ("grape", "포도")]:
        add_word(english, korean, "일상", 1)
    save_settings("선택안함", 5)
    window = main.create_main_window(on_close=lambda: None)
    home = window.tabs.widget(0)

    home.quiz_button.click()

    assert window.tabs.currentIndex() == 1


def test_close_hook_is_called(db_engine, qapp):
    calls = []
    window = main.create_main_window(on_close=lambda: calls.append("closed"))

    window.close()

    assert calls == ["closed"]


def test_prepare_database_creates_db_when_missing(tmp_path, monkeypatch):
    from database import session_scope
    from models import Word
    from sqlalchemy import select

    db_path = tmp_path / "data" / "smart_voca.db"
    monkeypatch.setattr(config, "get_db_path", lambda: db_path)
    monkeypatch.setattr(config, "get_backup_dir", lambda: tmp_path / "backups")
    monkeypatch.setattr(config, "get_log_dir", lambda: tmp_path / "logs")
    seed = tmp_path / "seed.csv"
    with seed.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["english", "korean_meaning", "category", "level", "example_1", "example_2", "example_3"])
        writer.writerow(["apple", "사과", "일상", "1", "An apple.", "", ""])
    monkeypatch.setattr(main, "default_csv_paths", lambda: [seed])

    created = main.prepare_database()
    try:
        assert created is True
        with session_scope() as session:
            assert [w.english for w in session.scalars(select(Word)).all()] == ["apple"]
    finally:
        from database import get_engine
        get_engine().dispose()
    assert db_path.exists()
