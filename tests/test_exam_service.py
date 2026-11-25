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
from app.study_service import record_card
from app.models import ExamItem, Word, db


def _real_session_id():
    """외래키가 켜져 있으므로 실제로 존재하는 시험 회차 id를 만든다."""
    from app.models import ExamSession

    session = ExamSession(question_count=1, direction_mode="en_ko", formats="short", position=1, status="done")
    db.session.add(session)
    db.session.commit()
    return session.id


def test_short_answer_accepts_any_meaning_part():
    assert exam_service.is_short_answer_correct("ko_en", "사과", "사과")
    assert exam_service.is_short_answer_correct("ko_en", "물체 / 반대하다", "반대하다")
    assert exam_service.is_short_answer_correct("ko_en", "물체 / 반대하다", "  물체  ")
    assert not exam_service.is_short_answer_correct("ko_en", "사과", "배")
    assert not exam_service.is_short_answer_correct("ko_en", "사과", "   ")


def test_english_short_answer_ignores_case_and_period():
    assert exam_service.is_short_answer_correct("en_ko", "apple", "Apple.")
    assert not exam_service.is_short_answer_correct("en_ko", "apple", "apples")


def test_create_session_validates_inputs(memorized):
    with pytest.raises(ExamError):
        exam_service.create_session(0, "en_ko", ["mc"])
    with pytest.raises(ExamError):
        exam_service.create_session(5, "bogus", ["mc"])
    with pytest.raises(ExamError):
        exam_service.create_session(5, "en_ko", [])


def test_create_session_needs_enough_words(ctx):
    with pytest.raises(ExamError, match="4개 이상"):
        exam_service.create_session(3, "en_ko", ["short"])


def test_mc_items_have_four_choices_including_answer(memorized):
    session = exam_service.create_session(6, "en_ko", ["mc"])

    for item in session.items:
        choices = json.loads(item.choices)
        assert len(choices) == 4
        assert item.expected in choices


def test_ox_items_expect_o_or_x(memorized):
    session = exam_service.create_session(6, "ko_en", ["ox"])

    assert {item.expected for item in session.items} <= {"O", "X"}


def test_answering_moves_forward_and_finishes(memorized):
    session = exam_service.create_session(3, "en_ko", ["short"])

    for _ in range(3):
        item = exam_service.current_item(session)
        exam_service.answer_item(session, item.expected)

    assert session.status == "done"
    correct, total = exam_service.score(session)
    assert (correct, total) == (3, 3)
    assert exam_service.wrong_items(session) == []


def test_wrong_answers_are_listed(memorized):
    session = exam_service.create_session(2, "en_ko", ["short"])
    exam_service.answer_item(session, "틀린답")
    exam_service.answer_item(session, exam_service.current_item(session).expected)

    wrong = exam_service.wrong_items(session)

    assert len(wrong) == 1
    assert wrong[0].given == "틀린답"


def test_answer_after_finish_is_rejected(memorized):
    session = exam_service.create_session(1, "en_ko", ["short"])
    exam_service.answer_item(session, "x")

    with pytest.raises(ExamError):
        exam_service.answer_item(session, "x")


def test_never_tested_words_are_picked_more_often(seeded):
    """가중치 추첨이라 항상 먼저 뽑히지는 않지만, 안 본 단어가 더 자주 뽑혀야 한다."""
    now = datetime.now()
    words = list(db.session.scalars(db.select(Word).order_by(Word.id)))
    for word in words[:3]:
        db.session.add(ExamItem(session_id=_real_session_id(), position=0, word_id=word.id, direction="en_ko",
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
        db.session.add(ExamItem(session_id=_real_session_id(), position=0, word_id=word.id, direction="en_ko",
                                fmt="short", prompt="x", expected="y", is_correct=True, answered_at=old))
    db.session.add(ExamItem(session_id=_real_session_id(), position=0, word_id=words[-1].id, direction="en_ko",
                            fmt="short", prompt="x", expected="y", is_correct=False, answered_at=old))
    db.session.commit()

    wins = 0
    for seed in range(200):
        picked = exam_service.pick_words(words, 1, random.Random(seed), now)
        wins += picked[0].id == words[-1].id
    assert wins > 200 / len(words)


def test_deleting_an_unanswered_word_skips_its_question(memorized):
    """이슈 #9: 시험 중 단어를 지우면 그 문항은 빠지고, 남은 문항이 이어서 나온다."""
    session = exam_service.create_session(4, "en_ko", ["short"])
    exam_service.answer_item(session, "x")
    victim = session.items[2].word_id
    db.session.delete(db.session.get(Word, victim))
    db.session.commit()
    db.session.refresh(session)

    current = exam_service.current_item(session)
    answered, total = exam_service.progress(session)

    assert current is not None and current.word_id != victim
    assert (answered, total) == (1, 3)


def test_deleting_the_current_word_moves_to_next(memorized):
    session = exam_service.create_session(3, "en_ko", ["short"])
    current_word_id = exam_service.current_item(session).word_id
    db.session.delete(db.session.get(Word, current_word_id))
    db.session.commit()
    db.session.refresh(session)

    nxt = exam_service.current_item(session)

    assert nxt is not None and nxt.word_id != current_word_id
    assert exam_service.progress(session) == (0, 2)


def test_session_finishes_when_remaining_words_are_deleted(memorized):
    session = exam_service.create_session(2, "en_ko", ["short"])
    exam_service.answer_item(session, "x")
    other = [item.word_id for item in session.items if item.answered_at is None]
    for word_id in other:
        db.session.delete(db.session.get(Word, word_id))
    db.session.commit()
    db.session.refresh(session)

    assert exam_service.current_item(session) is None
    assert session.status == "done"


def test_exam_uses_only_memorized_words(seeded):
    """외우지 않은 단어는 시험에 나오지 않는다."""
    from app.models import User
    for word_id in [w.id for w in db.session.scalars(db.select(Word)).all()][:4]:
        record_card(word_id, 1, "known", user_id=1)
    memorized_ids = {w.id for w in exam_service.memorized_words(1)}

    session = exam_service.create_session(10, "en_ko", ["short"], user_id=1)

    assert {item.word_id for item in session.items} <= memorized_ids
    assert len(memorized_ids) == 4


def test_last_again_answer_removes_word_from_pool(seeded):
    ids = [w.id for w in db.session.scalars(db.select(Word)).all()]
    for word_id in ids[:4]:
        record_card(word_id, 1, "known", user_id=1)
    record_card(ids[0], 1, "again", user_id=1)  # 마지막 응답이 아직이에요 -> 제외

    with pytest.raises(ExamError, match="4개 이상"):
        exam_service.create_session(3, "en_ko", ["short"], user_id=1)


def test_day_range_limits_the_pool(seeded):
    from app import study_service
    study_service.set_daily_amount(5)  # 1일차 5개, 2일차 1개
    ids = [w.id for w in db.session.scalars(db.select(Word).order_by(Word.id)).all()]
    for word_id in ids:
        record_card(word_id, 1 if word_id in ids[:5] else 2, "known", user_id=1)

    with pytest.raises(ExamError):
        exam_service.create_session(4, "en_ko", ["short"], user_id=1, day_from=2, day_to=2)
    session = exam_service.create_session(4, "en_ko", ["short"], user_id=1, day_from=1, day_to=1)
    assert {item.word_id for item in session.items} <= set(ids[:5])
