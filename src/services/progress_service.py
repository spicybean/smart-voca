#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 진도 반영, 홈 화면 통계 (FR-4.1, FR-3.3-A 반영 규칙)
# 파일 위치: src/services/progress_service.py

"""진도 계산과 통계. 설계서 4.11절 기준.

apply_result는 Progress 객체 하나를 바꾸는 순수 갱신 함수다.
같은 날 첫 세션 판정 등 '언제 반영할지'는 quiz_service가 정한다 (FR-3.3-A).
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select

from database import session_scope
from domain.srs import (
    STATUS_MASTERED,
    classify_status,
    compute_next_review,
    correct_rate,
    next_consecutive,
    next_interval_days,
)
from models import CATEGORY_VALUES, Progress, Quiz, Word


@dataclass(frozen=True)
class HomeStats:
    total_words: int
    mastered_count: int
    progress_rate: float
    yesterday_completed: int
    today_completed: int


@dataclass(frozen=True)
class CategoryProgress:
    total_words: int
    mastered_count: int
    progress_rate: float


def apply_result(progress: Progress, is_correct: bool, today: date) -> None:
    """정답·오답을 Progress에 반영하고 간격과 상태를 다시 계산한다 (FR-3.3, FR-4.0)."""
    if is_correct:
        progress.correct_count += 1
    else:
        progress.wrong_count += 1
    progress.consecutive_correct = next_consecutive(progress.consecutive_correct, is_correct)
    progress.last_reviewed_date = today
    progress.correct_rate = correct_rate(progress.correct_count, progress.wrong_count)

    interval_days = next_interval_days(progress.consecutive_correct, is_correct)
    progress.next_review_date = compute_next_review(today, interval_days)

    attempts = progress.correct_count + progress.wrong_count
    progress.status = classify_status(
        attempts=attempts,
        consecutive=progress.consecutive_correct,
        last_result_wrong=not is_correct,
        next_review=progress.next_review_date,
        today=today,
    )
    progress.updated_date = datetime.now()


def _rate(mastered: int, total: int) -> float:
    return mastered / total * 100 if total else 0.0


def _category_condition(category: str | None):
    return None if category is None else Word.category == category


def _count_words(session, category: str | None) -> int:
    statement = select(func.count(Word.id))
    condition = _category_condition(category)
    if condition is not None:
        statement = statement.where(condition)
    return session.scalar(statement) or 0


def _count_mastered(session, category: str | None) -> int:
    statement = (
        select(func.count(Progress.id))
        .join(Word, Word.id == Progress.word_id)
        .where(Progress.status == STATUS_MASTERED)
    )
    condition = _category_condition(category)
    if condition is not None:
        statement = statement.where(condition)
    return session.scalar(statement) or 0


def _count_base_answers(session, day: date, category: str | None) -> int:
    """하루치 기본 퀴즈 답변 수. 보너스와 재풀이 기록은 세지 않는다 (데이터 설계서 2.4)."""
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    statement = (
        select(func.count(Quiz.id))
        .join(Word, Word.id == Quiz.word_id)
        .where(
            Quiz.created_date >= start,
            Quiz.created_date < end,
            Quiz.is_bonus == False,  # noqa: E712 (SQLAlchemy 비교 연산자)
            Quiz.is_retry == False,  # noqa: E712
        )
    )
    condition = _category_condition(category)
    if condition is not None:
        statement = statement.where(condition)
    return session.scalar(statement) or 0


def home_stats(category: str | None, today: date) -> HomeStats:
    """홈 화면 수치. category가 None이면 전체 (FR-4.1)."""
    with session_scope() as session:
        total = _count_words(session, category)
        mastered = _count_mastered(session, category)
        return HomeStats(
            total_words=total,
            mastered_count=mastered,
            progress_rate=_rate(mastered, total),
            yesterday_completed=_count_base_answers(session, today - timedelta(days=1), category),
            today_completed=_count_base_answers(session, today, category),
        )


def category_progress() -> dict[str, CategoryProgress]:
    """분야별 진도율 (일상·비즈니스·미분류)."""
    result: dict[str, CategoryProgress] = {}
    with session_scope() as session:
        for category in CATEGORY_VALUES:
            total = _count_words(session, category)
            mastered = _count_mastered(session, category)
            result[category] = CategoryProgress(
                total_words=total,
                mastered_count=mastered,
                progress_rate=_rate(mastered, total),
            )
    return result
