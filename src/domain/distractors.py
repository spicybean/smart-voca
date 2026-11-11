#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 4지선다 보기(오답) 3개 선정
# 파일 위치: src/domain/distractors.py

"""4지선다 보기 선정. 요구사항 FR-3.1-E의 3단계 규칙을 따른다.

1) 같은 분야 + 난이도 ±1  2) 같은 분야  3) 전체 무작위
각 단계에서 정답과 같은 뜻, 이미 고른 뜻은 제외한다.
"""

import random

from domain.quiz_builder import WordCandidate
from domain.rules import DISTRACTOR_LEVEL_RANGE, MIN_OPTION_WORDS

DISTRACTOR_COUNT = MIN_OPTION_WORDS - 1


def pick_distractors(
    answer: WordCandidate,
    pool: list[WordCandidate],
    rng: random.Random,
) -> list[str] | None:
    """보기 오답 3개의 한글 뜻을 돌려준다. 후보가 모자라면 None.

    None이면 호출자(quiz_service)가 해당 문항을 오늘 퀴즈에서 제외한다.
    """
    others = [c for c in pool if c.word_id != answer.word_id and c.meaning != answer.meaning]

    same_category_and_level = [
        c for c in others
        if c.category == answer.category
        and abs(c.level - answer.level) <= DISTRACTOR_LEVEL_RANGE
    ]
    same_category = [c for c in others if c.category == answer.category]
    steps = [same_category_and_level, same_category, others]

    chosen_meanings: list[str] = []
    for step_candidates in steps:
        shuffled = list(step_candidates)
        rng.shuffle(shuffled)
        for candidate in shuffled:
            if candidate.meaning in chosen_meanings:
                continue
            chosen_meanings.append(candidate.meaning)
            if len(chosen_meanings) == DISTRACTOR_COUNT:
                return chosen_meanings
    return None
