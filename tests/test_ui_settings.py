#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 설정 화면 (분야·학습량 저장, 백업·복구·초기화) 테스트 (화면 없이 실행)
# 파일 위치: tests/test_ui_settings.py

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

import config  # noqa: E402
from services import backup_service  # noqa: E402
from services.settings_service import get_settings, save_settings  # noqa: E402
from services.word_service import add_word  # noqa: E402
from ui import message_boxes  # noqa: E402
from ui.settings_widget import SettingsWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_screen_shows_saved_settings(db_engine, qapp):
    save_settings("비즈니스", 15)

    widget = SettingsWidget()

    assert widget.category_buttons["비즈니스"].isChecked()
    assert not widget.custom_spin.isVisible()
    assert widget.save_button.isEnabled() is False


def test_save_is_enabled_only_after_change_and_persists(db_engine, qapp):
    save_settings("선택안함", 10)
    widget = SettingsWidget()

    widget.category_buttons["일상"].setChecked(True)
    assert widget.save_button.isEnabled()
    widget.save_button.click()

    assert get_settings().selected_category == "일상"
    assert widget.save_button.isEnabled() is False


def test_custom_amount_shows_spinbox_and_saves_value(db_engine, qapp):
    save_settings("선택안함", 10)
    widget = SettingsWidget()

    custom = [button for button, value in widget.amount_buttons if value is None][0]
    custom.setChecked(True)
    widget.custom_spin.setValue(37)
    widget.save_button.click()

    assert get_settings().daily_count == 37


def test_out_of_range_custom_value_is_not_allowed(db_engine, qapp):
    widget = SettingsWidget()

    widget.custom_spin.setValue(999)

    assert widget.custom_spin.value() == 50


def test_manual_backup_creates_file_in_backup_folder(db_engine, qapp, tmp_path, monkeypatch):
    import csv

    from database import init_engine
    from services.db_init import initialize_database

    db_path = tmp_path / "data" / "smart_voca.db"
    monkeypatch.setattr(config, "get_db_path", lambda: db_path)
    monkeypatch.setattr(config, "get_backup_dir", lambda: tmp_path / "backups")
    seed = tmp_path / "seed.csv"
    with seed.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["english", "korean_meaning", "category", "level", "example_1", "example_2", "example_3"])
        writer.writerow(["apple", "사과", "일상", "1", "", "", ""])
    initialize_database(db_path, [seed])
    init_engine(db_path)
    widget = SettingsWidget()
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    widget._backup()

    created = list((tmp_path / "backups").glob("manual_*.db"))
    assert len(created) == 1
    assert backup_service.validate_backup(created[0]) is True


def test_restore_rejected_file_shows_warning(db_engine, qapp, monkeypatch, tmp_path):
    shown = []
    monkeypatch.setattr(message_boxes, "confirm_restore", lambda parent: True)
    monkeypatch.setattr(message_boxes, "warn_restore_failed", lambda parent: shown.append("failed"))
    monkeypatch.setattr(config, "get_backup_dir", lambda: tmp_path)
    bad = tmp_path / "manual_bad.db"
    bad.write_bytes(b"not sqlite")
    widget = SettingsWidget()

    ok = widget.restore_file(bad)

    assert ok is False
    assert shown == ["failed"]


def test_reset_is_skipped_when_cancelled(db_engine, qapp, monkeypatch):
    add_word("apple", "사과", "일상", 1)
    monkeypatch.setattr(message_boxes, "confirm_reset", lambda parent: False)
    widget = SettingsWidget()

    widget._reset()

    from services.word_service import list_words
    assert len(list_words().items) == 1
