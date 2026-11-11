#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 단어 관리 화면 (목록, 검색·분야·정렬, 페이지, 추가·삭제) (UI 설계서 2.4절)
# 파일 위치: src/ui/word_widget.py

"""단어 목록 화면. 목록과 검증은 word_service가 맡고, 여기서는 표시와 입력만 한다."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import word_service
from services.word_service import (
    ALL_CATEGORIES,
    PAGE_SIZE,
    SORT_ENGLISH,
    SORT_PROGRESS,
    SORT_STATUS,
    DuplicateWordError,
    WordListItem,
)
from ui import message_boxes
from ui.styles import DANGER, PRIMARY, SECONDARY, TEXT, WARNING
from ui.word_detail_dialog import WordDetailDialog
from ui.word_form_dialog import WordFormDialog

CATEGORY_CHOICES = (ALL_CATEGORIES, "일상", "비즈니스", "미분류")
SORT_CHOICES = (("단어순", SORT_ENGLISH), ("상태순", SORT_STATUS), ("진도순", SORT_PROGRESS))
HEADERS = ("단어", "뜻", "상태", "습득도", "마지막복습", "정답/시도", "")
STATUS_COLORS = {
    "숙달": PRIMARY,
    "학습중": SECONDARY,
    "복습필요": WARNING,
    "미학습": TEXT,
}


class WordWidget(QWidget):
    word_selected = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.page = 1
        self.search = QLineEdit()
        self.search.setPlaceholderText("단어 또는 뜻 검색")
        self.search.textChanged.connect(self._reset_and_refresh)
        self.category = QComboBox()
        self.category.addItems(list(CATEGORY_CHOICES))
        self.category.currentIndexChanged.connect(self._reset_and_refresh)
        self.sort = QComboBox()
        for label, _key in SORT_CHOICES:
            self.sort.addItem(label)
        self.sort.currentIndexChanged.connect(self._reset_and_refresh)
        add_button = QPushButton("+ 추가")
        add_button.setObjectName("primary")
        add_button.clicked.connect(self._open_add_dialog)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(list(HEADERS))
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self._on_cell_clicked)

        self.page_label = QLabel()
        prev_button = QPushButton("◄")
        prev_button.clicked.connect(lambda: self._change_page(-1))
        next_button = QPushButton("►")
        next_button.clicked.connect(lambda: self._change_page(1))
        self.prev_button = prev_button
        self.next_button = next_button

        toolbar = QHBoxLayout()
        for widget in (self.search, self.category, self.sort, add_button):
            toolbar.addWidget(widget)
        pager = QHBoxLayout()
        pager.addWidget(self.page_label)
        pager.addWidget(prev_button)
        pager.addWidget(next_button)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.table)
        layout.addLayout(pager)
        self.refresh()

    # 목록 ------------------------------------------------------------

    def _selected_sort_key(self) -> str:
        return SORT_CHOICES[self.sort.currentIndex()][1]

    def _reset_and_refresh(self, *_args) -> None:
        self.page = 1
        self.refresh()

    def _change_page(self, step: int) -> None:
        self.page = max(1, self.page + step)
        self.refresh()

    def refresh(self) -> None:
        page = word_service.list_words(
            category=self.category.currentText(),
            keyword=self.search.text(),
            sort_by=self._selected_sort_key(),
            page=self.page,
            page_size=PAGE_SIZE,
        )
        if page.items == [] and page.total_count > 0 and self.page > page.total_pages:
            self.page = page.total_pages
            page = word_service.list_words(
                category=self.category.currentText(),
                keyword=self.search.text(),
                sort_by=self._selected_sort_key(),
                page=self.page,
                page_size=PAGE_SIZE,
            )
        self.table.setRowCount(len(page.items))
        for row, item in enumerate(page.items):
            self._fill_row(row, item)
        self.page_label.setText(f"페이지: {self.page}/{page.total_pages}")
        self.prev_button.setEnabled(self.page > 1)
        self.next_button.setEnabled(self.page < page.total_pages)

    def _fill_row(self, row: int, item: WordListItem) -> None:
        attempts = item.attempts
        rate = "-" if attempts == 0 else f"{round(item.correct_rate or 0)}%"
        last = item.last_reviewed_date.isoformat() if item.last_reviewed_date else "-"
        values = (
            item.english,
            item.korean_meaning,
            item.status,
            rate,
            last,
            f"{item.correct_count}/{attempts}",
            "✕",
        )
        for column, value in enumerate(values):
            cell = QTableWidgetItem(value)
            cell.setData(Qt.ItemDataRole.UserRole, item.id)
            if column == 2:
                cell.setForeground(QColor(STATUS_COLORS.get(item.status, TEXT)))
            if column == 6:
                cell.setForeground(QColor(DANGER))
            self.table.setItem(row, column, cell)

    def _on_cell_clicked(self, row: int, column: int) -> None:
        cell = self.table.item(row, 0)
        if cell is None:
            return
        word_id = cell.data(Qt.ItemDataRole.UserRole)
        if column == 6:
            self._delete_word(word_id, cell.text())
        else:
            self._open_detail(word_id)

    def _open_detail(self, word_id: int) -> None:
        dialog = WordDetailDialog(self, word_id)
        dialog.exec()
        self.word_selected.emit(word_id)
        self.refresh()

    # 추가·삭제 --------------------------------------------------------

    def _open_add_dialog(self) -> None:
        dialog = WordFormDialog(self)
        if dialog.exec():
            self._save_new(dialog.values())

    def _save_new(self, values: tuple[str, str, str, int]) -> bool:
        english, korean, category, level = values
        try:
            word_service.add_word(english, korean, category, level)
        except DuplicateWordError:
            message_boxes.warn_duplicate_word(self, english.strip())
            return False
        except ValueError as error:
            message_boxes.warn_invalid_input(self, str(error))
            return False
        self.refresh()
        return True

    def _delete_word(self, word_id: int, english: str) -> None:
        if not message_boxes.confirm_delete_word(self, english):
            return
        word_service.delete_word(word_id)
        self.refresh()
