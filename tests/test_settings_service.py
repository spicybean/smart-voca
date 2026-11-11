#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 학습 설정 저장·조회 테스트
# 파일 위치: tests/test_settings_service.py

import pytest

from services.settings_service import get_settings, save_settings


def test_defaults_when_nothing_saved(db_engine):
    value = get_settings()

    assert value.selected_category == "선택안함"
    assert value.daily_count == 10


def test_saved_values_are_returned(db_engine):
    save_settings("비즈니스", 15)

    value = get_settings()

    assert value.selected_category == "비즈니스"
    assert value.daily_count == 15


@pytest.mark.parametrize("count", [0, 51, -1])
def test_daily_count_must_be_between_1_and_50(db_engine, count):
    with pytest.raises(ValueError):
        save_settings("일상", count)


def test_daily_count_must_be_an_integer_not_bool(db_engine):
    with pytest.raises(ValueError):
        save_settings("일상", True)


def test_category_must_be_a_selectable_value(db_engine):
    with pytest.raises(ValueError):
        save_settings("미분류", 10)
