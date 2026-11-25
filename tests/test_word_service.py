#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 단어 등록·검색·수정·삭제, CSV 일괄 등록 테스트 (VOCA-FR-001~004)
# 파일 위치: tests/test_word_service.py

import pytest

from app import word_service
from app.models import Word, db
from app.word_service import WordError


def test_add_word_saves_english_and_meaning(ctx):
    word = word_service.add_word("  apple  ", "사과")

    assert word.english == "apple"
    assert word.meaning == "사과"
    assert word_service.count_words() == 1


def test_duplicate_ignores_case_and_extra_spaces(ctx):
    word_service.add_word("Apple", "사과")

    with pytest.raises(WordError, match="이미 등록된 단어"):
        word_service.add_word("  apple ", "사과2")


@pytest.mark.parametrize("english", ["", "123", "가나다", "a" * 65])
def test_invalid_english_is_rejected(ctx, english):
    with pytest.raises(WordError):
        word_service.add_word(english, "뜻")


def test_empty_meaning_is_rejected(ctx):
    with pytest.raises(WordError, match="뜻"):
        word_service.add_word("apple", "   ")


def test_search_matches_english_or_meaning(seeded):
    assert [w.english for w in word_service.search_words("apple")] == ["apple"]
    assert [w.english for w in word_service.search_words("강")] == ["river"]
    assert word_service.search_words("zzz") == []


def test_update_rejects_name_used_by_other_word(seeded):
    apple = db.session.scalar(db.select(Word).where(Word.english == "apple"))

    with pytest.raises(WordError):
        word_service.update_word(apple.id, "book", "사과")


def test_delete_removes_word(seeded):
    apple = db.session.scalar(db.select(Word).where(Word.english == "apple"))

    word_service.delete_word(apple.id)

    assert word_service.count_words() == len(seeded) - 1


def test_import_skips_duplicates_and_reports_invalid_rows(ctx):
    word_service.add_word("apple", "사과")
    raw = (
        "﻿영단어,뜻\r\n"
        "book,책\r\n"
        "Apple,사과\r\n"
        "book,책2\r\n"
        "gin하해,은행나무\r\n"
        "river,\r\n"
    ).encode("utf-8")

    report = word_service.import_csv(raw)

    assert report.added == 1
    assert report.duplicates == ["Apple", "book"]
    assert len(report.invalid) == 2
    assert word_service.count_words() == 2


def test_import_rejects_non_utf8_file(ctx):
    raw = "영단어,뜻\nbook,책\n".encode("cp949")

    with pytest.raises(WordError, match="UTF-8"):
        word_service.import_csv(raw)


def test_bundled_sample_csv_imports_without_errors(ctx):
    """저장소의 단어사전_샘플.csv 는 중복과 형식 오류 없이 모두 등록되어야 한다 (2026-11-25 원본 수정 기준)."""
    from pathlib import Path

    sample = Path(__file__).resolve().parent.parent / "app" / "seed" / "단어사전_샘플.csv"
    report = word_service.import_csv(sample.read_bytes())

    assert report.invalid == []
    assert report.duplicates == []
    assert report.added == 1999


def test_deleting_word_removes_its_study_and_exam_records(memorized):
    """이슈 #8: 단어를 지우면 암기 기록과 시험 문항이 함께 지워져야 한다."""
    from app import exam_service, study_service
    from app.models import ExamItem, StudyLog

    study_service.set_daily_amount(5)
    word = db.session.scalar(db.select(Word).where(Word.english == "apple"))
    study_service.record_card(word.id, 1, "known")
    session = exam_service.create_session(6, "en_ko", ["short"])  # 6개 전부 출제해서 이 단어가 반드시 포함되게
    assert any(item.word_id == word.id for item in session.items)

    word_service.delete_word(word.id)

    assert db.session.scalar(db.select(StudyLog).where(StudyLog.word_id == word.id)) is None
    assert db.session.scalar(db.select(ExamItem).where(ExamItem.word_id == word.id)) is None
