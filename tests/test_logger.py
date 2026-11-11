#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 로거 설정 단위 테스트 (파일 기록, 핸들러 중복 방지)
# 파일 위치: tests/test_logger.py

import logging
from logging.handlers import RotatingFileHandler

import pytest

from logger import LOG_FILE_NAME, LOGGER_NAME, setup_logging


@pytest.fixture
def logger_cleanup():
    yield
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def test_writes_messages_to_rotating_log_file(tmp_path, logger_cleanup):
    logger = setup_logging(tmp_path)

    logger.info("앱 시작")
    for handler in logger.handlers:
        handler.flush()

    log_text = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "앱 시작" in log_text


def test_repeated_setup_does_not_duplicate_handlers(tmp_path, logger_cleanup):
    setup_logging(tmp_path)
    logger = setup_logging(tmp_path)

    file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(file_handlers) == 1


def test_file_handler_uses_size_limit_and_three_backups(tmp_path, logger_cleanup):
    logger = setup_logging(tmp_path)

    file_handler = next(h for h in logger.handlers if isinstance(h, RotatingFileHandler))
    assert file_handler.maxBytes == 1_000_000
    assert file_handler.backupCount == 3
