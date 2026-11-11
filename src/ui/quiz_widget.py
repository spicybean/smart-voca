#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 퀴즈 화면 (준비, 진행, 결과, 이어서 풀기) (UI 설계서 2.3.1·2.3.2·2.3.4·2.3.5절)
# 파일 위치: src/ui/quiz_widget.py

"""퀴즈 탭. QStackedWidget으로 화면을 바꾼다. 채점과 저장은 quiz_service가 한다.

보너스 화면(2.3.3)은 다음 단계에서 추가한다. 지금은 기본 퀴즈가 끝나면 결과 화면으로 간다.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from domain.quiz_builder import plan_bucket_sizes
from services import progress_service, quiz_service
from services.quiz_service import (
    NoWordsError,
    QuizSessionExistsError,
    QuizSessionView,
)
from services.settings_service import get_settings
from ui import message_boxes
from ui.styles import DANGER, PRIMARY
from utils import today_local

PAGE_PREP, PAGE_RESUME, PAGE_PLAY, PAGE_RESULT = range(4)
ALL_CATEGORY_VALUES = ("선택안함", "전체")


class QuizWidget(QWidget):
    go_home_requested = pyqtSignal()
    go_words_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.stack = QStackedWidget()
        self._view: QuizSessionView | None = None
        self._last_finished = False

        self.prep_info = QLabel()
        self.prep_composition = QLabel()
        self.prep_notice = QLabel()
        self.prep_start = QPushButton("퀴즈 시작하기")
        self.prep_start.setObjectName("primary")
        self.prep_start.clicked.connect(self._start_quiz)
        self.stack.addWidget(self._build_prep_page())

        self.resume_info = QLabel()
        resume_button = QPushButton("이어서 풀기")
        resume_button.setObjectName("primary")
        resume_button.clicked.connect(self._resume_quiz)
        discard_button = QPushButton("세션 버리기")
        discard_button.setObjectName("danger")
        discard_button.clicked.connect(self._discard_quiz)
        self.stack.addWidget(self._build_resume_page(resume_button, discard_button))

        self.play_progress = QProgressBar()
        self.play_retry_badge = QLabel("다시 풀기 중 · 진도에 반영되지 않습니다")
        self.play_type = QLabel()
        self.play_question = QLabel()
        self.option_buttons: list[QPushButton] = []
        self.play_result = QLabel()
        self.play_next = QPushButton("다음 문제")
        self.play_next.setEnabled(False)
        self.play_next.clicked.connect(self._next_question)
        self.play_stop = QPushButton("그만하기")
        self.play_stop.setObjectName("danger")
        self.play_stop.clicked.connect(self._stop_quiz)
        self.stack.addWidget(self._build_play_page(self.play_stop))

        self.result_summary = QLabel()
        self.result_progress_label = QLabel()
        self.result_bar = QProgressBar()
        self.result_bar.setRange(0, 100)
        self.stack.addWidget(self._build_result_page())

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        self.refresh()

    # 화면 구성 -------------------------------------------------------

    def _build_prep_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("🎯 퀴즈 준비"))
        layout.addWidget(self.prep_info)
        layout.addWidget(self.prep_composition)
        layout.addWidget(self.prep_notice)
        buttons = QHBoxLayout()
        buttons.addWidget(self.prep_start)
        words = QPushButton("단어 관리")
        words.clicked.connect(self.go_words_requested)
        buttons.addWidget(words)
        layout.addLayout(buttons)
        return page

    def _build_resume_page(self, resume_button: QPushButton, discard_button: QPushButton) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("📝 이어서 풀기"))
        layout.addWidget(self.resume_info)
        buttons = QHBoxLayout()
        buttons.addWidget(resume_button)
        buttons.addWidget(discard_button)
        layout.addLayout(buttons)
        return page

    def _build_play_page(self, stop_button: QPushButton) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self.play_retry_badge)
        layout.addWidget(self.play_progress)
        layout.addWidget(self.play_type)
        layout.addWidget(self.play_question)
        for index in range(4):
            button = QPushButton()
            button.clicked.connect(lambda _checked=False, i=index: self._answer(i))
            self.option_buttons.append(button)
            layout.addWidget(button)
        layout.addWidget(self.play_result)
        buttons = QHBoxLayout()
        buttons.addWidget(self.play_next)
        buttons.addWidget(stop_button)
        layout.addLayout(buttons)
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("✓ 퀴즈 완료!"))
        layout.addWidget(self.result_summary)
        layout.addWidget(self.result_progress_label)
        layout.addWidget(self.result_bar)
        retry = QPushButton("다시 풀기")
        retry.clicked.connect(self._start_quiz)
        words = QPushButton("단어 관리")
        words.clicked.connect(self.go_words_requested)
        home = QPushButton("홈으로")
        home.clicked.connect(self.go_home_requested)
        buttons = QHBoxLayout()
        for button in (retry, words, home):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("※ 다시 풀기는 진도에 반영되지 않습니다"))
        return page

    # 화면 표시 -------------------------------------------------------

    def refresh(self) -> None:
        """저장된 세션을 확인해서 이어 풀기 화면이나 준비 화면을 보여준다 (2.3.1, 2.3.5)."""
        view = quiz_service.resume_session()
        if view is not None:
            self._view = view
            self.resume_info.setText(
                f"지난번 퀴즈가 {view.current_index}/{view.total_count} 문항에서 멈췄습니다."
            )
            self.stack.setCurrentIndex(PAGE_RESUME)
        else:
            self._show_prep()

    def _show_prep(self) -> None:
        settings = get_settings()
        self.prep_info.setText(
            f"분야: {settings.selected_category}\n일일 학습량: {settings.daily_count}개"
        )
        sizes = plan_bucket_sizes(settings.daily_count)
        self.prep_composition.setText(
            f"오늘 퀴즈 구성:\n• 신규·약한 단어: {sizes.new_or_weak}개\n"
            f"• 복습 대상: {sizes.review}개\n• 자주 틀린 단어: {sizes.wrong}개"
        )
        category = None if settings.selected_category in ALL_CATEGORY_VALUES else settings.selected_category
        availability = quiz_service.can_start_quiz(category)
        already_done = quiz_service.has_basic_answers_on(today_local())
        self.prep_start.setText("다시 풀기" if already_done else "퀴즈 시작하기")
        notices = []
        if already_done:
            notices.append("오늘 퀴즈는 완료했습니다. 다시 풀기는 진도에 반영되지 않습니다.")
        if availability.candidate_count < 4:
            notices.append("보기를 만들 단어가 부족합니다. 단어를 더 추가해 주세요.")
            self.prep_start.setEnabled(False)
        else:
            self.prep_start.setEnabled(True)
        self.prep_notice.setText("\n".join(notices))
        self.stack.setCurrentIndex(PAGE_PREP)

    def _show_question(self) -> None:
        view = quiz_service.resume_session()
        if view is None:
            self._show_prep()
            return
        if view.current_index >= view.total_count:
            self._show_result()
            return
        self._view = view
        self.play_retry_badge.setVisible(view.is_retry)
        self.play_progress.setRange(0, view.total_count)
        self.play_progress.setValue(view.current_index)
        item = view.items[view.current_index]
        self.play_type.setText(f"문제 {view.current_index + 1}: {item.quiz_type}")
        self.play_question.setText(f'"{item.question}"')
        for index, button in enumerate(self.option_buttons):
            button.setText(f"{index + 1}. {item.options[index]}")
            button.setEnabled(True)
            button.setStyleSheet("")
        self.play_result.setText("")
        last = view.current_index == view.total_count - 1
        self.play_next.setText("완료" if last else "다음 문제")
        self.play_next.setEnabled(False)
        self._last_finished = False
        self.stack.setCurrentIndex(PAGE_PLAY)

    def _show_result(self) -> None:
        summary = quiz_service.finish_session()
        percent = round(summary.correct_count / summary.answered_count * 100) if summary.answered_count else 0
        self.result_summary.setText(
            f"정답: {summary.correct_count}개 / 전체: {summary.answered_count}개\n정답률: {percent}%"
        )
        settings = get_settings()
        category = None if settings.selected_category in ALL_CATEGORY_VALUES else settings.selected_category
        stats = progress_service.home_stats(category, today_local())
        self.result_progress_label.setText(
            f"전체 진도 (학습 완료 단어): {stats.mastered_count:,}/{stats.total_words:,} ({round(stats.progress_rate)}%)"
        )
        self.result_bar.setValue(int(round(stats.progress_rate)))
        self.stack.setCurrentIndex(PAGE_RESULT)

    # 동작 -----------------------------------------------------------

    def _start_quiz(self) -> None:
        try:
            quiz_service.start_session()
        except QuizSessionExistsError:
            self.refresh()
            return
        except NoWordsError:
            message_boxes.warn_not_enough_words(self)
            self._show_prep()
            return
        self._show_question()

    def _resume_quiz(self) -> None:
        self._show_question()

    def _discard_quiz(self) -> None:
        if message_boxes.confirm_discard_session(self):
            quiz_service.discard_session()
            self.refresh()

    def _answer(self, index: int) -> None:
        if self._view is None or self._last_finished:
            return
        result = quiz_service.submit_answer(self._view.session_id, self._view.current_index, index)
        for button_index, button in enumerate(self.option_buttons):
            button.setEnabled(False)
            if button_index == result.correct_index:
                button.setStyleSheet(f"border: 2px solid {PRIMARY}; font-weight: bold;")
        if result.is_correct:
            self.play_result.setText("✓ 정답입니다!")
            self.play_result.setStyleSheet(f"color: {PRIMARY};")
        else:
            correct_text = self.option_buttons[result.correct_index].text()
            self.option_buttons[index].setStyleSheet(f"background: {DANGER}; color: white;")
            self.play_result.setText(f"✗ 오답입니다. 정답: {correct_text}")
            self.play_result.setStyleSheet(f"color: {DANGER};")
        self._last_finished = result.finished
        self.play_next.setEnabled(True)

    def _next_question(self) -> None:
        if self._last_finished:
            self._show_result()
        else:
            self._show_question()

    def _stop_quiz(self) -> None:
        quiz_service.stop_session()
        self.go_home_requested.emit()
