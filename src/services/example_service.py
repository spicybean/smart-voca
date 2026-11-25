#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 예문 조회, 부족 판정, 학생 예문 추가·삭제 (FR-1.5, FR-1.6)
# 파일 위치: src/services/example_service.py

"""예문 유스케이스. 설계서 4.11절, 데이터 설계서 2.2절 기준.

예문은 두 출처만 있다 (외부 API 없음, ADR-02).
- builtin: CSV 기본 예문 (초기 DB 생성 때 들어감). 삭제할 수 없다.
- user: 학생이 직접 입력. 추가·삭제할 수 있다.
"""

from dataclasses import dataclass

from sqlalchemy import select

from database import session_scope
from models import Example, Word
from services.word_service import WordNotFoundError

MIN_EXAMPLES = 3
MAX_SENTENCE_LENGTH = 500
SOURCE_USER = "user"


class DuplicateExampleError(ValueError):
    """같은 단어에 같은 문장이 이미 있을 때 (FR-1.6)."""


class ExampleNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class ExampleInfo:
    id: int
    word_id: int
    sentence: str
    source: str


def _to_info(example: Example) -> ExampleInfo:
    return ExampleInfo(
        id=example.id,
        word_id=example.word_id,
        sentence=example.sentence,
        source=example.source,
    )


def get_examples(word_id: int) -> list[ExampleInfo]:
    """단어의 예문을 모두 돌려준다 (기본 예문 먼저, 입력 순서대로)."""
    with session_scope() as session:
        if session.get(Word, word_id) is None:
            raise WordNotFoundError(f"단어 id {word_id}를 찾을 수 없습니다.")
        statement = select(Example).where(Example.word_id == word_id).order_by(Example.id)
        return [_to_info(example) for example in session.scalars(statement).all()]


def needs_more_examples(word_id: int) -> bool:
    """예문이 3개 미만이면 True. 화면에 '직접 추가해 보세요' 안내를 띄운다 (FR-1.5)."""
    return len(get_examples(word_id)) < MIN_EXAMPLES


def add_user_example(word_id: int, sentence: str) -> ExampleInfo:
    """학생 예문을 추가한다. 같은 문장이 이미 있으면 DuplicateExampleError.

    빈 문장이나 공백만 있는 문장은 ValueError.
    """
    cleaned = sentence.strip()
    if not cleaned:
        raise ValueError("예문을 입력해 주세요.")
    if len(cleaned) > MAX_SENTENCE_LENGTH:
        raise ValueError(f"예문은 {MAX_SENTENCE_LENGTH}자 이하로 입력해 주세요.")

    with session_scope() as session:
        if session.get(Word, word_id) is None:
            raise WordNotFoundError(f"단어 id {word_id}를 찾을 수 없습니다.")
        existing = session.scalars(
            select(Example).where(Example.word_id == word_id, Example.sentence == cleaned)
        ).first()
        if existing is not None:
            raise DuplicateExampleError("같은 문장이 이미 등록되어 있습니다.")
        example = Example(word_id=word_id, sentence=cleaned, source=SOURCE_USER)
        session.add(example)
        session.flush()
        return _to_info(example)


def delete_user_example(example_id: int) -> None:
    """학생이 입력한 예문만 지울 수 있다. 기본 예문은 ValueError."""
    with session_scope() as session:
        example = session.get(Example, example_id)
        if example is None:
            raise ExampleNotFoundError(f"예문 id {example_id}를 찾을 수 없습니다.")
        if example.source != SOURCE_USER:
            raise ValueError("기본 예문은 삭제할 수 없습니다.")
        session.delete(example)
