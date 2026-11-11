#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 설정 화면 (학습 분야·학습량, 정보, 백업·복구·초기화) (UI 설계서 2.5절)
# 파일 위치: src/ui/settings_widget.py

"""설정 탭. 값은 [저장]을 눌러야 저장된다 (UI 설계서 2.5절)."""

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import config
from services import progress_service
from services.backup_service import (
    InvalidBackupError,
    create_manual_backup,
    list_backups,
    restore_backup,
)
from services.db_init import reset_database
from services.settings_service import (
    DEFAULT_DAILY_COUNT,
    MAX_DAILY_COUNT,
    MIN_DAILY_COUNT,
    get_settings,
    save_settings,
)
from ui import message_boxes
from utils import today_local

CATEGORY_OPTIONS = (("일상", "일상"), ("비즈니스", "비즈니스"), ("선택안함(전체)", "선택안함"))
AMOUNT_OPTIONS = (("5개", 5), ("10개", 10), ("15개", 15), ("커스텀", None))
DB_FILE_NAME = config.DB_FILE_NAME


class SettingsWidget(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.category_group = QButtonGroup(self)
        self.category_buttons: dict[str, QRadioButton] = {}
        category_row = QHBoxLayout()
        for label, value in CATEGORY_OPTIONS:
            button = QRadioButton(label)
            button.toggled.connect(self._mark_dirty)
            self.category_group.addButton(button)
            self.category_buttons[value] = button
            category_row.addWidget(button)

        self.amount_group = QButtonGroup(self)
        self.amount_buttons: list[tuple[QRadioButton, int | None]] = []
        amount_row = QHBoxLayout()
        for label, value in AMOUNT_OPTIONS:
            button = QRadioButton(label)
            button.toggled.connect(self._mark_dirty)
            button.toggled.connect(self._update_custom_visibility)
            self.amount_group.addButton(button)
            self.amount_buttons.append((button, value))
            amount_row.addWidget(button)
        self.custom_spin = QSpinBox()
        self.custom_spin.setRange(MIN_DAILY_COUNT, MAX_DAILY_COUNT)
        self.custom_spin.valueChanged.connect(self._mark_dirty)

        self.save_button = QPushButton("저장")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self._save)

        self.info_label = QLabel()
        self.storage_label = QLabel(f"저장 위치: {config.get_data_dir()}")

        backup = QPushButton("백업 만들기")
        backup.clicked.connect(self._backup)
        restore = QPushButton("백업에서 복구")
        restore.clicked.connect(self._restore)
        reset = QPushButton("초기화")
        reset.setObjectName("danger")
        reset.clicked.connect(self._reset)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("📚 학습 설정"))
        layout.addWidget(QLabel("학습 분야:"))
        layout.addLayout(category_row)
        layout.addWidget(QLabel("일일 학습량:"))
        layout.addLayout(amount_row)
        layout.addWidget(self.custom_spin)
        layout.addWidget(QLabel("설정은 저장 즉시 반영되며, 퀴즈는 다음 '퀴즈 시작'부터 적용됩니다."))
        layout.addWidget(self.save_button)
        layout.addWidget(QLabel("📊 정보"))
        layout.addWidget(self.info_label)
        layout.addWidget(QLabel(f"데이터베이스: {DB_FILE_NAME}"))
        layout.addWidget(self.storage_label)
        layout.addWidget(QLabel("📁 데이터 관리"))
        data_row = QHBoxLayout()
        for button in (backup, restore, reset):
            data_row.addWidget(button)
        layout.addLayout(data_row)
        self._dirty = False
        self._loading = False
        self.load()

    # 표시와 저장 -----------------------------------------------------

    def load(self) -> None:
        """저장된 설정을 화면에 채운다."""
        settings = get_settings()
        self._loading = True
        self.category_buttons[settings.selected_category].setChecked(True)
        matched = False
        for button, value in self.amount_buttons:
            if value is not None and value == settings.daily_count:
                button.setChecked(True)
                matched = True
        if not matched:
            custom = next(button for button, value in self.amount_buttons if value is None)
            custom.setChecked(True)
        self.custom_spin.setValue(settings.daily_count if not matched else DEFAULT_DAILY_COUNT)
        self._loading = False
        self._set_dirty(False)
        self._update_custom_visibility()
        self._refresh_info()

    def _refresh_info(self) -> None:
        stats = progress_service.home_stats(None, today_local())
        self.info_label.setText(
            f"총 단어: {stats.total_words:,}개\n학습 완료(숙달): {stats.mastered_count:,}개"
        )

    def _selected_category(self) -> str:
        for value, button in self.category_buttons.items():
            if button.isChecked():
                return value
        return "선택안함"

    def _selected_count(self) -> int:
        for button, value in self.amount_buttons:
            if button.isChecked():
                return self.custom_spin.value() if value is None else value
        return DEFAULT_DAILY_COUNT

    def _update_custom_visibility(self, *_args) -> None:
        custom_checked = any(button.isChecked() for button, value in self.amount_buttons if value is None)
        self.custom_spin.setVisible(custom_checked)

    def _mark_dirty(self, *_args) -> None:
        if getattr(self, "_loading", False):
            return
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self.save_button.setEnabled(dirty)

    def _save(self) -> None:
        save_settings(self._selected_category(), self._selected_count())
        self._set_dirty(False)
        self.data_changed.emit()

    # 데이터 관리 -----------------------------------------------------

    def _backup(self) -> None:
        path = create_manual_backup()
        QMessageBox.information(self, "백업 완료", f"백업을 저장했습니다.\n{path}")

    def _restore(self) -> None:
        files = list_backups()
        if not files:
            QMessageBox.information(self, "백업에서 복구", "백업 폴더에 백업 파일이 없습니다.")
            return
        names = [path.name for path in files]
        chosen, ok = QInputDialog.getItem(self, "백업에서 복구", "복구할 백업 파일", names, 0, False)
        if not ok:
            return
        self.restore_file(Path(config.get_backup_dir()) / chosen)

    def restore_file(self, path: Path) -> bool:
        if not message_boxes.confirm_restore(self):
            return False
        try:
            restore_backup(path)
        except InvalidBackupError:
            message_boxes.warn_restore_failed(self)
            return False
        self.load()
        self.data_changed.emit()
        return True

    def _reset(self) -> None:
        if not message_boxes.confirm_reset(self):
            return
        reset_database()
        self.load()
        self.data_changed.emit()
