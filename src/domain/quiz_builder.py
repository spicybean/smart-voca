#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 오늘의 퀴즈 구성 (버킷 개수, 선정 순서, 부족분 보충)
# 파일 위치: src/domain/quiz_builder.py

"""오늘의 퀴즈 단어 선정. 요구사항 FR-3.1-A~D를 따른다.

입력은 WordCandidate 목록이고, DB 모델을 직접 받지 않는다.
rng는 random.Random 인스턴스이며 테스트에서 시드를 고정해 결과를 검증한다.
"""

import math
import random
from dataclasses import dataclass
from datetime import date

from domain.rules import RATIO_REVIEW, RATIO_WRONG
from domain.srs import STATUS_LEARNING, STATUS_NEW, is_frequently_wrong


@dataclass(frozen=True)
class WordCandidate:
    """퀴즈 선정에 필요한 단어 정보. DB 모델 대신 이 값 객체를 넘긴다."""

    word_id: int
    meaning: str
    level: int
    category: str
    attempts: int
    correct_rate: float | None
    last_reviewed: date | None
    next_review: date | None
    english: str = ""
    # 학습 상태(미학습·학습중·복습필요·숙달). 신규·약한 단어 판정에 쓴다 (FR-3.1-A)
    status: str = STATUS_NEW


@dataclass(frozen=True)
class BucketPlan:
    """버킷별 목표 개수."""

    wrong: int
    review: int
    new_or_weak: int


@dataclass(frozen=True)
class QuizPlan:
    """선정 결과. word_ids는 문항 순서(무작위)대로 정렬되어 있다."""

    word_ids: list[int]
    requested: int

    @property
    def shortage(self) -> int:
        """요청 문항 수보다 모자란 개수. 0이면 정상."""
        return self.requested - len(self.word_ids)


def _floor_ratio(total: int, ratio: float) -> int:
    # 0.1 * 30 같은 부동소수점 오차로 내림 결과가 틀어지지 않도록 반올림 후 내림한다.
    return math.floor(round(total * ratio, 9))


def plan_bucket_sizes(total: int) -> BucketPlan:
    """FR-3.1-B 순서로 버킷 개수를 정한다: 자주 틀린 → 복습 → 나머지(신규·약한)."""
    wrong = _floor_ratio(total, RATIO_WRONG)
    review = _floor_ratio(total, RATIO_REVIEW)
    return BucketPlan(wrong=wrong, review=review, new_or_weak=total - wrong - review)


def split_quiz_types(total: int) -> tuple[int, int]:
    """(한→영 개수, 영→한 개수). 홀수면 영→한이 1개 많다 (FR-3.2)."""
    korean_to_english = total // 2
    return korean_to_english, total - korean_to_english


def pick_unique_by_meaning(
    ordered: list[WordCandidate], limit: int, taken_meanings: frozenset[str] = frozenset()
) -> list[int]:
    """앞에서부터 보며 뜻이 겹치지 않는 단어를 limit개 고른다 (ADR-08 동의어 중복 방지).

    taken_meanings에 있는 뜻과 이미 고른 뜻은 건너뛴다.
    """
    seen = set(taken_meanings)
    picked: list[int] = []
    for candidate in ordered:
        if len(picked) >= limit:
            break
        if candidate.meaning in seen:
            continue
        seen.add(candidate.meaning)
        picked.append(candidate.word_id)
    return picked


def list_frequently_wrong(candidates: list[WordCandidate], today: date) -> list[WordCandidate]:
    """자주 틀린 단어를 정답률 낮은 순, 같으면 마지막 복습이 오래된 순으로 정렬해 돌려준다."""
    eligible = [c for c in candidates if is_frequently_wrong(c.correct_rate, c.last_reviewed, today)]
    return sorted(eligible, key=lambda c: (c.correct_rate, c.last_reviewed))


def select_wrong(
    candidates: list[WordCandidate],
    limit: int,
    today: date,
    taken_meanings: frozenset[str] = frozenset(),
) -> list[int]:
    """자주 틀린 단어 버킷. 정답률 오름차순으로 limit개 (뜻 중복 제외)."""
    return pick_unique_by_meaning(list_frequently_wrong(candidates, today), limit, taken_meanings)


def select_review(
    candidates: list[WordCandidate],
    limit: int,
    today: date,
    taken_meanings: frozenset[str] = frozenset(),
) -> list[int]:
    """복습 대상 버킷. 복습 예정일이 오늘 이하인 단어를 예정일 오름차순으로 limit개 (뜻 중복 제외)."""
    due = [c for c in candidates if c.next_review is not None and c.next_review <= today]
    due.sort(key=lambda c: c.next_review)
    return pick_unique_by_meaning(due, limit, taken_meanings)


def is_new_or_weak(candidate: WordCandidate) -> bool:
    """신규·약한 단어: 학습 상태가 미학습 또는 학습중인 단어 (FR-3.1-A)."""
    return candidate.status in (STATUS_NEW, STATUS_LEARNING)


def select_new_or_weak(
    candidates: list[WordCandidate],
    limit: int,
    rng: random.Random,
    taken_meanings: frozenset[str] = frozenset(),
) -> list[int]:
    """신규·약한 단어 버킷. 대상 중 무작위 순서로 뽑되 뜻이 겹치지 않게 limit개."""
    eligible = [c for c in candidates if is_new_or_weak(c)]
    shuffled = rng.sample(eligible, len(eligible))
    return pick_unique_by_meaning(shuffled, limit, taken_meanings)


def fill_shortfall(
    candidates: list[WordCandidate],
    excluded_ids: set[int],
    need: int,
    rng: random.Random,
    taken_meanings: frozenset[str] = frozenset(),
) -> list[int]:
    """부족분을 아직 뽑히지 않은 나머지(숙달 상태 포함)에서 무작위로 채운다 (뜻 중복 제외)."""
    remaining = [c for c in candidates if c.word_id not in excluded_ids]
    shuffled = rng.sample(remaining, len(remaining))
    return pick_unique_by_meaning(shuffled, need, taken_meanings)


def build_quiz_plan(
    candidates: list[WordCandidate],
    total: int,
    today: date,
    rng: random.Random,
) -> QuizPlan:
    """FR-3.1-C, D 순서로 단어를 뽑는다.

    1) 자주 틀린 단어 → 2) 복습 대상 → 3) 신규·약한 단어 → 4) 부족분 보충.
    버킷이 모자라면 그 차이는 신규·약한 단어가 채우고, 그래도 모자라면 나머지에서 채운다.
    한 퀴즈 안에서는 같은 한글 뜻을 가진 단어를 두 번 뽑지 않는다 (ADR-08).
    """
    sizes = plan_bucket_sizes(total)
    meaning_of = {c.word_id: c.meaning for c in candidates}
    chosen: list[int] = []

    def not_chosen() -> list[WordCandidate]:
        chosen_set = set(chosen)
        return [c for c in candidates if c.word_id not in chosen_set]

    def taken_meanings() -> frozenset[str]:
        return frozenset(meaning_of[word_id] for word_id in chosen)

    wrong_ids = select_wrong(not_chosen(), sizes.wrong, today, taken_meanings())
    chosen.extend(wrong_ids)

    review_ids = select_review(not_chosen(), sizes.review, today, taken_meanings())
    chosen.extend(review_ids)

    # 앞 두 버킷에서 모자란 개수만큼 신규·약한 단어 목표를 늘린다.
    new_target = total - len(wrong_ids) - len(review_ids)
    new_ids = select_new_or_weak(not_chosen(), new_target, rng, taken_meanings())
    chosen.extend(new_ids)

    need_more = total - len(chosen)
    filled_ids = fill_shortfall(candidates, set(chosen), need_more, rng, taken_meanings())
    chosen.extend(filled_ids)

    rng.shuffle(chosen)
    return QuizPlan(word_ids=chosen, requested=total)
