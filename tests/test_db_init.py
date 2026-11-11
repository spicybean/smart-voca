#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - DB 초기화(CSV 검증·적재·롤백) 통합 테스트
# 파일 위치: tests/test_db_init.py

import csv
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import create_db_engine
from models import DBVersion, Example, Progress, Settings, Word
from services import db_init
from services.db_init import (
    CsvValidationError,
    default_csv_paths,
    initialize_database,
    load_csv_rows,
    needs_initialization,
    validate_csv_rows,
)

HEADER = ["english", "korean_meaning", "category", "level", "example_1", "example_2", "example_3"]


def write_csv(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)
    return path


def count(db_path: Path, model) -> int:
    engine = create_db_engine(db_path)
    try:
        with Session(engine) as session:
            return session.scalar(select(func.count()).select_from(model))
    finally:
        engine.dispose()


def test_real_csv_loads_1500_words_with_progress_and_builtin_examples(tmp_path):
    db_path = tmp_path / "smart_voca.db"

    result = initialize_database(db_path, default_csv_paths())

    assert result.word_count == 1500
    assert result.example_count == 4500
    assert count(db_path, Word) == 1500
    assert count(db_path, Progress) == 1500
    assert count(db_path, Example) == 4500
    engine = create_db_engine(db_path)
    try:
        with Session(engine) as session:
            sources = set(session.scalars(select(Example.source)).all())
            statuses = set(session.scalars(select(Progress.status)).all())
            settings = session.get(Settings, 1)
            version = session.get(DBVersion, 1).version
    finally:
        engine.dispose()
    assert sources == {"builtin"}
    assert statuses == {"미학습"}
    assert settings.selected_category == "선택안함"
    assert settings.daily_word_count == 10
    assert version == "1.1"


def test_validation_error_creates_no_db_file(tmp_path):
    db_path = tmp_path / "smart_voca.db"
    csv_path = write_csv(tmp_path / "bad.csv", [["apple", "사과", "기타", "1", "", "", ""]])

    with pytest.raises(CsvValidationError) as info:
        initialize_database(db_path, [csv_path])

    assert any("허용되지 않음" in message for message in info.value.errors)
    assert not db_path.exists()


def test_failed_insert_rolls_back_and_removes_db_file(tmp_path, monkeypatch):
    db_path = tmp_path / "smart_voca.db"
    csv_path = write_csv(tmp_path / "ok.csv", [["apple", "사과", "일상", "1", "An apple.", "", ""]])

    def fail_after_adding_words(session, rows):
        session.add(Word(english="temp", korean_meaning="임시", category="일상", level=1))
        raise RuntimeError("적재 중 오류")

    monkeypatch.setattr(db_init, "_insert_all", fail_after_adding_words)

    with pytest.raises(RuntimeError):
        initialize_database(db_path, [csv_path])

    assert not db_path.exists()


def test_needs_initialization_before_and_after(tmp_path):
    db_path = tmp_path / "smart_voca.db"
    csv_path = write_csv(tmp_path / "ok.csv", [["apple", "사과", "일상", "1", "An apple.", "", ""]])
    assert needs_initialization(db_path) is True

    initialize_database(db_path, [csv_path])

    assert needs_initialization(db_path) is False


def test_duplicate_english_ignoring_case_is_an_error(tmp_path):
    csv_path = write_csv(
        tmp_path / "dup.csv",
        [
            ["Apple", "사과", "일상", "1", "", "", ""],
            ["apple", "사과2", "일상", "1", "", "", ""],
        ],
    )

    errors = validate_csv_rows(load_csv_rows([csv_path]))

    assert len(errors) == 1
    assert "중복" in errors[0]


def test_level_out_of_range_is_an_error(tmp_path):
    csv_path = write_csv(tmp_path / "level.csv", [["kite", "연", "일상", "6", "", "", ""]])

    errors = validate_csv_rows(load_csv_rows([csv_path]))

    assert any("level" in message for message in errors)


def test_blank_category_and_level_get_defaults(tmp_path):
    csv_path = write_csv(tmp_path / "defaults.csv", [["kite", "연", "", "", "", "", ""]])

    rows = load_csv_rows([csv_path])

    assert rows[0]["category"] == "미분류"
    assert rows[0]["level"] == "1"
    assert validate_csv_rows(rows) == []


def test_blank_example_cells_are_skipped(tmp_path):
    db_path = tmp_path / "smart_voca.db"
    csv_path = write_csv(
        tmp_path / "partial.csv",
        [["kite", "연", "일상", "1", "A kite flies.", "", "The kite is red."]],
    )

    result = initialize_database(db_path, [csv_path])

    assert result.example_count == 2
    assert count(db_path, Example) == 2
