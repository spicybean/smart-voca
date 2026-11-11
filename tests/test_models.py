#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - ORM 모델: 테이블 생성, 제약조건, CASCADE 삭제 단위 테스트
# 파일 위치: tests/test_models.py

from datetime import date

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import DBVersion, Example, Progress, Quiz, Settings, Word

EXPECTED_TABLES = {"Word", "Example", "Progress", "Quiz", "QuizSession", "Settings", "DBVersion"}


def test_all_seven_tables_are_created(db_engine):
    assert set(inspect(db_engine).get_table_names()) == EXPECTED_TABLES


def test_english_is_unique_ignoring_case(db_engine):
    with Session(db_engine) as session:
        session.add(Word(english="Apple", korean_meaning="사과"))
        session.commit()
        session.add(Word(english="apple", korean_meaning="사과2"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_category_rejects_unknown_value(db_engine):
    with Session(db_engine) as session:
        session.add(Word(english="kite", korean_meaning="연", category="기타"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_level_must_be_between_one_and_five(db_engine):
    with Session(db_engine) as session:
        session.add(Word(english="kite", korean_meaning="연", level=6))
        with pytest.raises(IntegrityError):
            session.commit()


def test_progress_allows_one_row_per_word(db_engine):
    with Session(db_engine) as session:
        word = Word(english="apple", korean_meaning="사과")
        session.add(word)
        session.flush()
        session.add(Progress(word_id=word.id))
        session.add(Progress(word_id=word.id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_word_cascades_to_related_rows(db_engine):
    with Session(db_engine) as session:
        word = Word(english="apple", korean_meaning="사과")
        word.examples.append(Example(sentence="I eat an apple.", source="builtin"))
        word.progress = Progress(status="학습중", correct_count=1, correct_rate=100.0)
        word.quizzes.append(Quiz(quiz_type="한→영", is_correct=True))
        session.add(word)
        session.commit()

        session.delete(word)
        session.commit()

        assert session.query(Example).count() == 0
        assert session.query(Progress).count() == 0
        assert session.query(Quiz).count() == 0


def test_database_level_cascade_needs_foreign_keys_on(db_engine):
    # ORM 없이 SQL로 Word를 지워도 연결된 Example이 함께 지워져야 한다 (PRAGMA foreign_keys = ON)
    with db_engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO Word (english, korean_meaning, category, level) VALUES ('apple', '사과', '일상', 1)"
        )
        connection.exec_driver_sql(
            "INSERT INTO Example (word_id, sentence, source) VALUES (1, 'I eat an apple.', 'builtin')"
        )
        connection.exec_driver_sql("DELETE FROM Word WHERE id = 1")
        remaining = connection.exec_driver_sql("SELECT COUNT(*) FROM Example").scalar()
    assert remaining == 0


def test_settings_is_single_row(db_engine):
    with Session(db_engine) as session:
        session.add(Settings(id=1, selected_category="선택안함", daily_word_count=10))
        session.commit()
        session.add(Settings(id=2, selected_category="선택안함", daily_word_count=10))
        with pytest.raises(IntegrityError):
            session.commit()


def test_settings_daily_count_range(db_engine):
    with Session(db_engine) as session:
        session.add(Settings(id=1, selected_category="일상", daily_word_count=51))
        with pytest.raises(IntegrityError):
            session.commit()


def test_db_version_defaults_to_schema_version(db_engine):
    with Session(db_engine) as session:
        session.add(DBVersion(id=1))
        session.commit()
        version = session.get(DBVersion, 1).version
    assert version == "1.1"


def test_progress_rate_can_be_null_and_dates_are_stored(db_engine):
    with Session(db_engine) as session:
        word = Word(english="apple", korean_meaning="사과")
        word.progress = Progress(correct_rate=None, last_reviewed_date=date(2026, 11, 11))
        session.add(word)
        session.commit()
        progress = session.query(Progress).one()
    assert progress.correct_rate is None
    assert progress.last_reviewed_date == date(2026, 11, 11)


def test_example_source_rejects_api_value(db_engine):
    # 외부 API를 쓰지 않으므로 source는 builtin(기본 예문) 또는 user(학생 입력)만 허용
    with Session(db_engine) as session:
        word = Word(english="apple", korean_meaning="사과")
        word.examples.append(Example(sentence="I eat an apple.", source="api"))
        session.add(word)
        with pytest.raises(IntegrityError):
            session.commit()
