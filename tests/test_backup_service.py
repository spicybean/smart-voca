#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 백업·복구 서비스 테스트 (임시 폴더 사용, 실제 data/ 미사용)
# 파일 위치: tests/test_backup_service.py

import csv
import sqlite3
from datetime import timedelta

import pytest

import config
import database
from services import backup_service
from services.backup_service import (
    AUTO_KEEP_COUNT,
    BackupError,
    InvalidBackupError,
    auto_backup,
    create_manual_backup,
    list_backups,
    restore_backup,
    validate_backup,
)
from services.db_init import initialize_database
from services.word_service import add_word, list_words


@pytest.fixture
def live_db(tmp_path, monkeypatch):
    """임시 폴더에 실제 파일 DB를 만들고 설정 경로를 그곳으로 돌린다."""
    db_path = tmp_path / "data" / "smart_voca.db"
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(config, "get_db_path", lambda: db_path)
    monkeypatch.setattr(config, "get_backup_dir", lambda: backup_dir)

    csv_path = tmp_path / "seed.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["english", "korean_meaning", "category", "level", "example_1", "example_2", "example_3"])
        writer.writerow(["apple", "사과", "일상", "1", "An apple.", "", ""])
    initialize_database(db_path, [csv_path])
    database.init_engine(db_path)
    yield db_path
    database.get_engine().dispose()


def word_names(path) -> list[str]:
    connection = sqlite3.connect(str(path))
    try:
        return sorted(row[0] for row in connection.execute("SELECT english FROM Word"))
    finally:
        connection.close()


def test_manual_backup_is_created_in_backup_folder_and_is_valid(live_db):
    path = create_manual_backup()

    assert path.parent == config.get_backup_dir()
    assert path.name.startswith("manual_") and path.suffix == ".db"
    assert validate_backup(path) is True
    assert word_names(path) == ["apple"]


def test_auto_backup_keeps_only_three_newest(live_db):
    for _ in range(AUTO_KEEP_COUNT + 2):
        auto_backup()

    auto_files = [p for p in list_backups() if p.name.startswith("auto_")]
    assert len(auto_files) == AUTO_KEEP_COUNT


def test_manual_backups_are_never_pruned(live_db):
    manual = [create_manual_backup() for _ in range(2)]
    for _ in range(AUTO_KEEP_COUNT + 2):
        auto_backup()

    assert all(path.exists() for path in manual)


def test_validate_rejects_non_sqlite_file(tmp_path):
    fake = tmp_path / "fake.db"
    fake.write_bytes(b"this is not a database")

    assert validate_backup(fake) is False


def test_validate_rejects_sqlite_without_smartvoca_tables(tmp_path):
    other = tmp_path / "other.db"
    connection = sqlite3.connect(str(other))
    connection.execute("CREATE TABLE memo (id INTEGER)")
    connection.commit()
    connection.close()

    assert validate_backup(other) is False


def test_restore_returns_db_to_backup_state_and_keeps_pre_restore_copy(live_db):
    backup = create_manual_backup()
    add_word("banana", "바나나")
    assert len(list_words().items) == 2

    restore_backup(backup)

    assert word_names(live_db) == ["apple"]
    assert len(list_words().items) == 1
    pre_restore = [p for p in list_backups() if p.name.startswith("pre_restore_")]
    assert len(pre_restore) == 1
    assert word_names(pre_restore[0]) == ["apple", "banana"]


def test_restore_rejects_file_outside_backup_folder(live_db, tmp_path):
    outside = tmp_path / "elsewhere.db"
    outside.write_bytes(live_db.read_bytes())

    with pytest.raises(InvalidBackupError):
        restore_backup(outside)


def test_restore_rejects_corrupt_backup(live_db):
    broken = config.get_backup_dir() / "manual_20000101_000000.db"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_bytes(b"garbage")

    with pytest.raises(InvalidBackupError):
        restore_backup(broken)


def test_manual_backup_fails_when_no_database(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "get_db_path", lambda: tmp_path / "missing.db")
    monkeypatch.setattr(config, "get_backup_dir", lambda: tmp_path / "backups")

    with pytest.raises(BackupError):
        create_manual_backup()
