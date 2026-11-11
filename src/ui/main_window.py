#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 메인 창 (왼쪽 사이드바 + 화면 전환, 고정 크기, 종료 훅) (UI 설계서 v1.5 2.1절)
# 파일 위치: src/ui/main_window.py

"""메인 창. 왼쪽 메뉴에서 화면을 고르고, 오른쪽에 선택한 화면을 보여 준다."""

from collections.abc import Callable

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QWidget

from ui.styles import SIDEBAR_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH

TAB_TITLES = ("홈", "퀴즈", "단어", "설정")


class MainWindow(QMainWindow):
    def __init__(self, on_close: Callable[[], None] | None = None):
        super().__init__()
        self._on_close = on_close
        self._titles: list[str] = []
        self.setWindowTitle("스마트보카")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.nav = QListWidget()
        self.nav.setObjectName("sidebar")
        self.nav.setFixedWidth(SIDEBAR_WIDTH)
        self.tabs = QStackedWidget()
        self.nav.currentRowChanged.connect(self._on_nav_changed)
        self.tabs.currentChanged.connect(self._sync_nav)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

    def add_tab(self, title: str, widget: QWidget) -> None:
        if title not in TAB_TITLES:
            raise ValueError(f"알 수 없는 탭: {title}")
        self._titles.append(title)
        self.tabs.addWidget(widget)
        self.nav.addItem(title)
        if self.tabs.count() == 1:
            self.nav.setCurrentRow(0)

    def tab_titles(self) -> list[str]:
        return list(self._titles)

    def _on_nav_changed(self, row: int) -> None:
        if 0 <= row < self.tabs.count():
            self.tabs.setCurrentIndex(row)

    def _sync_nav(self, index: int) -> None:
        self.nav.blockSignals(True)
        self.nav.setCurrentRow(index)
        self.nav.blockSignals(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        # 종료 시 자동 백업과 퀴즈 세션 보존 (FR-1.8, FR-3.6)
        if self._on_close is not None:
            self._on_close()
        super().closeEvent(event)
