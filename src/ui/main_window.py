#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 메인 창 (탭 4개, 고정 크기, 종료 훅) (UI 설계서 2.1절)
# 파일 위치: src/ui/main_window.py

"""메인 창. 탭 내용은 각 위젯이 만들고, 여기서는 배치와 종료 처리만 한다."""

from collections.abc import Callable

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from ui.styles import WINDOW_HEIGHT, WINDOW_WIDTH

TAB_TITLES = ("홈", "퀴즈", "단어", "설정")


class MainWindow(QMainWindow):
    def __init__(self, on_close: Callable[[], None] | None = None):
        super().__init__()
        self._on_close = on_close
        self.setWindowTitle("스마트보카")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

    def add_tab(self, title: str, widget: QWidget) -> None:
        if title not in TAB_TITLES:
            raise ValueError(f"알 수 없는 탭: {title}")
        self.tabs.addTab(widget, title)

    def closeEvent(self, event: QCloseEvent) -> None:
        # 종료 시 자동 백업과 퀴즈 세션 보존 (FR-1.8, FR-3.6)
        if self._on_close is not None:
            self._on_close()
        super().closeEvent(event)
