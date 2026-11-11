#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - SQLite 엔진 생성, 외래키 활성화, 세션 관리
# 파일 위치: src/database.py

"""DB 연결 계층. 설계서 시스템 구조 4.7절 기준.

- 모든 연결에서 PRAGMA foreign_keys = ON 을 실행한다 (CASCADE 삭제가 동작하려면 필수).
- 세션은 session_scope() 한 곳에서 커밋·롤백·닫기를 처리한다.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

MEMORY_DB = ":memory:"

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def create_db_engine(db_path: Path | str) -> Engine:
    """SQLite 엔진을 만든다. ':memory:' 를 주면 테스트용 인메모리 DB를 쓴다."""
    # 쓰레드 워커(QThread)에서도 같은 엔진을 쓸 수 있도록 check_same_thread를 끈다.
    connect_args = {"check_same_thread": False}
    if str(db_path) == MEMORY_DB:
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args=connect_args)
    else:
        engine = create_engine(f"sqlite:///{Path(db_path).as_posix()}", connect_args=connect_args)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def init_engine(db_path: Path | str) -> Engine:
    """앱 시작 시 한 번 호출해 전역 엔진과 세션 팩토리를 만든다. 테이블은 만들지 않는다."""
    global _engine, _session_factory
    _engine = create_db_engine(db_path)
    _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("init_engine()을 먼저 호출해야 합니다.")
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """정상 종료면 커밋, 예외면 롤백하고 다시 던진다. 항상 세션을 닫는다."""
    if _session_factory is None:
        raise RuntimeError("init_engine()을 먼저 호출해야 합니다.")
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
