#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 시험 출제·채점 테스트 (VOCA-FR-021~026)
# 파일 위치: tests/test_exam_service.py

import json
import random
from datetime import datetime, timedelta

import pytest

from app import exam_service
from app.exam_service import ExamError
from app.models import ExamItem, Word, db


def test_short_answer_accepts_any_meaning_part():
    assert exam_service.is_short_answer_correct("ko_en", "사과", "사과")
    assert exam_service.is_short_answer_correct("ko_en", "물체 / 반대하다", "반대하다")
    assert exam_service.is_short_answer_correct("ko_en", "물체 / 반대하다", "  물체  ")
    assert not exam_service.is_short_answer_correct("ko_en", "사과", "배")
    assert not exam_service.is_short_answer_correct("ko_en", "사과", "   ")


def test_english_short_answer_ignores_case_and_period():
    assert exam_service.is_short_answer_correct("en_ko", "apple", "Apple.")
    assert not exam_service.is_short_answer_correct("en_ko", "apple", "apples")


def test_create_session_validates_inputs(seeded):
    with pytest.raises(ExamError):
        exam_service.create_session(0, "en_ko", ["mc"])
    with pytest.raises(ExamError):
        exam_service.create_session(5, "bogus", ["mc"])
    with pytest.raises(ExamError):
        exam_service.create_session(5, "en_ko", [])


def test_create_session_needs_enough_words(ctx):
    with pytest.raises(ExamError, match="4개 이상"):
        exam_service.create_session(3, "en_ko", ["short"])


def test_mc_items_have_four_choices_including_answer(seeded):
    session = exam_service.create_session(6, "en_ko", ["mc"])

    for item in session.items:
        choices = json.loads(item.choices)
        assert len(choices) == 4
        assert item.expected in choices


def test_ox_items_expect_o_or_x(seeded):
    session = exam_service.create_session(6, "ko_en", ["ox"])

    assert {item.expected for item in session.items} <= {"O", "X"}


def test_answering_moves_forward_and_finishes(seeded):
    session = exam_service.create_session(3, "en_ko", ["short"])

    for _ in range(3):
        item = exam_service.current_item(session)
        exam_service.answer_item(session, item.expected)

    assert session.status == "done"
    correct, total = exam_service.score(session)
    assert (correct, total) == (3, 3)
    assert exam_service.wrong_items(session) == []


def test_wrong_answers_are_listed(seeded):
    session = exam_service.create_session(2, "en_ko", ["short"])
    exam_service.answer_item(session, "틀린답")
    exam_service.answer_item(session, exam_service.current_item(session).expected)

    wrong = exam_service.wrong_items(session)

    assert len(wrong) == 1
    assert wrong[0].given == "틀린답"


def test_answer_after_finish_is_rejected(seeded):
    session = exam_service.create_session(1, "en_ko", ["short"])
    exam_service.answer_item(session, "x")

    with pytest.raises(ExamError):
        exam_service.answer_item(session, "x")


def test_never_tested_words_are_picked_more_often(seeded):
    """가중치 추첨이라 항상 먼저 뽑히지는 않지만, 안 본 단어가 더 자주 뽑혀야 한다."""
    now = datetime.now()
    words = list(db.session.scalars(db.select(Word).order_by(Word.id)))
    for word in words[:3]:
        db.session.add(ExamItem(session_id=0, position=0, word_id=word.id, direction="en_ko",
                                fmt="short", prompt="x", expected="y", is_correct=True,
                                answered_at=now - timedelta(days=1)))
    db.session.commit()

    untested_hits = 0
    for seed in range(300):
        picked = exam_service.pick_words(words, 3, random.Random(seed), now)
        untested_hits += sum(1 for word in picked if word.id in {w.id for w in words[3:]})

    assert untested_hits / 300 > 1.5  # 안 본 단어 3개 중 평균 1.5개 이상은 뽑혀야 한다 (무작위 기대치 1.5)


def test_frequently_wrong_words_get_more_weight(seeded):
    now = datetime.now()
    words = list(db.session.scalars(db.select(Word).order_by(Word.id)))
    old = now - timedelta(days=3)
    for word in words:
        db.session.add(ExamItem(session_id=0, position=0, word_id=word.id, direction="en_ko",
                                fmt="short", prompt="x", expected="y", is_correct=True, answered_at=old))
    db.session.add(ExamItem(session_id=0, position=0, word_id=words[-1].id, direction="en_ko",
                            fmt="short", prompt="x", expected="y", is_correct=False, answered_at=old))
    db.session.commit()

    wins = 0
    for seed in range(200):
        picked = exam_service.pick_words(words, 1, random.Random(seed), now)
        wins += picked[0].id == words[-1].id
    assert wins > 200 / len(words)
