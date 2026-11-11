#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 퀴즈 화면 흐름 테스트 (준비·진행·결과·이어 풀기, 화면 없이 실행)
# 파일 위치: tests/test_ui_quiz.py

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402

from services import quiz_service  # noqa: E402
from services.settings_service import save_settings  # noqa: E402
from services.word_service import add_word  # noqa: E402
from ui import message_boxes  # noqa: E402
from ui.quiz_widget import PAGE_PLAY, PAGE_PREP, PAGE_RESULT, PAGE_RESUME, QuizWidget  # noqa: E402

WORDS = [
    ("apple", "사과"), ("banana", "바나나"), ("cherry", "체리"),
    ("grape", "포도"), ("melon", "멜론"), ("peach", "복숭아"),
]


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def seed(daily: int) -> None:
    for english, korean in WORDS:
        add_word(english, korean, "일상", 1)
    save_settings("선택안함", daily)


def test_prep_shows_composition_for_daily_ten(db_engine, qapp):
    seed(daily=10)

    widget = QuizWidget()

    assert widget.stack.currentIndex() == PAGE_PREP
    assert "신규·약한 단어: 7개" in widget.prep_composition.text()
    assert "복습 대상: 2개" in widget.prep_composition.text()


def test_start_shows_question_with_four_options(db_engine, qapp):
    seed(daily=5)
    widget = QuizWidget()

    widget.prep_start.click()

    assert widget.stack.currentIndex() == PAGE_PLAY
    assert all(button.isEnabled() for button in widget.option_buttons)
    assert all(button.text() for button in widget.option_buttons)


def test_correct_answer_shows_feedback_and_enables_next(db_engine, qapp):
    seed(daily=5)
    widget = QuizWidget()
    widget.prep_start.click()
    view = quiz_service.resume_session()

    widget.option_buttons[view.items[0].answer_index].click()

    assert "정답입니다" in widget.play_result.text()
    assert widget.play_next.isEnabled()
    assert not any(button.isEnabled() for button in widget.option_buttons)


def test_wrong_answer_shows_correct_text(db_engine, qapp):
    seed(daily=5)
    widget = QuizWidget()
    widget.prep_start.click()
    view = quiz_service.resume_session()
    wrong = (view.items[0].answer_index + 1) % 4

    widget.option_buttons[wrong].click()

    assert "오답입니다" in widget.play_result.text()
    assert "정답:" in widget.play_result.text()


def test_full_round_reaches_result_page(db_engine, qapp):
    seed(daily=5)
    widget = QuizWidget()
    widget.prep_start.click()

    for _ in range(5):
        view = quiz_service.resume_session()
        widget.option_buttons[view.items[view.current_index].answer_index].click()
        widget.play_next.click()

    assert widget.stack.currentIndex() == PAGE_RESULT
    assert "정답: 5개" in widget.result_summary.text()
    assert quiz_service.resume_session() is None


def test_stop_returns_home_and_deletes_session(db_engine, qapp):
    seed(daily=5)
    widget = QuizWidget()
    widget.prep_start.click()
    fired = []
    widget.go_home_requested.connect(lambda: fired.append("home"))

    widget.play_stop.click()

    assert fired == ["home"]
    assert quiz_service.resume_session() is None


def test_saved_session_opens_resume_page(db_engine, qapp):
    seed(daily=5)
    QuizWidget().prep_start.click()
    view = quiz_service.resume_session()
    widget_answer = view.items[0].answer_index
    quiz_service.submit_answer(view.session_id, 0, widget_answer)

    widget = QuizWidget()

    assert widget.stack.currentIndex() == PAGE_RESUME
    assert "1/5" in widget.resume_info.text()
    quiz_service.stop_session()


def test_discard_asks_then_deletes_session(db_engine, qapp, monkeypatch):
    seed(daily=5)
    QuizWidget().prep_start.click()
    monkeypatch.setattr(message_boxes, "confirm_discard_session", lambda parent: True)
    widget = QuizWidget()

    widget._discard_quiz()

    assert quiz_service.resume_session() is None
    assert widget.stack.currentIndex() == PAGE_PREP


def seed_bonus_scenario(today):
    """기본 퀴즈 1문항이 약한 두 단어 중 하나를 고르고, 남은 하나가 보너스 대상이 되도록 준비한다."""
    from datetime import timedelta

    from sqlalchemy import select

    from database import session_scope
    from models import Progress, Word
    from services.progress_service import apply_result

    for english, korean in WORDS:
        add_word(english, korean, "일상", 1)
    save_settings("선택안함", 1)
    with session_scope() as session:
        for english in ("apple", "banana"):
            progress = session.scalars(
                select(Progress).join(Word, Word.id == Progress.word_id).where(Word.english == english)
            ).one()
            progress.correct_count = 0
            progress.wrong_count = 3
            progress.correct_rate = 0.0
            progress.last_reviewed_date = today - timedelta(days=10)
            progress.next_review_date = today - timedelta(days=10)
            progress.status = "복습필요"
        for english in ("cherry", "grape", "melon", "peach"):
            word = session.scalars(select(Word).where(Word.english == english)).one()
            for _ in range(5):
                apply_result(word.progress, True, today)


def test_bonus_offer_appears_after_basic_and_can_be_accepted(db_engine, qapp):
    from ui.quiz_widget import PAGE_BONUS
    from utils import today_local

    seed_bonus_scenario(today_local())
    widget = QuizWidget()
    widget.prep_start.click()
    view = quiz_service.resume_session()
    widget.option_buttons[view.items[0].answer_index].click()
    widget.play_next.click()

    assert widget.stack.currentIndex() == PAGE_BONUS
    assert "약한 단어 1개" in widget.bonus_message.text()

    widget.bonus_accept.click()

    assert widget.stack.currentIndex() == PAGE_PLAY
    assert "보너스" in widget.play_retry_badge.text()
    quiz_service.stop_session()


def test_bonus_skip_goes_to_result(db_engine, qapp):
    from ui.quiz_widget import PAGE_BONUS
    from utils import today_local

    seed_bonus_scenario(today_local())
    widget = QuizWidget()
    widget.prep_start.click()
    view = quiz_service.resume_session()
    widget.option_buttons[view.items[0].answer_index].click()
    widget.play_next.click()
    assert widget.stack.currentIndex() == PAGE_BONUS

    skip = [b for b in widget.findChildren(QPushButton) if b.text() == "건너뛰기"][0]
    skip.click()

    assert widget.stack.currentIndex() == PAGE_RESULT
    assert quiz_service.resume_session() is None


def test_no_bonus_targets_goes_straight_to_result(db_engine, qapp):
    seed(daily=5)
    widget = QuizWidget()
    widget.prep_start.click()
    for _ in range(5):
        view = quiz_service.resume_session()
        widget.option_buttons[view.items[view.current_index].answer_index].click()
        widget.play_next.click()

    assert widget.stack.currentIndex() == PAGE_RESULT
