#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 추가·수정·삭제·조회 (FR-1.2, 1.3, 1.4, 1.7)
# 파일 위치: src/services/word_service.py

"""단어 관리 유스케이스. 설계서 4.11절 기준.

- 중복 검사: 앞뒤 공백 제거 후 대소문자 무시 (FR-1.7-A). DB의 NOCASE 컬럼이 비교를 맡는다.
- 정렬: 시도 0인 단어(습득도 '-')는 어떤 정렬에서도 맨 뒤에 둔다 (FR-1.2).
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import session_scope
from models import CATEGORY_VALUES, Progress, Word
from utils import normalize_english

ALL_CATEGORIES = "전체"
DEFAULT_CATEGORY = "미분류"
DEFAULT_LEVEL = 1
PAGE_SIZE = 20

SORT_ENGLISH = "english"
SORT_STATUS = "status"
SORT_PROGRESS = "progress"

# 상태순: 복습이 필요한 단어를 먼저 보여준다
STATUS_ORDER = {"복습필요": 0, "학습중": 1, "미학습": 2, "숙달": 3}


class DuplicateWordError(ValueError):
    """같은 영어 단어가 이미 있다 (대소문자·앞뒤 공백 무시)."""


class WordNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class WordInfo:
    id: int
    english: str
    korean_meaning: str
    category: str
    level: int


@dataclass(frozen=True)
class WordListItem:
    id: int
    english: str
    korean_meaning: str
    category: str
    level: int
    status: str
    correct_rate: float | None
    last_reviewed_date: date | None
    correct_count: int
    wrong_count: int

    @property
    def attempts(self) -> int:
        return self.correct_count + self.wrong_count


@dataclass(frozen=True)
class WordPage:
    items: list[WordListItem]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, -(-self.total_count // self.page_size))


def _to_info(word: Word) -> WordInfo:
    return WordInfo(
        id=word.id,
        english=word.english,
        korean_meaning=word.korean_meaning,
        category=word.category,
        level=word.level,
    )


def _validate_fields(english: str, korean: str, category: str, level: int) -> tuple[str, str]:
    cleaned_english = normalize_english(english)
    cleaned_korean = korean.strip()
    if not cleaned_english:
        raise ValueError("영어 단어를 입력해 주세요.")
    if not cleaned_korean:
        raise ValueError("뜻을 입력해 주세요.")
    if category not in CATEGORY_VALUES:
        raise ValueError(f"분야는 {', '.join(CATEGORY_VALUES)} 중 하나여야 합니다.")
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 5:
        raise ValueError("난이도는 1~5 정수여야 합니다.")
    return cleaned_english, cleaned_korean


def find_duplicate(english: str, exclude_id: int | None = None) -> WordInfo | None:
    """같은 영어 단어를 찾는다. exclude_id는 수정 중인 자기 자신을 뺄 때 쓴다."""
    key = normalize_english(english)
    with session_scope() as session:
        statement = select(Word).where(Word.english == key)
        if exclude_id is not None:
            statement = statement.where(Word.id != exclude_id)
        word = session.scalars(statement).first()
        return _to_info(word) if word else None


def add_word(
    english: str,
    korean: str,
    category: str = DEFAULT_CATEGORY,
    level: int = DEFAULT_LEVEL,
) -> WordInfo:
    """단어를 추가하고 미학습 상태의 Progress를 함께 만든다 (FR-1.3)."""
    english, korean = _validate_fields(english, korean, category, level)
    if find_duplicate(english) is not None:
        raise DuplicateWordError(f"'{english}'은(는) 이미 등록되어 있습니다.")

    word = Word(english=english, korean_meaning=korean, category=category, level=level)
    word.progress = Progress(
        status="미학습",
        correct_count=0,
        wrong_count=0,
        consecutive_correct=0,
        correct_rate=None,
    )
    try:
        with session_scope() as session:
            session.add(word)
            session.flush()
            return _to_info(word)
    except IntegrityError as error:
        raise DuplicateWordError(f"'{english}'은(는) 이미 등록되어 있습니다.") from error


def update_word(
    word_id: int,
    english: str,
    korean: str,
    category: str,
    level: int,
) -> WordInfo:
    """단어를 수정한다. Progress와 Example은 그대로 둔다 (FR-1.7)."""
    english, korean = _validate_fields(english, korean, category, level)
    if find_duplicate(english, exclude_id=word_id) is not None:
        raise DuplicateWordError(f"'{english}'은(는) 이미 다른 단어로 등록되어 있습니다.")

    try:
        with session_scope() as session:
            word = session.get(Word, word_id)
            if word is None:
                raise WordNotFoundError(f"단어 id {word_id}를 찾을 수 없습니다.")
            word.english = english
            word.korean_meaning = korean
            word.category = category
            word.level = level
            word.updated_date = datetime.now()
            session.flush()
            return _to_info(word)
    except IntegrityError as error:
        raise DuplicateWordError(f"'{english}'은(는) 이미 다른 단어로 등록되어 있습니다.") from error


def delete_word(word_id: int) -> None:
    """단어를 삭제한다. 예문·진도·퀴즈 기록은 ORM cascade로 함께 지워진다 (FR-1.4)."""
    with session_scope() as session:
        word = session.get(Word, word_id)
        if word is None:
            raise WordNotFoundError(f"단어 id {word_id}를 찾을 수 없습니다.")
        session.delete(word)


def _to_list_item(word: Word, progress: Progress | None) -> WordListItem:
    correct = progress.correct_count if progress else 0
    wrong = progress.wrong_count if progress else 0
    return WordListItem(
        id=word.id,
        english=word.english,
        korean_meaning=word.korean_meaning,
        category=word.category,
        level=word.level,
        status=progress.status if progress else "미학습",
        correct_rate=progress.correct_rate if progress else None,
        last_reviewed_date=progress.last_reviewed_date if progress else None,
        correct_count=correct,
        wrong_count=wrong,
    )


def _sort_key(item: WordListItem, sort_by: str):
    # 시도 0인 단어는 모든 정렬에서 맨 뒤 (FR-1.2)
    unattempted = item.attempts == 0
    if sort_by == SORT_STATUS:
        primary = STATUS_ORDER.get(item.status, 99)
    elif sort_by == SORT_PROGRESS:
        primary = -(item.correct_rate or 0.0)  # 습득도 높은 순
    else:
        primary = 0
    return (unattempted, primary, item.english.lower())


def list_words(
    category: str | None = None,
    keyword: str = "",
    sort_by: str = SORT_ENGLISH,
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> WordPage:
    """단어 목록을 필터·검색·정렬해서 한 페이지 돌려준다 (FR-1.2)."""
    if page < 1 or page_size < 1:
        raise ValueError("페이지 번호와 크기는 1 이상이어야 합니다.")
    if sort_by not in (SORT_ENGLISH, SORT_STATUS, SORT_PROGRESS):
        raise ValueError(f"알 수 없는 정렬 기준: {sort_by}")

    statement = select(Word, Progress).outerjoin(Progress, Progress.word_id == Word.id)
    if category and category != ALL_CATEGORIES:
        statement = statement.where(Word.category == category)
    cleaned_keyword = keyword.strip()
    if cleaned_keyword:
        statement = statement.where(
            Word.english.contains(cleaned_keyword) | Word.korean_meaning.contains(cleaned_keyword)
        )

    with session_scope() as session:
        items = [_to_list_item(word, progress) for word, progress in session.execute(statement).all()]

    items.sort(key=lambda item: _sort_key(item, sort_by))
    start = (page - 1) * page_size
    return WordPage(
        items=items[start:start + page_size],
        total_count=len(items),
        page=page,
        page_size=page_size,
    )


@dataclass(frozen=True)
class WordDetail:
    info: WordInfo
    status: str
    correct_count: int
    wrong_count: int
    consecutive_correct: int
    correct_rate: float | None
    next_review_date: date | None


def get_word_detail(word_id: int) -> WordDetail:
    """단어 상세 보기용 정보와 학습 통계를 돌려준다 (FR-4.2)."""
    with session_scope() as session:
        word = session.get(Word, word_id)
        if word is None:
            raise WordNotFoundError(f"단어 id {word_id}를 찾을 수 없습니다.")
        progress = word.progress
        return WordDetail(
            info=_to_info(word),
            status=progress.status if progress else "미학습",
            correct_count=progress.correct_count if progress else 0,
            wrong_count=progress.wrong_count if progress else 0,
            consecutive_correct=progress.consecutive_correct if progress else 0,
            correct_rate=progress.correct_rate if progress else None,
            next_review_date=progress.next_review_date if progress else None,
        )
