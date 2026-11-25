#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 설정 값 저장과 검증 (복습 비율, 시험 기본값, 하루 학습량) (VOCA-FR-061~062)
# 파일 위치: app/settings_service.py

"""설정은 setting 테이블(키-값)에 저장한다. 값이 없으면 기본값을 쓴다."""

from app.models import Setting, db

DEFAULT_REVIEW_PERCENT = 20
MIN_REVIEW_PERCENT = 0
MAX_REVIEW_PERCENT = 50

DEFAULT_EXAM_COUNT = 10
DEFAULT_EXAM_DIRECTION = "en_ko"
DEFAULT_EXAM_FORMATS = ("mc", "short", "ox")


def _get(key: str) -> str | None:
    row = db.session.get(Setting, key)
    return row.value if row is not None else None


def _set(key: str, value: str) -> None:
    row = db.session.get(Setting, key)
    if row is None:
        db.session.add(Setting(key=key, value=value))
    else:
        row.value = value


def get_review_percent() -> int:
    value = _get("review_percent")
    return int(value) if value is not None else DEFAULT_REVIEW_PERCENT


def set_review_percent(value: int) -> int:
    if not MIN_REVIEW_PERCENT <= value <= MAX_REVIEW_PERCENT:
        raise ValueError(f"복습 비율은 {MIN_REVIEW_PERCENT}~{MAX_REVIEW_PERCENT}% 사이로 정해 주세요.")
    _set("review_percent", str(value))
    return value


def get_exam_defaults() -> dict:
    count = _get("exam_count")
    direction = _get("exam_direction")
    formats = _get("exam_formats")
    return {
        "count": int(count) if count is not None else DEFAULT_EXAM_COUNT,
        "direction": direction if direction is not None else DEFAULT_EXAM_DIRECTION,
        "formats": formats.split(",") if formats is not None else list(DEFAULT_EXAM_FORMATS),
    }


def set_exam_defaults(count: int, direction: str, formats: list[str], allowed_directions, allowed_formats,
                      max_count: int) -> dict:
    if not 1 <= count <= max_count:
        raise ValueError(f"시험 기본 문제 수는 1~{max_count}개 사이로 정해 주세요.")
    if direction not in allowed_directions:
        raise ValueError("시험 기본 방향을 골라 주세요.")
    chosen = [fmt for fmt in formats if fmt in allowed_formats]
    if not chosen:
        raise ValueError("시험 기본 형식을 하나 이상 골라 주세요.")
    _set("exam_count", str(count))
    _set("exam_direction", direction)
    _set("exam_formats", ",".join(chosen))
    return {"count": count, "direction": direction, "formats": chosen}
