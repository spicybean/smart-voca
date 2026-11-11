#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 홈 화면 표시와 버튼 동작 테스트 (화면 없이 실행)
# 파일 위치: tests/test_ui_home.py

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from services.settings_service import save_settings  # noqa: E402
from services.word_service import add_word  # noqa: E402
from ui.home_widget import HomeWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_empty_database_shows_add_words_hint(db_engine, qapp):
    home = HomeWidget()

    assert not home.empty_label.isHidden()
    assert home.empty_label.text() == "단어를 추가해 주세요."
    assert home.quiz_button.text() == "퀴즈 시작하기"


def test_counts_and_daily_target_are_shown(db_engine, qapp):
    add_word("apple", "사과", "일상")
    add_word("invoice", "청구서", "비즈니스")
    save_settings("선택안함", 15)

    home = HomeWidget()

    assert "등록된 단어: 2개" in home.count_label.text()
    assert "오늘 학습할 단어: 15개" in home.today_label.text()


def test_category_rows_exist_for_all_three_categories(db_engine, qapp):
    home = HomeWidget()

    assert set(home.category_bars) == {"일상", "비즈니스", "미분류"}


def test_quiz_button_emits_start_when_no_session(db_engine, qapp):
    home = HomeWidget()
    fired = []
    home.start_quiz_requested.connect(lambda: fired.append("start"))

    home.quiz_button.click()

    assert fired == ["start"]


def test_quiz_button_becomes_resume_when_session_exists(db_engine, qapp):
    from services import quiz_service

    add_word("apple", "사과", "일상")
    add_word("banana", "바나나", "일상")
    add_word("cherry", "체리", "일상")
    add_word("grape", "포도", "일상")
    add_word("melon", "멜론", "일상")
    save_settings("선택안함", 1)
    quiz_service.start_session()
    home = HomeWidget()
    home.refresh()
    fired = []
    home.resume_quiz_requested.connect(lambda: fired.append("resume"))

    assert home.quiz_button.text() == "이어서 풀기"
    home.quiz_button.click()
    assert fired == ["resume"]
    quiz_service.stop_session()
