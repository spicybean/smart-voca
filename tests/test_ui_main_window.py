#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 메인 창과 공통 대화상자 스모크 테스트 (화면 없이 실행)
# 파일 위치: tests/test_ui_main_window.py

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402
from ui.styles import WINDOW_HEIGHT, WINDOW_WIDTH  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_window_is_fixed_size_with_title(qapp):
    window = MainWindow()

    assert window.windowTitle() == "스마트보카"
    assert window.width() == WINDOW_WIDTH and window.height() == WINDOW_HEIGHT
    assert window.minimumSize() == window.maximumSize()


def test_four_tabs_in_order(qapp):
    window = MainWindow()
    for title in ("홈", "퀴즈", "단어", "설정"):
        window.add_tab(title, QWidget())

    assert window.tab_titles() == ["홈", "퀴즈", "단어", "설정"]


def test_unknown_tab_is_rejected(qapp):
    window = MainWindow()

    with pytest.raises(ValueError):
        window.add_tab("기타", QWidget())


def test_close_calls_hook(qapp):
    calls = []
    window = MainWindow(on_close=lambda: calls.append("closed"))

    window.close()

    assert calls == ["closed"]
