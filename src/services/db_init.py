#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 최초 DB 생성, CSV 검증·로드, 기본 예문 적재 (FR-1.1)
# 파일 위치: src/services/db_init.py

"""최초 실행 때 DB를 만든다. 설계서 4.11절, 데이터 설계서 5.1절 기준.

CSV 검증이 통과해야 DB 파일을 만든다. 적재 중 오류가 나면 트랜잭션을 되돌리고
DB 파일을 지운다. 그래서 다음 실행에서 다시 시도할 수 있다.
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from database import create_db_engine
from logger import LOGGER_NAME
from models import CATEGORY_VALUES, Base, DBVersion, Example, Progress, Settings, Word
from utils import normalize_english, resource_path

log = logging.getLogger(LOGGER_NAME)

SCHEMA_VERSION = "1.1"
CSV_FILE_NAMES = ("data/words_common.csv", "data/words_business.csv")
EXAMPLE_COLUMNS = ("example_1", "example_2", "example_3")
DEFAULT_CATEGORY = "미분류"
DEFAULT_LEVEL = 1
LEVEL_RANGE = range(1, 6)
DEFAULT_DAILY_WORD_COUNT = 10


@dataclass(frozen=True)
class InitResult:
    word_count: int
    example_count: int


class CsvValidationError(ValueError):
    """CSV 검증 실패. 모든 오류 메시지를 errors에 담는다."""

    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


def default_csv_paths() -> list[Path]:
    return [resource_path(name) for name in CSV_FILE_NAMES]


def needs_initialization(db_path: Path) -> bool:
    """DB 파일이 없거나, 테이블이 없거나, 단어가 하나도 없으면 초기화가 필요하다."""
    if not db_path.exists():
        return True
    engine = create_db_engine(db_path)
    try:
        if not inspect(engine).has_table("Word"):
            return True
        with Session(engine) as session:
            word_count = session.scalar(select(func.count()).select_from(Word))
        return word_count == 0
    finally:
        engine.dispose()


def load_csv_rows(csv_paths: list[Path]) -> list[dict]:
    """CSV를 읽어 정리된 행 목록을 만든다. 빈 분야·난이도는 기본값으로 채운다."""
    rows: list[dict] = []
    for path in csv_paths:
        with path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                rows.append({
                    "where": f"{path.name} {reader.line_num}행",
                    "english": normalize_english(raw.get("english") or ""),
                    "korean_meaning": (raw.get("korean_meaning") or "").strip(),
                    "category": (raw.get("category") or "").strip() or DEFAULT_CATEGORY,
                    "level": (raw.get("level") or "").strip() or str(DEFAULT_LEVEL),
                    "examples": [(raw.get(column) or "").strip() for column in EXAMPLE_COLUMNS],
                })
    return rows


def _is_level_in_range(value: str) -> bool:
    try:
        return int(value) in LEVEL_RANGE
    except ValueError:
        return False


def validate_csv_rows(rows: list[dict]) -> list[str]:
    """오류 메시지 목록을 돌려준다. 비어 있으면 검증 통과."""
    errors: list[str] = []
    first_seen: dict[str, str] = {}
    for row in rows:
        where = row["where"]
        english = row["english"]
        if not english:
            errors.append(f"{where}: english가 비어 있음")
        else:
            key = english.lower()
            if key in first_seen:
                errors.append(f"{where}: '{english}' 중복 (처음 위치: {first_seen[key]})")
            else:
                first_seen[key] = where
        if not row["korean_meaning"]:
            errors.append(f"{where}: 뜻이 비어 있음")
        if row["category"] not in CATEGORY_VALUES:
            errors.append(f"{where}: 분야 '{row['category']}'는 허용되지 않음")
        if not _is_level_in_range(row["level"]):
            errors.append(f"{where}: level '{row['level']}'은 1~5 정수여야 함")
    return errors


def _insert_all(session: Session, rows: list[dict]) -> int:
    """단어·진도·기본 예문·설정·버전을 넣는다. 넣은 예문 개수를 돌려준다."""
    example_count = 0
    for row in rows:
        word = Word(
            english=row["english"],
            korean_meaning=row["korean_meaning"],
            category=row["category"],
            level=int(row["level"]),
        )
        word.progress = Progress(
            status="미학습",
            correct_count=0,
            wrong_count=0,
            consecutive_correct=0,
            correct_rate=None,
        )
        for sentence in row["examples"]:
            if sentence:
                word.examples.append(Example(sentence=sentence, source="builtin"))
                example_count += 1
        session.add(word)
    session.add(Settings(id=1, selected_category="선택안함", daily_word_count=DEFAULT_DAILY_WORD_COUNT))
    session.add(DBVersion(id=1, version=SCHEMA_VERSION))
    session.flush()
    return example_count


def initialize_database(db_path: Path, csv_paths: list[Path]) -> InitResult:
    """DB를 만들고 CSV 데이터를 한 트랜잭션으로 넣는다.

    CSV 검증에 실패하면 DB 파일을 만들지 않고 CsvValidationError를 던진다.
    적재 중 오류가 나면 DB 파일을 지우고 예외를 다시 던진다.
    """
    log.info("DB 초기화 시작: %s", db_path)
    rows = load_csv_rows(csv_paths)
    errors = validate_csv_rows(rows)
    if errors:
        log.error("CSV 검증 실패 %d건", len(errors))
        raise CsvValidationError(errors)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_db_engine(db_path)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            example_count = _insert_all(session, rows)
            session.commit()
    except Exception:
        log.exception("DB 초기화 실패, DB 파일을 지우고 다시 시도할 수 있게 한다")
        engine.dispose()  # Windows에서 파일을 지우려면 연결을 먼저 닫아야 한다
        db_path.unlink(missing_ok=True)
        raise
    finally:
        engine.dispose()

    log.info("DB 초기화 완료: 단어 %d개, 기본 예문 %d개", len(rows), example_count)
    return InitResult(word_count=len(rows), example_count=example_count)
