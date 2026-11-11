#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 수동·자동 백업, 백업 검증, 복구 (FR-1.8)
# 파일 위치: src/services/backup_service.py

"""백업과 복구. 설계서 4.11절, 데이터 설계서 5.2절 기준.

- 파일을 그대로 복사하지 않고 SQLite 백업 API를 쓴다 (앱이 DB를 열고 있어도 일관성 유지).
- 백업 폴더는 고정이다. 사용자는 저장 위치를 고르지 않는다 (2026-11-11 결정).
- 자동 백업은 최근 3개만 남긴다. 수동 백업과 복구 전 백업은 지우지 않는다.
"""

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import config
import database
from logger import LOGGER_NAME
from services.db_init import SCHEMA_VERSION

log = logging.getLogger(LOGGER_NAME)

AUTO_PREFIX = "auto_"
MANUAL_PREFIX = "manual_"
PRE_RESTORE_PREFIX = "pre_restore_"
AUTO_KEEP_COUNT = 3
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


class BackupError(RuntimeError):
    pass


class InvalidBackupError(BackupError):
    """SmartVoca DB가 아니거나 손상된 백업 파일."""


def _backup_dir() -> Path:
    directory = config.get_backup_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _new_backup_path(prefix: str) -> Path:
    """이름이 겹치면 _2, _3을 붙여 덮어쓰지 않는다."""
    directory = _backup_dir()
    stamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    candidate = directory / f"{prefix}{stamp}.db"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{prefix}{stamp}_{counter}.db"
        counter += 1
    return candidate


def _copy_database(source: Path, target: Path) -> None:
    """SQLite 백업 API로 source의 내용을 target에 복사한다."""
    source_connection = sqlite3.connect(str(source))
    try:
        target_connection = sqlite3.connect(str(target))
        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
    finally:
        source_connection.close()


def create_manual_backup() -> Path:
    """사용자가 누른 백업. backups/manual_*.db로 저장하고 경로를 돌려준다."""
    db_path = config.get_db_path()
    if not db_path.exists():
        raise BackupError("백업할 DB 파일이 없습니다.")
    target = _new_backup_path(MANUAL_PREFIX)
    _copy_database(db_path, target)
    log.info("수동 백업 생성: %s", target.name)
    return target


def auto_backup() -> Path:
    """앱 종료 때 호출. auto_*.db를 만들고 최근 3개만 남긴다."""
    db_path = config.get_db_path()
    if not db_path.exists():
        raise BackupError("백업할 DB 파일이 없습니다.")
    target = _new_backup_path(AUTO_PREFIX)
    _copy_database(db_path, target)
    auto_files = sorted(_backup_dir().glob(f"{AUTO_PREFIX}*.db"), key=lambda p: p.name, reverse=True)
    for old in auto_files[AUTO_KEEP_COUNT:]:
        old.unlink(missing_ok=True)
        log.info("오래된 자동 백업 삭제: %s", old.name)
    log.info("자동 백업 생성: %s", target.name)
    return target


def list_backups() -> list[Path]:
    """백업 폴더의 .db 파일을 최신 이름순으로 돌려준다 (복구 파일 선택용)."""
    return sorted(_backup_dir().glob("*.db"), key=lambda p: p.name, reverse=True)


def validate_backup(path: Path) -> bool:
    """SQLite 파일이고 DBVersion·Word 테이블이 있으며 무결성이 맞는지 확인한다."""
    if not path.is_file():
        return False
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if not {"DBVersion", "Word"}.issubset(tables):
                return False
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            return integrity == "ok"
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        return False


def _is_inside_backup_dir(path: Path) -> bool:
    return path.resolve().parent == _backup_dir().resolve()


def restore_backup(path: Path) -> None:
    """백업 폴더 안의 파일로 DB를 되돌린다.

    순서: 검증 → 현재 DB를 pre_restore로 보관 → 연결 닫기 → 복사 → 다시 연결 → 버전 확인.
    버전이 맞지 않으면 pre_restore 파일로 되돌리고 예외를 던진다.
    """
    path = Path(path)
    if not _is_inside_backup_dir(path):
        raise InvalidBackupError("백업 폴더 안의 파일만 복구할 수 있습니다.")
    if not validate_backup(path):
        raise InvalidBackupError("SmartVoca 백업 파일이 아니거나 손상되었습니다.")

    db_path = config.get_db_path()
    pre_restore = None
    if db_path.exists():
        pre_restore = _new_backup_path(PRE_RESTORE_PREFIX)
        _copy_database(db_path, pre_restore)
        log.info("복구 전 현재 DB 보관: %s", pre_restore.name)

    _close_engine()
    _copy_database(path, db_path)
    database.init_engine(db_path)

    if _stored_version() != SCHEMA_VERSION:
        log.error("복구한 백업의 스키마 버전이 맞지 않음, 복구 전 상태로 되돌림")
        _close_engine()
        if pre_restore is not None:
            _copy_database(pre_restore, db_path)
        database.init_engine(db_path)
        raise InvalidBackupError("백업 파일의 DB 버전이 현재 앱과 맞지 않습니다.")
    log.info("복구 완료: %s", path.name)


def _close_engine() -> None:
    try:
        database.get_engine().dispose()
    except RuntimeError:
        pass


def _stored_version() -> str | None:
    engine = database.get_engine()
    with engine.connect() as connection:
        row = connection.exec_driver_sql("SELECT version FROM DBVersion WHERE id = 1").fetchone()
    return row[0] if row else None
