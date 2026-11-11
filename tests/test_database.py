#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - DB 엔진·세션 관리 단위 테스트 (외래키 활성화, 커밋·롤백)
# 파일 위치: tests/test_database.py

import pytest
from sqlalchemy import select

from database import session_scope
from models import Word


def test_foreign_keys_pragma_is_on_for_every_connection(db_engine):
    with db_engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_session_scope_commits_on_success(db_engine):
    with session_scope() as session:
        session.add(Word(english="apple", korean_meaning="사과"))

    with session_scope() as session:
        assert session.scalars(select(Word.english)).all() == ["apple"]


def test_session_scope_rolls_back_on_error(db_engine):
    with pytest.raises(RuntimeError):
        with session_scope() as session:
            session.add(Word(english="apple", korean_meaning="사과"))
            raise RuntimeError("중간 실패")

    with session_scope() as session:
        assert session.scalars(select(Word)).all() == []
