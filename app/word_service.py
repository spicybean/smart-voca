#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 단어 등록·조회·수정·삭제, CSV 일괄 등록 (VOCA-FR-001~004)
# 파일 위치: app/word_service.py

"""단어 관리 규칙. 화면과 무관하게 DB 만 다룬다."""

import csv
import io
import re

from sqlalchemy import or_

from app.models import Word, db

ENGLISH_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]*$")
MAX_ENGLISH = 64
MAX_MEANING = 200


class WordError(ValueError):
    """입력이 규칙에 맞지 않을 때 (화면에 그대로 보여 준다)."""


def normalize_english(text: str) -> str:
    """표시용 영단어: 앞뒤 공백과 중간 공백을 정리한다."""
    return " ".join(text.split())


def english_key(text: str) -> str:
    """중복 검사용 키 (VOCA-FR-003 정책): 공백 정리 후 소문자."""
    return normalize_english(text).lower()


def validate(english: str, meaning: str) -> tuple[str, str]:
    cleaned_english = normalize_english(english)
    cleaned_meaning = " ".join(meaning.split())
    if not cleaned_english:
        raise WordError("영단어를 입력해 주세요.")
    if len(cleaned_english) > MAX_ENGLISH or not ENGLISH_PATTERN.match(cleaned_english):
        raise WordError("영단어는 영문자, 공백, 하이픈, 아포스트로피만 쓸 수 있고 64자 이하여야 합니다.")
    if not cleaned_meaning:
        raise WordError("뜻을 입력해 주세요.")
    if len(cleaned_meaning) > MAX_MEANING:
        raise WordError("뜻은 200자 이하로 입력해 주세요.")
    return cleaned_english, cleaned_meaning


def find_by_english(english: str) -> Word | None:
    return db.session.scalar(db.select(Word).where(Word.english_key == english_key(english)))


def add_word(english: str, meaning: str) -> Word:
    cleaned_english, cleaned_meaning = validate(english, meaning)
    if find_by_english(cleaned_english):
        raise WordError(f"이미 등록된 단어입니다: {cleaned_english}")
    word = Word(english_key=english_key(cleaned_english), english=cleaned_english, meaning=cleaned_meaning)
    db.session.add(word)
    db.session.commit()
    return word


def update_word(word_id: int, english: str, meaning: str) -> Word:
    word = db.get_or_404(Word, word_id)
    cleaned_english, cleaned_meaning = validate(english, meaning)
    other = find_by_english(cleaned_english)
    if other is not None and other.id != word.id:
        raise WordError(f"이미 등록된 단어입니다: {cleaned_english}")
    word.english_key = english_key(cleaned_english)
    word.english = cleaned_english
    word.meaning = cleaned_meaning
    db.session.commit()
    return word


def delete_word(word_id: int) -> None:
    word = db.get_or_404(Word, word_id)
    db.session.delete(word)
    db.session.commit()


def search_words(query: str = "") -> list[Word]:
    """영단어 또는 뜻에 검색어가 들어간 단어 (VOCA-FR-004). 검색어가 없으면 전체."""
    stmt = db.select(Word).order_by(Word.english_key)
    q = query.strip()
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Word.english.ilike(pattern), Word.meaning.ilike(pattern)))
    return list(db.session.scalars(stmt))


def count_words() -> int:
    return db.session.scalar(db.select(db.func.count(Word.id))) or 0


class ImportReport:
    """CSV 일괄 등록 결과."""

    def __init__(self):
        self.added = 0
        self.duplicates: list[str] = []
        self.invalid: list[str] = []

    @property
    def summary(self) -> str:
        return (
            f"추가 {self.added}개, 중복으로 건너뜀 {len(self.duplicates)}개, "
            f"형식 오류로 건너뜀 {len(self.invalid)}개"
        )


def import_csv(raw: bytes) -> ImportReport:
    """영단어,뜻 두 열의 CSV를 읽는다. 정책 (문서화 대상):
    - 첫 줄은 제목 줄로 본다. 인코딩은 UTF-8 (BOM 허용).
    - DB 에 이미 있거나 파일 안에서 먼저 나온 같은 영단어(대소문자·공백 무시)는 건너뛴다. 먼저 나온 뜻을 쓴다.
    - 영단어 형식이 맞지 않거나 뜻이 비어 있으면 건너뛰고 줄 번호를 보고한다.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise WordError("CSV 파일은 UTF-8 인코딩이어야 합니다.") from error

    report = ImportReport()
    seen: set[str] = set()
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # 제목 줄
    for line_no, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) < 2:
            report.invalid.append(f"{line_no}줄: 열이 2개가 아닙니다")
            continue
        english_raw, meaning_raw = row[0], row[1]
        try:
            cleaned_english, cleaned_meaning = validate(english_raw, meaning_raw)
        except WordError as error:
            report.invalid.append(f"{line_no}줄 ({english_raw.strip()}): {error}")
            continue
        key = english_key(cleaned_english)
        if key in seen or find_by_english(cleaned_english):
            report.duplicates.append(cleaned_english)
            continue
        seen.add(key)
        db.session.add(Word(english_key=key, english=cleaned_english, meaning=cleaned_meaning))
        report.added += 1
    db.session.commit()
    return report
