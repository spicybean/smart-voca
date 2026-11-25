#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 첫 실행 시 설정 화면 우선 표시 테스트 (FR-2.1, UI 3.1)
# 파일 위치: tests/test_first_run_window.py
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

import main  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def tab_title_of_current(window) -> str:
    return window.tab_titles()[window.tabs.currentIndex()]


def test_first_run_opens_settings_tab(db_engine, qapp):
    window = main.create_main_window(first_run=True)

    assert tab_title_of_current(window) == "설정"


def test_normal_run_opens_home_tab(db_engine, qapp):
    window = main.create_main_window(first_run=False)

    assert tab_title_of_current(window) == "홈"


def test_saving_on_first_run_moves_to_home(db_engine, qapp):
    window = main.create_main_window(first_run=True)
    settings = window.tabs.widget(window.tab_titles().index("설정"))

    settings.save_button.click()

    assert tab_title_of_current(window) == "홈"
