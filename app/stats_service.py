#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 학습 진척 통계 (VOCA-FR-031~034), DB 이력으로 계산
# 파일 위치: app/stats_service.py

"""통계는 화면 값을 받지 않고 DB 이력에서만 계산한다 (VOCA-FR-034)."""

from sqlalchemy import func

from app.models import ExamItem, ExamSession, Word, db
from app.study_service import current_day, memorized_word_count, total_days


def progress_summary() -> dict:
    total_words = db.session.scalar(db.select(func.count(Word.id))) or 0
    return {
        "current_day": current_day(),
        "total_days": total_days(),
        "memorized": memorized_word_count(),
        "total_words": total_words,
    }


def daily_accuracy_trend() -> list[dict]:
    """날짜별 정답률 (VOCA-FR-032). 답한 문항이 있는 날만 나온다."""
    day = func.date(ExamItem.answered_at).label("day")
    stmt = (
        db.select(
            day,
            func.count(ExamItem.id).label("total"),
            func.sum(db.case((ExamItem.is_correct == True, 1), else_=0)).label("correct"),  # noqa: E712
        )
        .where(ExamItem.answered_at.is_not(None))
        .group_by(day)
        .order_by(day)
    )
    rows = []
    for row in db.session.execute(stmt):
        total = row.total or 0
        correct = row.correct or 0
        rows.append({"day": row.day, "total": total, "correct": correct, "rate": round(correct * 100 / total) if total else 0})
    return rows


def session_history() -> list[dict]:
    """회차별 점수 (VOCA-FR-032 회차별 추이)."""
    sessions = db.session.scalars(
        db.select(ExamSession).where(ExamSession.status == "done").order_by(ExamSession.id)
    )
    history = []
    for number, session in enumerate(sessions, start=1):
        correct = sum(1 for item in session.items if item.is_correct)
        total = len(session.items)
        history.append({
            "number": number,
            "finished_at": session.finished_at,
            "correct": correct,
            "total": total,
            "rate": round(correct * 100 / total) if total else 0,
        })
    return history


def frequent_wrong_words(limit: int = 10) -> list[dict]:
    """자주 틀리는 단어 상위 N개 (VOCA-FR-033)."""
    wrong = func.count(ExamItem.id).label("wrong")
    stmt = (
        db.select(Word.english, Word.meaning, wrong)
        .join(ExamItem, ExamItem.word_id == Word.id)
        .where(ExamItem.is_correct == False)  # noqa: E712
        .group_by(Word.id)
        .order_by(wrong.desc(), Word.english)
        .limit(limit)
    )
    return [{"english": row.english, "meaning": row.meaning, "wrong": row.wrong} for row in db.session.execute(stmt)]
