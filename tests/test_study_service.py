#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 암기 일차 구성, 카드 기록 테스트 (VOCA-FR-011~014)
# 파일 위치: tests/test_study_service.py

import pytest

from app import study_service
from app.models import ExamItem, Word, db


def _real_session_id():
    """외래키가 켜져 있으므로 실제로 존재하는 시험 회차 id를 만든다."""
    from app.models import ExamSession

    session = ExamSession(question_count=1, direction_mode="en_ko", formats="short", position=1, status="done")
    db.session.add(session)
    db.session.commit()
    return session.id


def _ids_in_order():
    return list(db.session.scalars(db.select(Word.id).order_by(Word.id)))


def test_daily_amount_defaults_and_rejects_out_of_range(ctx):
    assert study_service.get_daily_amount() == study_service.DEFAULT_DAILY_AMOUNT
    with pytest.raises(ValueError):
        study_service.set_daily_amount(study_service.MAX_DAILY_AMOUNT + 1)
    assert study_service.set_daily_amount(5) == 5
    assert study_service.get_daily_amount() == 5


def test_total_days_rounds_up(seeded):
    study_service.set_daily_amount(5)

    assert study_service.total_days() == 2  # 6단어, 하루 5개


def test_day_one_has_first_words_in_order(seeded):
    study_service.set_daily_amount(5)
    ids = _ids_in_order()

    cards = study_service.day_word_ids(1)

    assert set(cards) == set(ids[:5])
    assert len(cards) == 5


def test_later_day_mixes_review_words_from_earlier_days(seeded):
    study_service.set_daily_amount(5)
    ids = _ids_in_order()

    cards = study_service.day_word_ids(2)

    assert ids[5] in cards  # 새 단어
    review = set(cards) - {ids[5]}
    assert review and review <= set(ids[:5])  # 복습은 이전 일차 단어에서만


def test_day_word_order_is_deterministic(seeded):
    study_service.set_daily_amount(5)

    assert study_service.day_word_ids(2) == study_service.day_word_ids(2)


def test_frequent_wrong_words_join_the_day(seeded):
    study_service.set_daily_amount(5)
    ids = _ids_in_order()
    wrong_word = ids[0]
    db.session.add(ExamItem(session_id=_real_session_id(), position=0, word_id=wrong_word, direction="en_ko",
                            fmt="short", prompt="x", expected="y", is_correct=False))
    db.session.commit()

    cards = study_service.day_word_ids(2)

    assert wrong_word in cards


def test_record_card_and_memorized_count(seeded):
    study_service.set_daily_amount(5)
    ids = _ids_in_order()

    study_service.record_card(ids[0], 1, "known")
    study_service.record_card(ids[1], 1, "again")
    study_service.record_card(ids[0], 1, "known")

    assert study_service.memorized_word_count() == 1
    assert study_service.current_day() == 1


def test_record_card_rejects_unknown_action(seeded):
    with pytest.raises(ValueError):
        study_service.record_card(_ids_in_order()[0], 1, "maybe")


def test_current_day_moves_to_latest_day_seen(seeded):
    study_service.set_daily_amount(5)
    study_service.record_card(_ids_in_order()[5], 2, "known")

    assert study_service.current_day() == 2
