#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 암기 일차 구성, 카드 기록, 설정 (VOCA-FR-011~014, FR-061)
# 파일 위치: app/study_service.py

"""암기 규칙. 단어를 등록 순서(id)대로 하루 학습량씩 잘라 일차를 만든다.

일차 구성 (정책, 문서화 대상):
- 기본: 해당 일차의 새 단어 (하루 학습량만큼)
- 복습: 이전 일차 단어 중 약 20% 를 무작위로 (같은 일차는 항상 같은 목록)
- 자주 틀린 단어: 시험에서 틀린 횟수가 많은 단어 3개 (일차 기본 목록에 없을 때만)
"""

import math
import random
from datetime import datetime

from sqlalchemy import func

from app import settings_service
from app.models import DEFAULT_USER_ID, ExamItem, ExamSession, Setting, StudyLog, Word, db

DEFAULT_DAILY_AMOUNT = 20
MIN_DAILY_AMOUNT = 5
MAX_DAILY_AMOUNT = 50
FREQUENT_WRONG_COUNT = 3


def get_daily_amount() -> int:
    row = db.session.get(Setting, "daily_amount")
    if row is None:
        return DEFAULT_DAILY_AMOUNT
    return int(row.value)


def set_daily_amount(value: int) -> int:
    if not MIN_DAILY_AMOUNT <= value <= MAX_DAILY_AMOUNT:
        raise ValueError(f"하루 학습량은 {MIN_DAILY_AMOUNT}~{MAX_DAILY_AMOUNT}개 사이로 정해 주세요.")
    row = db.session.get(Setting, "daily_amount")
    if row is None:
        db.session.add(Setting(key="daily_amount", value=str(value)))
    else:
        row.value = str(value)
    db.session.commit()
    return value


def total_days() -> int:
    total = db.session.scalar(db.select(func.count(Word.id))) or 0
    return math.ceil(total / get_daily_amount()) if total else 0


def _word_ids_in_order() -> list[int]:
    return list(db.session.scalars(db.select(Word.id).order_by(Word.id)))


def _frequent_wrong_ids(limit: int, user_id: int) -> list[int]:
    stmt = (
        db.select(ExamItem.word_id, func.count(ExamItem.id).label("wrong"))
        .join(ExamSession, ExamSession.id == ExamItem.session_id)
        .where(ExamSession.user_id == user_id)
        .where(ExamItem.is_correct == False)  # noqa: E712
        .group_by(ExamItem.word_id)
        .order_by(func.count(ExamItem.id).desc(), ExamItem.word_id)
        .limit(limit)
    )
    return [row.word_id for row in db.session.execute(stmt)]


def day_word_ids(day_no: int, user_id: int = DEFAULT_USER_ID) -> list[int]:
    """일차 카드 목록 (단어 id 순서). 복습과 자주 틀린 단어를 포함한다."""
    daily = get_daily_amount()
    ordered = _word_ids_in_order()
    start = (day_no - 1) * daily
    base = ordered[start:start + daily]
    if not base:
        return []

    rng = random.Random(f"day-{day_no}")
    chosen = list(base)
    earlier = ordered[:start]
    percent = settings_service.get_review_percent()
    review_count = max(1, round(daily * percent / 100)) if earlier and percent > 0 else 0
    if earlier and review_count:
        chosen += rng.sample(earlier, min(review_count, len(earlier)))

    for word_id in _frequent_wrong_ids(FREQUENT_WRONG_COUNT, user_id):
        if word_id not in chosen and word_id in ordered:
            chosen.append(word_id)

    rng.shuffle(chosen)
    return chosen


def record_card(word_id: int, day_no: int, action: str, user_id: int = DEFAULT_USER_ID) -> StudyLog:
    if action not in ("known", "again"):
        raise ValueError("알 수 없는 응답입니다.")
    if db.session.get(Word, word_id) is None:
        raise ValueError("단어를 찾을 수 없습니다.")
    log = StudyLog(
        user_id=user_id,
        word_id=word_id,
        day_no=day_no,
        action=action,
        created_at=datetime.now(),
    )
    db.session.add(log)
    db.session.commit()
    return log


def memorized_words(user_id: int = DEFAULT_USER_ID, day_from: int | None = None,
                    day_to: int | None = None) -> list[Word]:
    """이 계정이 '외웠어요'로 표시한 단어 (마지막 응답이 외웠어요인 단어). 일차 범위를 줄 수 있다.

    시험은 이 목록에서만 낸다 (이슈: 외우지 않은 단어가 시험에 나오는 문제).
    """
    latest_ids = (
        db.select(func.max(StudyLog.id))
        .where(StudyLog.user_id == user_id)
        .group_by(StudyLog.word_id)
    )
    stmt = (
        db.select(Word)
        .join(StudyLog, StudyLog.word_id == Word.id)
        .where(StudyLog.id.in_(latest_ids), StudyLog.action == "known")
    )
    if day_from is not None:
        stmt = stmt.where(StudyLog.day_no >= day_from)
    if day_to is not None:
        stmt = stmt.where(StudyLog.day_no <= day_to)
    return list(db.session.scalars(stmt.order_by(Word.id)))


def memorized_word_count(user_id: int = DEFAULT_USER_ID) -> int:
    stmt = (
        db.select(func.count(func.distinct(StudyLog.word_id)))
        .where(StudyLog.user_id == user_id, StudyLog.action == "known")
    )
    return db.session.scalar(stmt) or 0


def current_day(user_id: int = DEFAULT_USER_ID) -> int:
    """이 계정이 카드를 본 가장 큰 일차. 기록이 없으면 1일차."""
    latest = db.session.scalar(db.select(func.max(StudyLog.day_no)).where(StudyLog.user_id == user_id))
    return latest or 1
