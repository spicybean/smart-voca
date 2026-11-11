#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 서비스 (추가·중복·수정·삭제·목록) 통합 테스트
# 파일 위치: tests/test_word_service.py

import pytest
from sqlalchemy import select

from database import session_scope
from models import Example, Progress, Quiz, Word
from services import progress_service
from services.word_service import (
    DuplicateWordError,
    WordNotFoundError,
    add_word,
    delete_word,
    find_duplicate,
    list_words,
    update_word,
)


def test_add_word_creates_unlearned_progress(db_engine):
    info = add_word("apple", "사과", "일상", 1)

    with session_scope() as session:
        progress = session.scalars(select(Progress).where(Progress.word_id == info.id)).one()
    assert progress.status == "미학습"
    assert progress.correct_count == 0
    assert progress.correct_rate is None


def test_duplicate_check_ignores_case_and_surrounding_spaces(db_engine):
    add_word("Apple", "사과")

    with pytest.raises(DuplicateWordError):
        add_word(" apple ", "사과2")
    assert find_duplicate("APPLE") is not None


@pytest.mark.parametrize(
    "english, korean, category, level",
    [
        ("   ", "사과", "일상", 1),
        ("apple", "  ", "일상", 1),
        ("apple", "사과", "기타", 1),
        ("apple", "사과", "일상", 6),
        ("apple", "사과", "일상", True),
    ],
)
def test_add_word_rejects_invalid_fields(db_engine, english, korean, category, level):
    with pytest.raises(ValueError):
        add_word(english, korean, category, level)


def test_update_keeps_progress_and_examples(db_engine):
    info = add_word("apple", "사과", "일상", 1)
    with session_scope() as session:
        word = session.get(Word, info.id)
        word.progress.status = "학습중"
        word.progress.correct_count = 3
        word.examples.append(Example(sentence="I eat an apple.", source="builtin"))

    update_word(info.id, "Apple", "사과 (과일)", "일상", 2)

    with session_scope() as session:
        word = session.get(Word, info.id)
        assert word.english == "Apple"
        assert word.level == 2
        assert word.progress.status == "학습중"
        assert word.progress.correct_count == 3
        assert len(word.examples) == 1


def test_update_to_case_variant_of_itself_is_allowed(db_engine):
    info = add_word("apple", "사과")

    updated = update_word(info.id, "APPLE", "사과", "일상", 1)

    assert updated.english == "APPLE"


def test_update_to_another_words_english_is_rejected(db_engine):
    add_word("apple", "사과")
    banana = add_word("banana", "바나나")

    with pytest.raises(DuplicateWordError):
        update_word(banana.id, "Apple", "바나나", "일상", 1)


def test_update_missing_word_raises(db_engine):
    with pytest.raises(WordNotFoundError):
        update_word(999, "apple", "사과", "일상", 1)


def test_delete_cascades_to_examples_progress_and_quizzes(db_engine):
    info = add_word("apple", "사과")
    with session_scope() as session:
        word = session.get(Word, info.id)
        word.examples.append(Example(sentence="I eat an apple.", source="builtin"))
        word.quizzes.append(Quiz(quiz_type="한→영", is_correct=True))

    delete_word(info.id)

    with session_scope() as session:
        assert session.scalars(select(Example)).all() == []
        assert session.scalars(select(Progress)).all() == []
        assert session.scalars(select(Quiz)).all() == []


def test_delete_missing_word_raises(db_engine):
    with pytest.raises(WordNotFoundError):
        delete_word(999)


def test_list_filters_by_category_and_keyword_matches_meaning(db_engine):
    add_word("apple", "사과", "일상")
    add_word("invoice", "청구서", "비즈니스")

    business = list_words(category="비즈니스")
    by_meaning = list_words(category="전체", keyword="사과")

    assert [item.english for item in business.items] == ["invoice"]
    assert [item.english for item in by_meaning.items] == ["apple"]


def test_list_paginates_twenty_per_page(db_engine):
    for index in range(25):
        add_word(f"word{index:02d}", f"뜻{index}")

    first = list_words(page=1)
    second = list_words(page=2)

    assert len(first.items) == 20
    assert len(second.items) == 5
    assert first.total_count == 25
    assert first.total_pages == 2


def test_unattempted_words_go_last_in_progress_sort(db_engine, today):
    add_word("aaa", "가")
    tried = add_word("zzz", "나")
    with session_scope() as session:
        progress = session.get(Word, tried.id).progress
        progress_service.apply_result(progress, True, today)

    page = list_words(sort_by="progress")

    assert [item.english for item in page.items] == ["zzz", "aaa"]


def test_status_sort_puts_review_needed_first(db_engine, today):
    add_word("calm", "차분한")
    needs_review = add_word("alarm", "경보")
    with session_scope() as session:
        progress = session.get(Word, needs_review.id).progress
        progress_service.apply_result(progress, False, today)

    page = list_words(sort_by="status")

    assert page.items[0].english == "alarm"
    assert page.items[0].status == "복습필요"


def test_invalid_sort_key_is_rejected(db_engine):
    with pytest.raises(ValueError):
        list_words(sort_by="unknown")
