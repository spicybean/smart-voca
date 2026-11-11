#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 퀴즈 구성(버킷·선정 순서·부족분) 단위 테스트
# 파일 위치: tests/test_quiz_builder.py

import random
from datetime import timedelta

import pytest

from domain.quiz_builder import (
    build_quiz_plan,
    plan_bucket_sizes,
    select_new_or_weak,
    select_review,
    select_wrong,
    split_quiz_types,
)


@pytest.mark.parametrize(
    "total, expected",
    [
        (10, (1, 2, 7)),
        (15, (1, 3, 11)),
        (30, (3, 6, 21)),
        (3, (0, 0, 3)),
        (0, (0, 0, 0)),
    ],
)
def test_bucket_sizes_use_floor_and_remainder(total, expected):
    sizes = plan_bucket_sizes(total)
    assert (sizes.wrong, sizes.review, sizes.new_or_weak) == expected


@pytest.mark.parametrize("total, expected", [(10, (5, 5)), (7, (3, 4)), (1, (0, 1))])
def test_quiz_types_put_extra_question_on_english_to_korean(total, expected):
    assert split_quiz_types(total) == expected


def test_select_wrong_takes_lowest_rate_first(make_candidate, today):
    old = today - timedelta(days=10)
    candidates = [
        make_candidate(1, attempts=5, correct_rate=50.0, last_reviewed=old),
        make_candidate(2, attempts=5, correct_rate=20.0, last_reviewed=old),
        make_candidate(3, attempts=5, correct_rate=10.0, last_reviewed=today - timedelta(days=1)),
    ]
    # 3번은 최근에 복습해서 제외, 2번(20%)이 1번(50%)보다 먼저
    assert select_wrong(candidates, limit=5, today=today) == [2, 1]


def test_select_review_includes_due_today_and_sorts_by_date(make_candidate, today):
    candidates = [
        make_candidate(1, attempts=2, correct_rate=80.0, next_review=today),
        make_candidate(2, attempts=2, correct_rate=80.0, next_review=today - timedelta(days=3)),
        make_candidate(3, attempts=2, correct_rate=80.0, next_review=today + timedelta(days=1)),
    ]
    assert select_review(candidates, limit=5, today=today) == [2, 1]


def test_select_new_or_weak_takes_unattempted_and_low_rate_only(make_candidate):
    candidates = [
        make_candidate(1, attempts=0),
        make_candidate(2, attempts=4, correct_rate=69.0),
        make_candidate(3, attempts=4, correct_rate=70.0),
        make_candidate(4, attempts=4, correct_rate=95.0),
    ]
    picked = select_new_or_weak(candidates, limit=10, rng=random.Random(1))
    assert sorted(picked) == [1, 2]


def test_build_plan_fills_each_bucket_when_enough_words(make_candidate, today):
    # N=10 → 자주 틀린 1, 복습 2, 신규·약한 7
    candidates = [
        make_candidate(1, attempts=5, correct_rate=10.0, last_reviewed=today - timedelta(days=20)),
        make_candidate(2, attempts=3, correct_rate=80.0, next_review=today - timedelta(days=1)),
        make_candidate(3, attempts=3, correct_rate=85.0, next_review=today),
    ]
    candidates += [make_candidate(100 + i, attempts=0) for i in range(10)]

    plan = build_quiz_plan(candidates, total=10, today=today, rng=random.Random(7))

    assert len(plan.word_ids) == 10
    assert len(set(plan.word_ids)) == 10
    assert plan.shortage == 0
    assert {1, 2, 3}.issubset(plan.word_ids)


def test_build_plan_reports_shortage_when_pool_is_small(make_candidate, today):
    candidates = [make_candidate(i, attempts=0) for i in range(4)]

    plan = build_quiz_plan(candidates, total=10, today=today, rng=random.Random(3))

    assert len(plan.word_ids) == 4
    assert plan.requested == 10
    assert plan.shortage == 6


def test_missing_wrong_bucket_is_filled_by_new_or_weak(make_candidate, today):
    # 자주 틀린 단어가 하나도 없으면 그 자리는 신규·약한 단어가 채운다
    weak_ids = list(range(1, 9))
    candidates = [make_candidate(i, attempts=0) for i in weak_ids]
    candidates += [make_candidate(50 + i, attempts=9, correct_rate=95.0) for i in range(5)]

    plan = build_quiz_plan(candidates, total=10, today=today, rng=random.Random(11))

    assert len(plan.word_ids) == 10
    assert set(weak_ids).issubset(plan.word_ids)


def test_missing_review_bucket_is_filled_by_new_or_weak(make_candidate, today):
    # 복습 대상이 1개뿐이면 나머지 자리도 신규·약한 단어가 채운다
    candidates = [make_candidate(1, attempts=3, correct_rate=80.0, next_review=today)]
    candidates += [make_candidate(10 + i, attempts=0) for i in range(9)]

    plan = build_quiz_plan(candidates, total=10, today=today, rng=random.Random(5))

    assert len(plan.word_ids) == 10
    assert 1 in plan.word_ids


def test_plan_is_reproducible_with_same_seed(make_candidate, today):
    candidates = [make_candidate(i, attempts=0) for i in range(30)]

    first = build_quiz_plan(candidates, total=10, today=today, rng=random.Random(42))
    second = build_quiz_plan(candidates, total=10, today=today, rng=random.Random(42))

    assert first.word_ids == second.word_ids


def test_plan_never_repeats_a_meaning(make_candidate, today):
    # 뜻이 같은 단어(hour, time 모두 '시간')는 한 퀴즈에 한 번만 나온다 (ADR-08)
    candidates = [
        make_candidate(1, meaning="시간"),
        make_candidate(2, meaning="시간"),
        make_candidate(3, meaning="바나나"),
    ]

    plan = build_quiz_plan(candidates, total=3, today=today, rng=random.Random(0))

    meanings = [c.meaning for c in candidates if c.word_id in plan.word_ids]
    assert len(meanings) == len(set(meanings)) == 2
    assert plan.shortage == 1


def test_wrong_bucket_skips_same_meaning_word(make_candidate, today):
    old = today - timedelta(days=10)
    candidates = [
        make_candidate(1, meaning="시간", attempts=5, correct_rate=10.0, last_reviewed=old),
        make_candidate(2, meaning="시간", attempts=5, correct_rate=20.0, last_reviewed=old),
        make_candidate(3, meaning="바나나", attempts=5, correct_rate=30.0, last_reviewed=old),
    ]

    assert select_wrong(candidates, limit=5, today=today) == [1, 3]
