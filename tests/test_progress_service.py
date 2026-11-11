#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 진도 반영과 홈 통계 테스트
# 파일 위치: tests/test_progress_service.py

from datetime import datetime, time, timedelta

import pytest

from database import session_scope
from models import Progress, Quiz, Word
from services.progress_service import apply_result, category_progress, home_stats
from services.word_service import add_word


def fresh_progress() -> Progress:
    return Progress(status="미학습", correct_count=0, wrong_count=0, consecutive_correct=0)


def test_first_correct_answer_sets_one_day_interval(today):
    progress = fresh_progress()

    apply_result(progress, True, today)

    assert progress.correct_count == 1
    assert progress.consecutive_correct == 1
    assert progress.correct_rate == pytest.approx(100.0)
    assert progress.next_review_date == today + timedelta(days=1)
    assert progress.last_reviewed_date == today
    assert progress.status == "학습중"


def test_wrong_answer_resets_streak_and_needs_review(today):
    progress = fresh_progress()
    apply_result(progress, True, today)
    apply_result(progress, True, today)

    apply_result(progress, False, today)

    assert progress.consecutive_correct == 0
    assert progress.wrong_count == 1
    assert progress.next_review_date == today + timedelta(days=1)
    assert progress.status == "복습필요"


def test_five_correct_answers_in_a_row_master_the_word(today):
    progress = fresh_progress()
    for _ in range(5):
        apply_result(progress, True, today)

    assert progress.consecutive_correct == 5
    assert progress.status == "숙달"
    assert progress.next_review_date == today + timedelta(days=30)


def test_correct_rate_uses_all_attempts(today):
    progress = fresh_progress()
    for is_correct in (True, True, True, False):
        apply_result(progress, is_correct, today)

    assert progress.correct_rate == pytest.approx(75.0)


def test_home_stats_counts_mastered_and_rate(db_engine, today):
    add_word("apple", "사과", "일상")
    add_word("banana", "바나나", "일상")
    add_word("invoice", "청구서", "비즈니스")
    with session_scope() as session:
        apple = session.query(Word).filter(Word.english == "apple").one()
        for _ in range(5):
            apply_result(apple.progress, True, today)

    everything = home_stats(None, today)
    daily_only = home_stats("일상", today)

    assert everything.total_words == 3
    assert everything.mastered_count == 1
    assert everything.progress_rate == pytest.approx(100 / 3)
    assert daily_only.total_words == 2
    assert daily_only.progress_rate == pytest.approx(50.0)


def test_home_stats_excludes_bonus_and_retry_answers_from_counts(db_engine, today):
    word = add_word("apple", "사과", "일상")
    yesterday_noon = datetime.combine(today - timedelta(days=1), time(12))
    today_noon = datetime.combine(today, time(12))
    with session_scope() as session:
        session.add_all([
            Quiz(word_id=word.id, quiz_type="한→영", is_correct=True, created_date=yesterday_noon),
            Quiz(word_id=word.id, quiz_type="영→한", is_correct=False, created_date=today_noon),
            Quiz(word_id=word.id, quiz_type="한→영", is_correct=True, is_bonus=True, created_date=today_noon),
            Quiz(word_id=word.id, quiz_type="한→영", is_correct=True, is_retry=True, created_date=today_noon),
        ])

    stats = home_stats(None, today)

    assert stats.yesterday_completed == 1
    assert stats.today_completed == 1


def test_category_progress_lists_all_three_categories(db_engine):
    add_word("apple", "사과", "일상")

    result = category_progress()

    assert set(result) == {"일상", "비즈니스", "미분류"}
    assert result["일상"].total_words == 1
    assert result["비즈니스"].total_words == 0
    assert result["비즈니스"].progress_rate == 0.0
