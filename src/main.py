#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 앱 진입점 (DB 준비, 탭 연결, 종료 시 세션 보존과 자동 백업)
# 파일 위치: src/main.py

"""실행: python src/main.py (프로젝트 루트에서 venv 활성화 후)

시작 순서: 로깅 → 폴더 준비 → DB 준비(없으면 CSV로 생성) → 창 구성 → 실행.
종료 순서: 퀴즈 세션 보존(save_and_exit) → 자동 백업(auto_backup).
"""

import logging
import sys
from collections.abc import Callable

from PyQt6.QtWidgets import QApplication, QWidget

import config
from database import init_engine
from logger import LOGGER_NAME, setup_logging
from services import backup_service, quiz_service
from services.db_init import default_csv_paths, initialize_database, needs_initialization
from ui import message_boxes
from ui.home_widget import HomeWidget
from ui.main_window import MainWindow
from ui.quiz_widget import QuizWidget
from ui.settings_widget import SettingsWidget
from ui.styles import APP_STYLESHEET
from ui.word_widget import WordWidget

log = logging.getLogger(LOGGER_NAME)


def prepare_database() -> None:
    """폴더를 만들고, DB가 없거나 비어 있으면 CSV로 만든 뒤 연결한다."""
    config.ensure_runtime_dirs()
    db_path = config.get_db_path()
    if needs_initialization(db_path):
        log.info("DB가 없어 초기 데이터로 만듭니다")
        initialize_database(db_path, default_csv_paths())
    init_engine(db_path)


def close_app() -> None:
    """창을 닫을 때: 퀴즈 세션은 남기고, 학습 데이터는 자동 백업한다 (FR-1.8, FR-3.6)."""
    try:
        quiz_service.save_and_exit()
        backup_service.auto_backup()
    except Exception:
        log.exception("종료 처리 중 오류")


def create_main_window(on_close: Callable[[], None] | None = None) -> MainWindow:
    home = HomeWidget()
    quiz = QuizWidget()
    words = WordWidget()
    settings = SettingsWidget()
    window = MainWindow(on_close=on_close)
    window.add_tab("홈", home)
    window.add_tab("퀴즈", quiz)
    window.add_tab("단어", words)
    window.add_tab("설정", settings)

    def show_tab(widget: QWidget) -> None:
        window.tabs.setCurrentWidget(widget)

    def refresh_data_views() -> None:
        home.refresh()
        words.refresh()
        settings.load()

    home.start_quiz_requested.connect(lambda: (show_tab(quiz), quiz.refresh()))
    home.resume_quiz_requested.connect(lambda: (show_tab(quiz), quiz.refresh()))
    home.words_requested.connect(lambda: show_tab(words))
    home.settings_requested.connect(lambda: show_tab(settings))
    quiz.go_home_requested.connect(lambda: (home.refresh(), show_tab(home)))
    quiz.go_words_requested.connect(lambda: show_tab(words))
    settings.data_changed.connect(refresh_data_views)
    words.word_selected.connect(lambda _word_id: home.refresh())

    def on_tab_changed(index: int) -> None:
        widget = window.tabs.widget(index)
        if widget is home:
            home.refresh()
        elif widget is words:
            words.refresh()
        elif widget is settings:
            settings.load()

    window.tabs.currentChanged.connect(on_tab_changed)
    return window


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    try:
        prepare_database()
    except Exception:
        log.exception("DB 준비 실패")
        message_boxes.warn_database_error(None)
        return 1
    window = create_main_window(on_close=close_app)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
