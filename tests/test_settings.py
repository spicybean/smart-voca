#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 설정 저장과 반영 테스트 (VOCA-FR-061~062, 이슈 #12)
# 파일 위치: tests/test_settings.py

import pytest

from app import exam_service, settings_service, study_service
from app.models import Word, db


def test_defaults_when_nothing_saved(ctx):
    assert settings_service.get_review_percent() == settings_service.DEFAULT_REVIEW_PERCENT
    defaults = settings_service.get_exam_defaults()
    assert defaults["count"] == settings_service.DEFAULT_EXAM_COUNT
    assert defaults["direction"] == settings_service.DEFAULT_EXAM_DIRECTION
    assert defaults["formats"] == list(settings_service.DEFAULT_EXAM_FORMATS)


def test_review_percent_out_of_range_is_rejected(ctx):
    with pytest.raises(ValueError):
        settings_service.set_review_percent(51)
    with pytest.raises(ValueError):
        settings_service.set_review_percent(-1)


def test_zero_review_percent_gives_no_review_words(seeded):
    study_service.set_daily_amount(5)
    settings_service.set_review_percent(0)
    ids = list(db.session.scalars(db.select(Word.id).order_by(Word.id)))

    cards = study_service.day_word_ids(2)

    assert set(cards) == set(ids[5:])


def test_exam_defaults_are_saved_and_validated(ctx):
    saved = settings_service.set_exam_defaults(
        count=7, direction="ko_en", formats=["short", "bogus"],
        allowed_directions=exam_service.DIRECTION_LABELS,
        allowed_formats=exam_service.FORMAT_LABELS,
        max_count=exam_service.MAX_QUESTIONS,
    )
    assert saved == {"count": 7, "direction": "ko_en", "formats": ["short"]}
    assert settings_service.get_exam_defaults()["formats"] == ["short"]

    with pytest.raises(ValueError):
        settings_service.set_exam_defaults(
            count=7, direction="ko_en", formats=["bogus"],
            allowed_directions=exam_service.DIRECTION_LABELS,
            allowed_formats=exam_service.FORMAT_LABELS,
            max_count=exam_service.MAX_QUESTIONS,
        )


def test_settings_page_saves_all_values(client, ctx):
    response = client.post("/settings", data={
        "daily_amount": "15", "review_percent": "30", "exam_count": "8",
        "exam_direction": "mix", "exam_formats": ["mc", "ox"],
    }, follow_redirects=True)

    assert "설정을 저장했습니다".encode() in response.data
    assert study_service.get_daily_amount() == 15
    assert settings_service.get_review_percent() == 30
    assert settings_service.get_exam_defaults() == {"count": 8, "direction": "mix", "formats": ["mc", "ox"]}


def test_exam_page_uses_saved_defaults(client, memorized):
    client.post("/settings", data={
        "daily_amount": "20", "review_percent": "20", "exam_count": "4",
        "exam_direction": "ko_en", "exam_formats": ["short"],
    })

    html = client.get("/exam").get_data(as_text=True)

    assert 'name="count" value="4"' in html
    assert 'name="direction" value="ko_en" checked' in html
