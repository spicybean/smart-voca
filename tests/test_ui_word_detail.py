#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 상세 보기 (예문·통계·수정·삭제) 테스트 (화면 없이 실행)
# 파일 위치: tests/test_ui_word_detail.py

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: E402
from sqlalchemy import select  # noqa: E402

from database import session_scope  # noqa: E402
from models import Example  # noqa: E402
from services import word_service  # noqa: E402
from services.example_service import get_examples  # noqa: E402
from services.word_service import add_word  # noqa: E402
from ui import message_boxes  # noqa: E402
from ui.word_detail_dialog import WordDetailDialog  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication([])


def add_builtin(word_id: int, sentences: list[str]) -> None:
    with session_scope() as session:
        for sentence in sentences:
            session.add(Example(word_id=word_id, sentence=sentence, source="builtin"))


def buttons_with_text(dialog, text: str) -> list[QPushButton]:
    return [button for button in dialog.findChildren(QPushButton) if button.text() == text]


def test_shortage_warning_shown_for_word_without_examples(db_engine, qapp):
    word = add_word("kite", "연", "일상", 1)

    dialog = WordDetailDialog(None, word.id)

    assert not dialog.shortage_label.isHidden()
    assert "정답 0" in dialog.stats_label.text()


def test_builtin_examples_show_source_and_no_remove_button(db_engine, qapp):
    word = add_word("apple", "사과", "일상", 1)
    add_builtin(word.id, ["An apple.", "Red apple.", "Apple pie."])

    dialog = WordDetailDialog(None, word.id)

    assert dialog.shortage_label.isHidden()
    assert buttons_with_text(dialog, "✕") == []


def test_add_user_example_button_enabled_only_with_text(db_engine, qapp):
    word = add_word("kite", "연", "일상", 1)
    dialog = WordDetailDialog(None, word.id)

    assert not dialog.add_button.isEnabled()
    dialog.example_input.setText("   ")
    assert not dialog.add_button.isEnabled()
    dialog.example_input.setText("A kite flies.")
    assert dialog.add_button.isEnabled()

    dialog.add_button.click()

    assert [e.sentence for e in get_examples(word.id)] == ["A kite flies."]
    assert dialog.changed is True


def test_user_example_can_be_removed_with_x_button(db_engine, qapp):
    word = add_word("kite", "연", "일상", 1)
    dialog = WordDetailDialog(None, word.id)
    dialog.example_input.setText("A kite flies.")
    dialog.add_button.click()

    remove = buttons_with_text(dialog, "✕")
    assert len(remove) == 1
    remove[0].click()

    assert get_examples(word.id) == []


def test_save_edit_updates_word_and_keeps_examples(db_engine, qapp):
    word = add_word("apple", "사과", "일상", 1)
    add_builtin(word.id, ["An apple."])
    dialog = WordDetailDialog(None, word.id)

    ok = dialog.save_edit(("Apple", "사과 (과일)", "비즈니스", 2))

    assert ok is True
    detail = word_service.get_word_detail(word.id)
    assert detail.info.english == "Apple"
    assert detail.info.category == "비즈니스"
    assert len(get_examples(word.id)) == 1


def test_save_edit_duplicate_warns_and_keeps_word(db_engine, qapp, monkeypatch):
    add_word("apple", "사과", "일상", 1)
    banana = add_word("banana", "바나나", "일상", 1)
    shown = []
    monkeypatch.setattr(message_boxes, "warn_duplicate_word", lambda parent, english: shown.append(english))
    dialog = WordDetailDialog(None, banana.id)

    ok = dialog.save_edit(("Apple", "바나나", "일상", 1))

    assert ok is False
    assert shown == ["Apple"]
    assert word_service.get_word_detail(banana.id).info.english == "banana"


def test_delete_after_confirmation_marks_deleted(db_engine, qapp, monkeypatch):
    word = add_word("apple", "사과", "일상", 1)
    monkeypatch.setattr(message_boxes, "confirm_delete_word", lambda parent, english: True)
    dialog = WordDetailDialog(None, word.id)

    dialog._delete_word()

    assert dialog.deleted is True
    assert word_service.list_words().items == []
