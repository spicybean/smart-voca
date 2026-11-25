#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 환경변수 설정 (DB_PATH, SECRET_KEY)
# 파일 위치: app/config.py

"""실행 설정. 값은 모두 환경변수에서 읽는다 (VOCA-NFR-004, 제출 규칙 R-08)."""

import os
import secrets
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 서버에서는 DB_PATH=/data/voca.db 로 준다. 개발 PC에서는 프로젝트의 data/voca.db 를 쓴다.
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "voca.db"

# 업로드 제한: 서버가 20MB까지 받는다 (과제 기술 요건)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def get_db_path() -> Path:
    """SQLite 파일 경로. 없으면 개발용 기본 위치."""
    return Path(os.environ.get("DB_PATH", DEFAULT_DB_PATH))


def get_secret_key() -> str:
    """세션 키. SECRET_KEY 가 없으면 실행할 때마다 무작위로 만든다 (R-08)."""
    return os.environ.get("SECRET_KEY") or secrets.token_hex(32)
