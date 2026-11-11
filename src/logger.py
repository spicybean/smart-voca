#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 로깅 설정 (파일 로테이션, 개발 모드 콘솔 출력)
# 파일 위치: src/logger.py

"""앱 전체가 쓰는 logging 설정. 설계서 시스템 구조 4.10절 기준.

- 로거 이름: smartvoca
- 파일: 1MB 단위 로테이션, 3개 보관
- 콘솔: 개발 모드에서만
- 레벨: 기본 INFO, 개발 모드는 DEBUG
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import config

LOGGER_NAME = "smartvoca"
LOG_FILE_NAME = "smart_voca.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _clear_handlers(logger: logging.Logger) -> None:
    # 여러 번 호출해도 핸들러가 중복되지 않도록 기존 핸들러를 닫고 뗀다.
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


def setup_logging(log_dir: Path | None = None) -> logging.Logger:
    """로거를 설정하고 돌려준다. log_dir을 생략하면 config의 로그 폴더를 쓴다."""
    logger = logging.getLogger(LOGGER_NAME)
    _clear_handlers(logger)

    dev_mode = config.is_dev_mode()
    logger.setLevel(logging.DEBUG if dev_mode else logging.INFO)

    directory = log_dir or config.get_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        directory / LOG_FILE_NAME,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if dev_mode:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
