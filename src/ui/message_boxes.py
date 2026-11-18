#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 공통 대화상자 (UI 설계서 2.6절 목록)
# 파일 위치: src/ui/message_boxes.py

"""대화상자 문구와 버튼을 한 곳에 모은다. 각 함수는 사용자가 확인했는지 bool로 돌려준다."""

from PyQt6.QtWidgets import QMessageBox, QWidget


def _ask(parent: QWidget | None, title: str, text: str, ok_text: str, cancel_text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    ok_button = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    box.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(ok_button)
    box.exec()
    return box.clickedButton() is ok_button


def _notice(parent: QWidget | None, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)


def confirm_delete_word(parent: QWidget | None, english: str) -> bool:
    return _ask(
        parent,
        "단어 삭제",
        f"정말 삭제하시겠어요?\n\n'{english}'\n\n학습 기록과 예문도 함께 삭제됩니다.",
        "삭제",
        "취소",
    )


def warn_duplicate_word(parent: QWidget | None, english: str) -> None:
    _notice(parent, "중복된 단어", f"이미 등록된 단어입니다: {english}")


def confirm_restore(parent: QWidget | None) -> bool:
    return _ask(
        parent,
        "백업에서 복구",
        "현재 학습 기록이 백업 파일 내용으로 바뀝니다. 복구 전 현재 데이터는 자동 백업됩니다.",
        "복구",
        "취소",
    )


def warn_restore_failed(parent: QWidget | None) -> None:
    _notice(parent, "복구할 수 없음", "스마트보카 백업 파일이 아니거나 손상되었습니다.")


def confirm_reset(parent: QWidget | None) -> bool:
    return _ask(
        parent,
        "데이터 초기화",
        "모든 학습 기록(진도, 퀴즈, 예문, 단어 추가분)이 삭제됩니다. 되돌릴 수 없습니다.",
        "초기화",
        "취소",
    )


def confirm_discard_session(parent: QWidget | None) -> bool:
    return _ask(
        parent,
        "퀴즈 그만하기",
        "저장된 퀴즈 세션을 삭제합니다. 지금까지 답한 기록은 유지됩니다.",
        "그만하기",
        "취소",
    )


def warn_not_enough_words(parent: QWidget | None) -> None:
    _notice(parent, "퀴즈를 만들 수 없음", "분야 단어가 4개 미만이라 보기를 만들 수 없습니다.")


def warn_invalid_input(parent: QWidget | None, message: str) -> None:
    _notice(parent, "입력 확인", message)


def warn_database_error(parent: QWidget | None) -> None:
    _notice(parent, "데이터베이스 오류", "데이터를 읽을 수 없습니다. 백업에서 복구하거나 초기화할 수 있습니다.")
