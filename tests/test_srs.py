#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 간격 반복·상태 판정 단위 테스트
# 파일 위치: tests/test_srs.py

from datetime import timedelta

import pytest

from domain.srs import (
    STATUS_LEARNING,
    STATUS_MASTERED,
    STATUS_NEW,
    STATUS_REVIEW_NEEDED,
    classify_status,
    compute_next_review,
    correct_rate,
    is_frequently_wrong,
    next_consecutive,
    next_interval_days,
)


@pytest.mark.parametrize(
    "consecutive, expected_days",
    [(1, 1), (2, 3), (3, 7), (4, 14), (5, 30), (9, 30)],
)
def test_correct_answer_interval_follows_streak(consecutive, expected_days):
    assert next_interval_days(consecutive, is_correct=True) == expected_days


def test_wrong_answer_interval_is_one_day_regardless_of_streak():
    assert next_interval_days(0, is_correct=False) == 1
    assert next_interval_days(4, is_correct=False) == 1


def test_correct_answer_requires_streak_of_at_least_one():
    with pytest.raises(ValueError):
        next_interval_days(0, is_correct=True)


def test_next_consecutive_increments_on_correct_and_resets_on_wrong():
    assert next_consecutive(2, is_correct=True) == 3
    assert next_consecutive(2, is_correct=False) == 0


def test_correct_rate_is_none_without_attempts():
    assert correct_rate(0, 0) is None


def test_correct_rate_is_percentage():
    assert correct_rate(3, 1) == pytest.approx(75.0)


def test_compute_next_review_adds_interval_days(today):
    assert compute_next_review(today, 7) == today + timedelta(days=7)


def test_status_is_new_when_never_attempted(today):
    status = classify_status(0, 0, False, None, today)
    assert status == STATUS_NEW


def test_status_mastered_wins_over_review_needed(today):
    # 연속 정답 5회 이상이면 마지막 결과가 오답이어도 숙달 (판정 순서 2번이 3번보다 먼저)
    status = classify_status(7, 5, True, today - timedelta(days=1), today)
    assert status == STATUS_MASTERED


def test_status_review_needed_when_last_result_wrong(today):
    status = classify_status(3, 0, True, today + timedelta(days=1), today)
    assert status == STATUS_REVIEW_NEEDED


def test_status_review_needed_when_review_date_is_overdue(today):
    status = classify_status(3, 2, False, today - timedelta(days=1), today)
    assert status == STATUS_REVIEW_NEEDED


def test_status_learning_when_review_is_due_today(today):
    # 예정일이 오늘이면 아직 '이전'이 아니므로 복습필요가 아니다
    status = classify_status(3, 2, False, today, today)
    assert status == STATUS_LEARNING


def test_status_learning_otherwise(today):
    status = classify_status(3, 2, False, today + timedelta(days=3), today)
    assert status == STATUS_LEARNING


def test_frequently_wrong_needs_low_rate_and_stale_review(today):
    assert is_frequently_wrong(59.0, today - timedelta(days=7), today) is True


def test_frequently_wrong_rate_boundary_is_exclusive(today):
    # 정답률 60%는 '60% 미만'이 아니므로 제외
    assert is_frequently_wrong(60.0, today - timedelta(days=30), today) is False


def test_frequently_wrong_review_must_be_seven_days_old(today):
    assert is_frequently_wrong(10.0, today - timedelta(days=6), today) is False


def test_frequently_wrong_is_false_without_attempts(today):
    assert is_frequently_wrong(None, None, today) is False

