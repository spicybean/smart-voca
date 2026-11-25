#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 상세 보기 (예문, 통계, 수정, 삭제) (UI 설계서 2.4.2절)
# 파일 위치: src/ui/word_detail_dialog.py

"""단어 하나의 예문과 학습 통계를 보여 준다. 예문 추가·삭제와 수정·삭제 버튼을 둔다."""

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services import word_service
from services.example_service import (
    DuplicateExampleError,
    add_user_example,
    delete_user_example,
    get_examples,
    needs_more_examples,
)
from services.word_service import DuplicateWordError, WordDetail
from ui import message_boxes
from ui.word_form_dialog import WordFormDialog

SOURCE_LABELS = {"builtin": "기본 (CSV)", "user": "사용자"}


class WordDetailDialog(QDialog):
    def __init__(self, parent: QWidget | None, word_id: int):
        super().__init__(parent)
        self.word_id = word_id
        self.deleted = False
        self.changed = False
        self.setWindowTitle("단어 상세")

        self.info_label = QLabel()
        self.stats_label = QLabel()
        self.examples_layout = QVBoxLayout()
        self.shortage_label = QLabel("예문이 부족합니다. 직접 추가해 보세요")
        self.example_input = QLineEdit()
        self.example_input.setPlaceholderText("새 예문 입력")
        self.example_input.textChanged.connect(self._update_add_enabled)
        self.add_button = QPushButton("추가")
        self.add_button.clicked.connect(self._add_example)

        edit_button = QPushButton("수정")
        edit_button.clicked.connect(self._edit_word)
        delete_button = QPushButton("삭제")
        delete_button.setObjectName("danger")
        delete_button.clicked.connect(self._delete_word)
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)

        add_row = QHBoxLayout()
        add_row.addWidget(self.example_input)
        add_row.addWidget(self.add_button)
        buttons = QHBoxLayout()
        for button in (edit_button, delete_button, close_button):
            buttons.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addWidget(QLabel("예문:"))
        layout.addLayout(self.examples_layout)
        layout.addWidget(self.shortage_label)
        layout.addLayout(add_row)
        layout.addWidget(QLabel("통계:"))
        layout.addWidget(self.stats_label)
        layout.addLayout(buttons)
        self.refresh()

    # 표시 ------------------------------------------------------------

    def refresh(self) -> None:
        detail: WordDetail = word_service.get_word_detail(self.word_id)
        info = detail.info
        self.info_label.setText(
            f"영어: {info.english}\n한글: {info.korean_meaning}\n분야: {info.category}\n난이도: {info.level}"
        )
        self._render_examples()
        self.shortage_label.setVisible(needs_more_examples(self.word_id))
        rate = "-" if detail.correct_rate is None else f"{round(detail.correct_rate)}%"
        next_review = detail.next_review_date.isoformat() if detail.next_review_date else "-"
        self.stats_label.setText(
            f"정답 {detail.correct_count} | 오답 {detail.wrong_count} | 연속 정답 {detail.consecutive_correct}\n"
            f"정답률: {rate}\n다음 복습: {next_review}\n상태: {detail.status}"
        )
        self._update_add_enabled()

    def _render_examples(self) -> None:
        while self.examples_layout.count():
            item = self.examples_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for number, example in enumerate(get_examples(self.word_id), start=1):
            row = QHBoxLayout()
            label = QLabel(f"{number}. {example.sentence}\n[출처: {SOURCE_LABELS.get(example.source, example.source)}]")
            row.addWidget(label)
            if example.source == "user":
                remove = QPushButton("✕")
                remove.clicked.connect(lambda _checked=False, eid=example.id: self._remove_example(eid))
                row.addWidget(remove)
            holder = QWidget()
            holder.setLayout(row)
            self.examples_layout.addWidget(holder)

    def _update_add_enabled(self, *_args) -> None:
        self.add_button.setEnabled(bool(self.example_input.text().strip()))

    # 동작 ------------------------------------------------------------

    def _add_example(self) -> None:
        try:
            add_user_example(self.word_id, self.example_input.text())
        except DuplicateExampleError:
            message_boxes.warn_duplicate_example(self)
            return
        self.example_input.clear()
        self.changed = True
        self.refresh()

    def _remove_example(self, example_id: int) -> None:
        delete_user_example(example_id)
        self.changed = True
        self.refresh()

    def _edit_word(self) -> None:
        dialog = WordFormDialog(self, word=word_service.get_word_detail(self.word_id).info)
        if not dialog.exec():
            return
        self.save_edit(dialog.values())

    def save_edit(self, values: tuple[str, str, str, int]) -> bool:
        english, korean, category, level = values
        try:
            word_service.update_word(self.word_id, english, korean, category, level)
        except DuplicateWordError:
            message_boxes.warn_duplicate_word(self, english.strip())
            return False
        except ValueError as error:
            message_boxes.warn_invalid_input(self, str(error))
            return False
        self.changed = True
        self.refresh()
        return True

    def _delete_word(self) -> None:
        english = word_service.get_word_detail(self.word_id).info.english
        if not message_boxes.confirm_delete_word(self, english):
            return
        word_service.delete_word(self.word_id)
        self.deleted = True
        self.accept()
