#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 보너스 문제 대상 선정
# 파일 위치: src/domain/bonus.py

"""보너스 문제 대상 선정. 요구사항 FR-3.4를 따른다.

자주 틀린 단어 조건을 쓰되, 오늘 기본 퀴즈에 나온 단어와 뜻이 같은 단어는 제외한다 (ADR-08).
"""

from datetime import date

from domain.quiz_builder import WordCandidate, list_frequently_wrong, pick_unique_by_meaning
from domain.rules import BONUS_MAX


def select_bonus(
    candidates: list[WordCandidate],
    exclude_ids: set[int],
    today: date,
    limit: int = BONUS_MAX,
) -> list[int]:
    """보너스 단어 id를 정답률 낮은 순 → 마지막 복습이 오래된 순으로 최대 limit개.

    오늘 기본 퀴즈에 나온 단어와, 그 단어와 뜻이 같은 단어는 제외한다 (ADR-08).
    조건을 만족하는 단어가 없으면 빈 목록을 돌려준다. 호출자는 이때 보너스 화면을 건너뛴다.
    """
    taken_meanings = frozenset(c.meaning for c in candidates if c.word_id in exclude_ids)
    not_excluded = [c for c in candidates if c.word_id not in exclude_ids]
    return pick_unique_by_meaning(list_frequently_wrong(not_excluded, today), limit, taken_meanings)
