#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 4지선다 보기 선정 단위 테스트
# 파일 위치: tests/test_distractors.py

import random

from domain.distractors import pick_distractors


def test_returns_three_distinct_meanings_without_answer(make_candidate):
    answer = make_candidate(1, meaning="사과", level=1)
    pool = [answer] + [make_candidate(i, meaning=f"뜻{i}", level=1) for i in range(2, 8)]

    options = pick_distractors(answer, pool, random.Random(0))

    assert options is not None
    assert len(options) == 3
    assert len(set(options)) == 3
    assert "사과" not in options


def test_prefers_same_category_and_level_within_one(make_candidate):
    answer = make_candidate(1, meaning="사과", category="일상", level=3)
    close = [
        make_candidate(2, meaning="배", category="일상", level=2),
        make_candidate(3, meaning="포도", category="일상", level=4),
        make_candidate(4, meaning="수박", category="일상", level=3),
    ]
    far = [make_candidate(10 + i, meaning=f"먼{i}", category="비즈니스", level=5) for i in range(5)]

    options = pick_distractors(answer, [answer] + close + far, random.Random(9))

    assert sorted(options) == ["배", "수박", "포도"]


def test_falls_back_to_same_category_when_level_is_far(make_candidate):
    answer = make_candidate(1, meaning="사과", category="일상", level=1)
    same_category_far_level = [
        make_candidate(2, meaning="배", category="일상", level=5),
        make_candidate(3, meaning="포도", category="일상", level=5),
        make_candidate(4, meaning="수박", category="일상", level=4),
    ]
    other_category = [make_candidate(9, meaning="회의", category="비즈니스", level=1)]

    options = pick_distractors(answer, [answer] + same_category_far_level + other_category, random.Random(2))

    assert sorted(options) == ["배", "수박", "포도"]


def test_skips_candidates_with_the_same_meaning_as_answer(make_candidate):
    answer = make_candidate(1, meaning="사과", level=1)
    duplicates = [make_candidate(2, meaning="사과", level=1), make_candidate(3, meaning="사과", level=1)]
    usable = [make_candidate(4, meaning="배"), make_candidate(5, meaning="포도"), make_candidate(6, meaning="수박")]

    options = pick_distractors(answer, [answer] + duplicates + usable, random.Random(4))

    assert sorted(options) == ["배", "수박", "포도"]


def test_returns_none_when_fewer_than_three_usable_meanings(make_candidate):
    answer = make_candidate(1, meaning="사과", level=1)
    pool = [answer, make_candidate(2, meaning="배"), make_candidate(3, meaning="사과")]

    assert pick_distractors(answer, pool, random.Random(0)) is None
