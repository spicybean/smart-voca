#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 퀴즈 서비스 (세션 시작·답변·재개·보너스·그만하기) 통합 테스트
# 파일 위치: tests/test_quiz_service.py

import random
from datetime import timedelta

import pytest
from sqlalchemy import select

from database import session_scope
from models import Progress, Quiz, QuizSession, Word
from services import quiz_service
from services.progress_service import apply_result
from services.quiz_service import (
    QuizSessionExistsError,
    can_start_quiz,
    discard_session,
    finish_session,
    resume_session,
    save_and_exit,
    start_bonus,
    start_session,
    stop_session,
    submit_answer,
)
from services.settings_service import save_settings
from services.word_service import add_word, delete_word
from utils import today_local

WORDS = [
    ("apple", "사과"), ("banana", "바나나"), ("cherry", "체리"),
    ("grape", "포도"), ("melon", "멜론"), ("peach", "복숭아"),
]


def seed(words=WORDS, daily=5):
    ids = {}
    for english, korean in words:
        ids[english] = add_word(english, korean, "일상", 1).id
    save_settings("선택안함", daily)
    return ids


def quiz_row_count() -> int:
    with session_scope() as session:
        return len(session.scalars(select(Quiz.id)).all())


def progress_of(word_id: int) -> Progress:
    with session_scope() as session:
        progress = session.scalars(select(Progress).where(Progress.word_id == word_id)).one()
        return Progress(
            status=progress.status,
            correct_count=progress.correct_count,
            wrong_count=progress.wrong_count,
            consecutive_correct=progress.consecutive_correct,
        )


def answer_all_correctly(view):
    for item in view.items:
        submit_answer(1, item.index, item.answer_index)


def test_start_builds_items_with_four_options(db_engine):
    seed(daily=5)

    view = start_session(rng=random.Random(1))

    assert view.total_count == 5
    assert view.shortage == 0
    for item in view.items:
        assert len(item.options) == 4
        assert len(set(item.options)) == 4
        assert 0 <= item.answer_index < 4


def test_korean_to_english_options_are_english_words(db_engine):
    ids = seed(daily=5)

    view = start_session(rng=random.Random(2))

    with session_scope() as session:
        english_by_id = {w.id: w.english for w in session.scalars(select(Word)).all()}
    for item in view.items:
        if item.quiz_type == "한→영":
            assert item.options[item.answer_index] == english_by_id[item.word_id]
            assert all(option in english_by_id.values() for option in item.options)
    assert all(item.word_id in ids.values() for item in view.items)


def test_answer_records_quiz_and_updates_progress_on_first_session(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(3))
    first = view.items[0]

    result = submit_answer(1, 0, first.answer_index)

    assert result.is_correct is True
    assert result.finished is False
    assert progress_of(first.word_id).correct_count == 1
    assert quiz_row_count() == 1


def test_wrong_answer_is_recorded_as_wrong(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(4))
    first = view.items[0]
    wrong_choice = (first.answer_index + 1) % 4

    result = submit_answer(1, 0, wrong_choice)

    assert result.is_correct is False
    assert progress_of(first.word_id).wrong_count == 1


def test_cannot_answer_same_item_twice_or_out_of_order(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(5))
    submit_answer(1, 0, view.items[0].answer_index)

    with pytest.raises(ValueError):
        submit_answer(1, 0, 0)
    with pytest.raises(ValueError):
        submit_answer(1, 3, 0)


def test_second_start_while_session_exists_is_rejected(db_engine):
    seed(daily=5)
    start_session(rng=random.Random(6))

    with pytest.raises(QuizSessionExistsError):
        start_session(rng=random.Random(6))


def test_finishing_all_items_completes_basic_quiz(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(7))
    for item in view.items:
        result = submit_answer(1, item.index, item.answer_index)
    assert result.finished is True

    summary = finish_session()

    assert summary.answered_count == 5
    assert summary.correct_count == 5
    assert resume_session() is None


def test_same_day_second_session_is_retry_and_keeps_progress(db_engine):
    seed(daily=5)
    first = start_session(rng=random.Random(8))
    answer_all_correctly(first)
    finish_session()
    before = progress_of(first.items[0].word_id)

    retry = start_session(rng=random.Random(9))
    submit_answer(1, 0, retry.items[0].answer_index)

    assert retry.is_retry is True
    assert progress_of(retry.items[0].word_id).correct_count == before.correct_count


def test_resume_returns_same_items_and_position(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(10))
    submit_answer(1, 0, view.items[0].answer_index)
    submit_answer(1, 1, view.items[1].answer_index)

    resumed = resume_session()

    assert resumed is not None
    assert resumed.current_index == 2
    assert [item.word_id for item in resumed.items] == [item.word_id for item in view.items]
    assert resumed.items[0].selected_index == view.items[0].answer_index


def test_resume_drops_items_for_deleted_words(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(11))
    victim = view.items[-1].word_id
    delete_word(victim)

    resumed = resume_session()

    assert resumed.total_count == 4
    assert all(item.word_id != victim for item in resumed.items)


def test_stop_deletes_session_but_keeps_answers(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(12))
    submit_answer(1, 0, view.items[0].answer_index)

    stop_session()

    assert resume_session() is None
    assert quiz_row_count() == 1


def test_discard_is_same_as_stop(db_engine):
    seed(daily=5)
    start_session(rng=random.Random(13))

    discard_session()

    assert resume_session() is None


def test_app_exit_keeps_session_for_resume(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(14))
    submit_answer(1, 0, view.items[0].answer_index)

    save_and_exit()

    assert resume_session().current_index == 1


def test_bonus_targets_frequently_wrong_word_not_in_basic_quiz(db_engine):
    # 기본 퀴즈 1문항(daily=1)이 두 약한 단어 중 하나를 고르고, 남은 하나가 보너스 대상이 된다.
    today = today_local()
    ids = seed(WORDS, daily=1)
    weak_a, weak_b = ids["apple"], ids["banana"]
    with session_scope() as session:
        for word_id in (weak_a, weak_b):
            progress = session.scalars(select(Progress).where(Progress.word_id == word_id)).one()
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

    basic = start_session(rng=random.Random(15))
    basic_word = basic.items[0].word_id
    answer_all_correctly(basic)

    bonus = start_bonus(rng=random.Random(16))

    assert bonus is not None
    assert bonus.phase == "bonus"
    bonus_word = bonus.items[0].word_id
    assert {bonus_word, basic_word} == {weak_a, weak_b}
    before = progress_of(bonus_word)
    submit_answer(1, 0, bonus.items[0].answer_index)
    assert progress_of(bonus_word).correct_count == before.correct_count
    with session_scope() as session:
        bonus_quiz = session.scalars(select(Quiz).where(Quiz.word_id == bonus_word)).all()[-1]
        assert bonus_quiz.is_bonus is True


def test_bonus_is_none_when_nothing_qualifies(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(17))
    answer_all_correctly(view)

    assert start_bonus(rng=random.Random(18)) is None


def test_bonus_requires_basic_quiz_to_be_finished(db_engine):
    seed(daily=5)
    start_session(rng=random.Random(19))

    with pytest.raises(ValueError):
        start_bonus(rng=random.Random(19))


def test_can_start_quiz_reports_no_words_for_empty_category(db_engine):
    seed(daily=5)

    business = can_start_quiz("비즈니스")
    daily = can_start_quiz("일상")

    assert business.available is False
    assert business.candidate_count == 0
    assert daily.available is True
    assert daily.candidate_count == 6


def test_answer_for_deleted_current_word_is_skipped_without_quiz_row(db_engine):
    seed(daily=5)
    view = start_session(rng=random.Random(13))
    current = view.items[view.current_index]
    delete_word(current.word_id)
    rows_before = quiz_row_count()

    result = submit_answer(view.session_id, view.current_index, 0)

    assert result.skipped is True
    assert quiz_row_count() == rows_before
    resumed = resume_session()
    assert resumed.total_count == 4
    assert resumed.current_index == view.current_index
    assert all(item.word_id != current.word_id for item in resumed.items)
