#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 간격 반복 계산, 상태 판정, 자주 틀린 단어 판정
# 파일 위치: src/domain/srs.py

"""간격 반복(SRS) 규칙. 요구사항 FR-4.0과 2.4절 판정 순서를 따른다."""

from datetime import date, timedelta

from domain.rules import (
    MASTERED_STREAK,
    REVIEW_INTERVALS,
    STALE_DAYS,
    WRONG_INTERVAL_DAYS,
    WRONG_RATE_THRESHOLD,
)

STATUS_NEW = "미학습"
STATUS_LEARNING = "학습중"
STATUS_REVIEW_NEEDED = "복습필요"
STATUS_MASTERED = "숙달"


def next_interval_days(consecutive_correct: int, is_correct: bool) -> int:
    """이번 답을 반영한 뒤 다음 복습까지의 간격(일)을 돌려준다.

    consecutive_correct는 이번 답을 반영한 뒤의 연속 정답 수다.
    오답이면 연속 정답 수와 무관하게 WRONG_INTERVAL_DAYS를 쓴다.
    """
    if not is_correct:
        return WRONG_INTERVAL_DAYS
    if consecutive_correct < 1:
        raise ValueError("정답 반영 후 연속 정답 수는 1 이상이어야 합니다.")
    longest_key = max(REVIEW_INTERVALS)
    return REVIEW_INTERVALS[min(consecutive_correct, longest_key)]


def next_consecutive(previous_consecutive: int, is_correct: bool) -> int:
    """정답이면 연속 정답 +1, 오답이면 0으로 되돌린다."""
    if is_correct:
        return previous_consecutive + 1
    return 0


def correct_rate(correct_count: int, wrong_count: int) -> float | None:
    """정답률(0~100). 시도 횟수가 0이면 None (화면에는 '-'로 표시)."""
    attempts = correct_count + wrong_count
    if attempts == 0:
        return None
    return correct_count / attempts * 100


def classify_status(
    attempts: int,
    consecutive: int,
    last_result_wrong: bool,
    next_review: date | None,
    today: date,
) -> str:
    """진도 값으로 상태를 정한다. 판정 순서는 2.4절과 같다."""
    if attempts == 0:
        return STATUS_NEW
    if consecutive >= MASTERED_STREAK:
        return STATUS_MASTERED
    review_overdue = next_review is not None and next_review < today
    if last_result_wrong or review_overdue:
        return STATUS_REVIEW_NEEDED
    return STATUS_LEARNING


def compute_next_review(today: date, interval_days: int) -> date:
    """복습 예정일 = 반영한 날짜 + 간격."""
    return today + timedelta(days=interval_days)


def is_frequently_wrong(
    correct_rate_value: float | None,
    last_reviewed: date | None,
    today: date,
) -> bool:
    """자주 틀린 단어 조건: 정답률 60% 미만 AND 마지막 복습이 7일 이상 전.

    시도 기록이 없으면(정답률 None, 마지막 복습 None) 해당하지 않는다.
    """
    if correct_rate_value is None or last_reviewed is None:
        return False
    days_since_review = (today - last_reviewed).days
    return correct_rate_value < WRONG_RATE_THRESHOLD and days_since_review >= STALE_DAYS
