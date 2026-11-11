#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 실행 모드 판정, 저장 경로
# 파일 위치: src/config.py

"""실행 모드(개발/배포)에 따라 DB·백업·로그 경로를 정한다.

개발 모드: 프로젝트 안의 data/, backups/, logs/ 를 쓴다.
배포 모드: 사용자 데이터 폴더(Windows %APPDATA%\\SmartVoca) 아래를 쓴다.
설계서 시스템 구조 4.8절, 데이터 설계서 8장 기준.
"""

import os
import sys
from pathlib import Path

APP_FOLDER_NAME = "SmartVoca"
DB_FILE_NAME = "smart_voca.db"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def is_dev_mode() -> bool:
    """SMARTVOCA_DEV=1 이거나 PyInstaller로 묶인 실행 파일이 아니면 개발 모드."""
    if os.environ.get("SMARTVOCA_DEV") == "1":
        return True
    return not getattr(sys, "frozen", False)


def _app_support_dir() -> Path:
    """배포 모드의 사용자 데이터 폴더."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_FOLDER_NAME
    return Path(os.environ.get("APPDATA", Path.home())) / APP_FOLDER_NAME


def get_data_dir() -> Path:
    """DB 파일이 들어가는 폴더."""
    if is_dev_mode():
        return PROJECT_ROOT / "data"
    return _app_support_dir()


def get_db_path() -> Path:
    return get_data_dir() / DB_FILE_NAME


def get_backup_dir() -> Path:
    if is_dev_mode():
        return PROJECT_ROOT / "backups"
    return _app_support_dir() / "backups"


def get_log_dir() -> Path:
    if is_dev_mode():
        return PROJECT_ROOT / "logs"
    return _app_support_dir() / "logs"


def ensure_runtime_dirs() -> None:
    """DB·백업·로그 폴더가 없으면 만든다."""
    for directory in (get_data_dir(), get_backup_dir(), get_log_dir()):
        directory.mkdir(parents=True, exist_ok=True)


