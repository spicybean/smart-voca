#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 추가·수정 팝업 (UI 설계서 2.4.1절)
# 파일 위치: src/ui/word_form_dialog.py

"""추가와 수정은 같은 폼을 쓴다. 저장 검증과 중복 검사는 word_service가 한다."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models import CATEGORY_VALUES
from services.word_service import DEFAULT_CATEGORY, DEFAULT_LEVEL, WordInfo


class WordFormDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, word: WordInfo | None = None):
        super().__init__(parent)
        self.setWindowTitle("단어 수정" if word else "새 단어 추가")

        self.english = QLineEdit()
        self.korean = QLineEdit()
        self.category = QComboBox()
        self.category.addItems(list(CATEGORY_VALUES))
        self.level = QSpinBox()
        self.level.setRange(1, 5)

        if word is None:
            self.category.setCurrentText(DEFAULT_CATEGORY)
            self.level.setValue(DEFAULT_LEVEL)
        else:
            self.english.setText(word.english)
            self.korean.setText(word.korean_meaning)
            self.category.setCurrentText(word.category)
            self.level.setValue(word.level)

        form = QFormLayout()
        form.addRow("영어 (필수)", self.english)
        form.addRow("한글 (필수)", self.korean)
        form.addRow("분야", self.category)
        form.addRow("난이도", self.level)

        save = QPushButton("저장")
        save.setObjectName("primary")
        save.clicked.connect(self.accept)
        cancel = QPushButton("취소")
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(save)
        buttons.addWidget(cancel)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def values(self) -> tuple[str, str, str, int]:
        """입력값을 (영어, 한글, 분야, 난이도)로 돌려준다. 앞뒤 공백 정리는 서비스가 한다."""
        return (
            self.english.text(),
            self.korean.text(),
            self.category.currentText(),
            self.level.value(),
        )
