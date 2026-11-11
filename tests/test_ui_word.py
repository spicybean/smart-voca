#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 관리 화면 (목록·페이지·검색·추가·삭제) 테스트 (화면 없이 실행)
# 파일 위치: tests/test_ui_word.py

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from services import word_service  # noqa: E402
from services.word_service import add_word  # noqa: E402
from ui import message_boxes  # noqa: E402
from ui.word_form_dialog import WordFormDialog  # noqa: E402
from ui.word_widget import WordWidget  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def test_table_shows_twenty_rows_per_page(db_engine, qapp):
    for index in range(25):
        add_word(f"word{index:02d}", f"뜻{index}", "일상", 1)

    widget = WordWidget()

    assert widget.table.rowCount() == 20
    assert widget.page_label.text() == "페이지: 1/2"
    assert widget.next_button.isEnabled()
    assert not widget.prev_button.isEnabled()


def test_next_page_shows_remaining_rows(db_engine, qapp):
    for index in range(25):
        add_word(f"word{index:02d}", f"뜻{index}", "일상", 1)
    widget = WordWidget()

    widget.next_button.click()

    assert widget.table.rowCount() == 5
    assert widget.page_label.text() == "페이지: 2/2"


def test_search_and_category_filter_narrow_the_table(db_engine, qapp):
    add_word("apple", "사과", "일상", 1)
    add_word("invoice", "청구서", "비즈니스", 2)
    widget = WordWidget()

    widget.search.setText("청구")
    assert widget.table.rowCount() == 1
    assert widget.table.item(0, 0).text() == "invoice"

    widget.search.setText("")
    widget.category.setCurrentText("일상")
    assert widget.table.rowCount() == 1
    assert widget.table.item(0, 0).text() == "apple"


def test_unattempted_row_shows_dash_for_rate(db_engine, qapp):
    add_word("apple", "사과", "일상", 1)

    widget = WordWidget()

    assert widget.table.item(0, 3).text() == "-"
    assert widget.table.item(0, 5).text() == "0/0"


def test_save_new_word_refreshes_table(db_engine, qapp):
    widget = WordWidget()

    ok = widget._save_new(("apple", "사과", "일상", 1))

    assert ok is True
    assert widget.table.rowCount() == 1


def test_duplicate_word_shows_warning_and_is_not_saved(db_engine, qapp, monkeypatch):
    add_word("apple", "사과", "일상", 1)
    shown = []
    monkeypatch.setattr(message_boxes, "warn_duplicate_word", lambda parent, english: shown.append(english))
    widget = WordWidget()

    ok = widget._save_new(("  Apple ", "사과2", "일상", 1))

    assert ok is False
    assert shown == ["Apple"]
    assert len(word_service.list_words().items) == 1


def test_delete_after_confirmation_removes_word(db_engine, qapp, monkeypatch):
    add_word("apple", "사과", "일상", 1)
    monkeypatch.setattr(message_boxes, "confirm_delete_word", lambda parent, english: True)
    widget = WordWidget()
    word_id = widget.table.item(0, 0).data(Qt.ItemDataRole.UserRole)

    widget._delete_word(word_id, "apple")

    assert word_service.list_words().items == []


def test_delete_cancelled_keeps_word(db_engine, qapp, monkeypatch):
    add_word("apple", "사과", "일상", 1)
    monkeypatch.setattr(message_boxes, "confirm_delete_word", lambda parent, english: False)
    widget = WordWidget()
    word_id = widget.table.item(0, 0).data(Qt.ItemDataRole.UserRole)

    widget._delete_word(word_id, "apple")

    assert len(word_service.list_words().items) == 1


def test_form_dialog_collects_values(qapp):
    dialog = WordFormDialog()
    dialog.english.setText(" kite ")
    dialog.korean.setText("연")
    dialog.category.setCurrentText("미분류")
    dialog.level.setValue(3)

    assert dialog.values() == (" kite ", "연", "미분류", 3)
