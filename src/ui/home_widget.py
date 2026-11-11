#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 홈 화면 (학습 현황, 분야별 진도, 최근 활동, 빠른 이동) (UI 설계서 2.2절)
# 파일 위치: src/ui/home_widget.py

"""홈 대시보드. 수치는 Service에서 받아 표시만 한다."""

from datetime import date

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from models import CATEGORY_VALUES
from services import progress_service, quiz_service
from services.settings_service import get_settings
from utils import today_local

ALL_CATEGORY_VALUES = ("선택안함", "전체")


class HomeWidget(QWidget):
    start_quiz_requested = pyqtSignal()
    resume_quiz_requested = pyqtSignal()
    words_requested = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.total_bar = QProgressBar()
        self.total_bar.setRange(0, 100)
        self.count_label = QLabel()
        self.today_label = QLabel()
        self.empty_label = QLabel("단어를 추가해 주세요.")
        self.empty_label.setVisible(False)

        self.toggle_button = QToolButton()
        self.toggle_button.setText("분야별 진도 ▼")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.toggled.connect(self._set_category_visible)
        self.category_bars: dict[str, QProgressBar] = {}
        self.category_box = QWidget()
        category_layout = QVBoxLayout(self.category_box)
        for name in CATEGORY_VALUES:
            row = QHBoxLayout()
            row.addWidget(QLabel(name))
            bar = QProgressBar()
            bar.setRange(0, 100)
            row.addWidget(bar)
            category_layout.addLayout(row)
            self.category_bars[name] = bar

        self.recent_label = QLabel()
        self.quiz_button = QPushButton("퀴즈 시작하기")
        self.quiz_button.setObjectName("primary")
        self.quiz_button.clicked.connect(self._on_quiz_clicked)
        words_button = QPushButton("단어 관리")
        words_button.clicked.connect(self.words_requested)
        settings_button = QPushButton("설정")
        settings_button.clicked.connect(self.settings_requested)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("📊 학습 현황"))
        layout.addWidget(self.empty_label)
        layout.addWidget(self.total_bar)
        layout.addWidget(self.count_label)
        layout.addWidget(self.today_label)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.category_box)
        layout.addWidget(QLabel("🔥 최근 활동"))
        layout.addWidget(self.recent_label)
        buttons = QHBoxLayout()
        for button in (self.quiz_button, words_button, settings_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.refresh()

    def _set_category_visible(self, visible: bool) -> None:
        self.category_box.setVisible(visible)
        self.toggle_button.setText("분야별 진도 ▼" if visible else "분야별 진도 ▶")

    def _on_quiz_clicked(self) -> None:
        if quiz_service.resume_session() is not None:
            self.resume_quiz_requested.emit()
        else:
            self.start_quiz_requested.emit()

    def refresh(self, today: date | None = None) -> None:
        """DB 값을 다시 읽어 화면을 갱신한다. 퀴즈 후·설정 저장 후 호출한다."""
        today = today or today_local()
        settings = get_settings()
        category = None if settings.selected_category in ALL_CATEGORY_VALUES else settings.selected_category
        stats = progress_service.home_stats(category, today)
        per_category = progress_service.category_progress()
        session_view = quiz_service.resume_session()

        has_words = stats.total_words > 0
        self.empty_label.setVisible(not has_words)
        self.total_bar.setValue(int(round(stats.progress_rate)))
        self.total_bar.setVisible(has_words)
        self.count_label.setText(
            f"등록된 단어: {stats.total_words:,}개  |  학습 완료: {stats.mastered_count:,}개"
        )
        for name, bar in self.category_bars.items():
            bar.setValue(int(round(per_category[name].progress_rate)))

        if session_view is not None:
            self.today_label.setText(f"오늘 학습할 단어: {session_view.total_count}개 (진행 중)")
            self.recent_label.setText(
                f"어제 완료: {stats.yesterday_completed}문항\n"
                f"오늘 진행: {session_view.current_index}/{session_view.total_count} 진행 중"
            )
            self.quiz_button.setText("이어서 풀기")
        else:
            self.today_label.setText(f"오늘 학습할 단어: {settings.daily_count}개")
            self.recent_label.setText(
                f"어제 완료: {stats.yesterday_completed}문항\n"
                f"오늘 완료: {stats.today_completed}문항"
            )
            self.quiz_button.setText("퀴즈 시작하기")
