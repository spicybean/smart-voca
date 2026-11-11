#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 학습 설정 저장·조회 (FR-2.1, FR-2.2)
# 파일 위치: src/services/settings_service.py

"""학습 설정. 설계서 4.11절 기준.

설정 저장은 즉시 반영하고, 퀴즈 구성 값은 다음 '퀴즈 시작'부터 적용된다 (FR-2.1, FR-2.2).
"""

from dataclasses import dataclass
from datetime import datetime

from database import session_scope
from models import SELECTED_CATEGORY_VALUES, Settings

DEFAULT_CATEGORY = "선택안함"
DEFAULT_DAILY_COUNT = 10
MIN_DAILY_COUNT = 1
MAX_DAILY_COUNT = 50


@dataclass(frozen=True)
class SettingsValue:
    selected_category: str
    daily_count: int


def _to_value(row: Settings) -> SettingsValue:
    return SettingsValue(selected_category=row.selected_category, daily_count=row.daily_word_count)


def get_settings() -> SettingsValue:
    """저장된 설정을 돌려준다. 행이 없으면 기본값으로 만든다."""
    with session_scope() as session:
        row = session.get(Settings, 1)
        if row is None:
            row = Settings(
                id=1,
                selected_category=DEFAULT_CATEGORY,
                daily_word_count=DEFAULT_DAILY_COUNT,
            )
            session.add(row)
            session.flush()
        return _to_value(row)


def save_settings(category: str, daily_count: int) -> None:
    """분야와 일일 학습량을 저장한다. 잘못된 값은 ValueError."""
    if category not in SELECTED_CATEGORY_VALUES:
        raise ValueError(f"분야는 {', '.join(SELECTED_CATEGORY_VALUES)} 중 하나여야 합니다.")
    if isinstance(daily_count, bool) or not isinstance(daily_count, int):
        raise ValueError("학습량은 정수여야 합니다.")
    if not MIN_DAILY_COUNT <= daily_count <= MAX_DAILY_COUNT:
        raise ValueError(f"학습량은 {MIN_DAILY_COUNT}~{MAX_DAILY_COUNT} 사이여야 합니다.")

    with session_scope() as session:
        row = session.get(Settings, 1)
        if row is None:
            row = Settings(id=1)
            session.add(row)
        row.selected_category = category
        row.daily_word_count = daily_count
        row.last_updated_date = datetime.now()
