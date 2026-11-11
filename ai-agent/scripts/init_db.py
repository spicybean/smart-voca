#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - DB 초기화 CLI (services/db_init 호출, 이미 있으면 건너뜀)
# 파일 위치: ai-agent/scripts/init_db.py

"""개발자가 직접 DB를 만들 때 쓰는 얇은 래퍼. 실제 로직은 src/services/db_init.py에 있다.

사용법 (프로젝트 루트, venv 활성화 후):
    python ai-agent/scripts/init_db.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import config  # noqa: E402
from services.db_init import (  # noqa: E402
    CsvValidationError,
    default_csv_paths,
    initialize_database,
    needs_initialization,
)


def main() -> int:
    db_path = config.get_db_path()
    if not needs_initialization(db_path):
        print(f"이미 초기화되어 있습니다: {db_path}")
        return 0
    try:
        result = initialize_database(db_path, default_csv_paths())
    except CsvValidationError as error:
        print("CSV 검증 실패:")
        for message in error.errors:
            print(f"  - {message}")
        return 1
    print(f"초기화 완료: {db_path}")
    print(f"  단어 {result.word_count}개, 기본 예문 {result.example_count}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
