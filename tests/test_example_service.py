#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 예문 서비스 (조회·부족 판정·학생 예문 추가·삭제) 테스트
# 파일 위치: tests/test_example_service.py

import pytest
from sqlalchemy import select

from database import session_scope
from models import Example
from services.example_service import (
    DuplicateExampleError,
    ExampleNotFoundError,
    add_user_example,
    delete_user_example,
    get_examples,
    needs_more_examples,
)
from services.word_service import WordNotFoundError, add_word


def add_builtin(word_id: int, sentences: list[str]) -> None:
    with session_scope() as session:
        for sentence in sentences:
            session.add(Example(word_id=word_id, sentence=sentence, source="builtin"))


def test_word_with_no_examples_needs_more(db_engine):
    word = add_word("kite", "연")

    assert get_examples(word.id) == []
    assert needs_more_examples(word.id) is True


def test_three_examples_are_enough(db_engine):
    word = add_word("apple", "사과")
    add_builtin(word.id, ["An apple.", "Red apple.", "Apple pie."])

    assert needs_more_examples(word.id) is False


def test_user_example_is_saved_with_user_source(db_engine):
    word = add_word("kite", "연")

    added = add_user_example(word.id, "  The kite is high.  ")

    assert added.sentence == "The kite is high."
    assert added.source == "user"
    assert [e.sentence for e in get_examples(word.id)] == ["The kite is high."]


def test_adding_two_user_examples_still_needs_one_more(db_engine):
    word = add_word("kite", "연")
    add_user_example(word.id, "A kite flies.")
    add_user_example(word.id, "The kite is red.")

    assert needs_more_examples(word.id) is True
    add_user_example(word.id, "I have a kite.")
    assert needs_more_examples(word.id) is False


@pytest.mark.parametrize("sentence", ["", "   "])
def test_blank_sentence_is_rejected(db_engine, sentence):
    word = add_word("kite", "연")

    with pytest.raises(ValueError):
        add_user_example(word.id, sentence)
    assert get_examples(word.id) == []


def test_too_long_sentence_is_rejected(db_engine):
    word = add_word("kite", "연")

    with pytest.raises(ValueError):
        add_user_example(word.id, "a" * 501)


def test_duplicate_sentence_is_rejected_and_not_saved(db_engine):
    word = add_word("kite", "연")
    add_user_example(word.id, "A kite flies.")

    with pytest.raises(DuplicateExampleError):
        add_user_example(word.id, "A kite flies.")

    assert len(get_examples(word.id)) == 1


def test_user_example_can_be_deleted(db_engine):
    word = add_word("kite", "연")
    added = add_user_example(word.id, "A kite flies.")

    delete_user_example(added.id)

    assert get_examples(word.id) == []


def test_builtin_example_cannot_be_deleted(db_engine):
    word = add_word("apple", "사과")
    add_builtin(word.id, ["An apple."])
    with session_scope() as session:
        example_id = session.scalars(select(Example.id).where(Example.word_id == word.id)).one()

    with pytest.raises(ValueError):
        delete_user_example(example_id)
    assert len(get_examples(word.id)) == 1


def test_missing_word_and_example_raise(db_engine):
    with pytest.raises(WordNotFoundError):
        get_examples(999)
    with pytest.raises(WordNotFoundError):
        add_user_example(999, "A kite.")
    with pytest.raises(ExampleNotFoundError):
        delete_user_example(999)
