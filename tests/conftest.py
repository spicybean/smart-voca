#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 테스트 공용 픽스처 (WordCandidate 생성 헬퍼, 인메모리 DB)
# 파일 위치: tests/conftest.py

from datetime import date

import pytest

from database import init_engine
from domain.quiz_builder import WordCandidate
from models import Base

TODAY = date(2026, 11, 11)


@pytest.fixture
def today() -> date:
    return TODAY


@pytest.fixture
def db_engine():
    """테이블이 모두 만들어진 인메모리 DB. 테스트마다 새로 만든다."""
    engine = init_engine(":memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def make_candidate():
    """테스트마다 필요한 값만 바꿔 WordCandidate를 만드는 팩토리.

    status를 주지 않으면 시도 0이면 미학습, 시도가 있으면 숙달로 본다.
    숙달은 신규·약한 묶음에 들지 않으므로, 필요한 테스트는 status를 명시한다.
    """

    def _make(
        word_id: int,
        *,
        meaning: str | None = None,
        level: int = 1,
        category: str = "일상",
        attempts: int = 0,
        correct_rate: float | None = None,
        last_reviewed: date | None = None,
        next_review: date | None = None,
        english: str | None = None,
        status: str | None = None,
    ) -> WordCandidate:
        if status is None:
            status = "미학습" if attempts == 0 else "숙달"
        return WordCandidate(
            word_id=word_id,
            english=english or f"word{word_id}",
            meaning=meaning or f"뜻{word_id}",
            level=level,
            category=category,
            attempts=attempts,
            correct_rate=correct_rate,
            last_reviewed=last_reviewed,
            next_review=next_review,
            status=status,
        )

    return _make
