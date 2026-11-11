#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 보너스 대상 선정 단위 테스트
# 파일 위치: tests/test_bonus.py

from datetime import timedelta

from domain.bonus import select_bonus


def test_selects_frequently_wrong_sorted_by_rate_then_oldest_review(make_candidate, today):
    old = today - timedelta(days=30)
    older = today - timedelta(days=60)
    candidates = [
        make_candidate(1, attempts=5, correct_rate=40.0, last_reviewed=old),
        make_candidate(2, attempts=5, correct_rate=20.0, last_reviewed=old),
        make_candidate(3, attempts=5, correct_rate=40.0, last_reviewed=older),
    ]

    assert select_bonus(candidates, exclude_ids=set(), today=today) == [2, 3, 1]


def test_excludes_words_already_in_basic_quiz(make_candidate, today):
    old = today - timedelta(days=30)
    candidates = [
        make_candidate(1, attempts=5, correct_rate=10.0, last_reviewed=old),
        make_candidate(2, attempts=5, correct_rate=20.0, last_reviewed=old),
    ]

    assert select_bonus(candidates, exclude_ids={1}, today=today) == [2]


def test_returns_at_most_bonus_max(make_candidate, today):
    old = today - timedelta(days=30)
    candidates = [
        make_candidate(i, attempts=5, correct_rate=float(i), last_reviewed=old)
        for i in range(1, 9)
    ]

    selected = select_bonus(candidates, exclude_ids=set(), today=today)

    assert len(selected) == 5
    assert selected == [1, 2, 3, 4, 5]


def test_returns_empty_list_when_no_word_qualifies(make_candidate, today):
    candidates = [
        make_candidate(1, attempts=5, correct_rate=80.0, last_reviewed=today - timedelta(days=30)),
        make_candidate(2, attempts=5, correct_rate=10.0, last_reviewed=today - timedelta(days=3)),
        make_candidate(3, attempts=0),
    ]

    assert select_bonus(candidates, exclude_ids=set(), today=today) == []


def test_accepts_fewer_than_max_when_only_one_qualifies(make_candidate, today):
    candidates = [make_candidate(7, attempts=5, correct_rate=30.0, last_reviewed=today - timedelta(days=8))]

    assert select_bonus(candidates, exclude_ids=set(), today=today) == [7]


def test_bonus_skips_words_sharing_meaning_with_basic_quiz(make_candidate, today):
    # 기본 퀴즈에 1번(시간)이 나왔다면, 같은 뜻인 2번은 보너스에서도 뺀다 (ADR-08)
    old = today - timedelta(days=30)
    candidates = [
        make_candidate(1, meaning="시간", attempts=5, correct_rate=10.0, last_reviewed=old),
        make_candidate(2, meaning="시간", attempts=5, correct_rate=20.0, last_reviewed=old),
        make_candidate(3, meaning="바나나", attempts=5, correct_rate=30.0, last_reviewed=old),
    ]

    assert select_bonus(candidates, exclude_ids={1}, today=today) == [3]
