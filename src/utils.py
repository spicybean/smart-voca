#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 공용 유틸 (영단어 정규화, 로컬 날짜, 리소스 경로)
# 파일 위치: src/utils.py

"""여러 계층이 함께 쓰는 작은 함수 모음."""

import sys
from datetime import date, datetime
from pathlib import Path

from config import PROJECT_ROOT


def normalize_english(text: str) -> str:
    """앞뒤 공백을 제거한다. 대소문자는 DB의 NOCASE 비교가 처리한다."""
    return text.strip()


def today_local() -> date:
    """시스템 로컬 시간 기준 오늘 날짜. 자정에 바뀐다 (요구사항 6장 날짜 기준)."""
    return datetime.now().date()


def resource_path(relative: str) -> Path:
    """개발 모드는 프로젝트 루트, PyInstaller 실행 파일은 임시 풀림 폴더(sys._MEIPASS)를 기준으로 한다."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else PROJECT_ROOT
    return root / relative
