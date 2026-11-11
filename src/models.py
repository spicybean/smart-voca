#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - SQLAlchemy ORM 모델 (테이블 7개, 데이터 설계서 v1.2 기준)
# 파일 위치: src/models.py

"""DB 테이블 정의. 제약조건과 인덱스는 데이터 설계서 2장 SQL 스키마를 따른다.

시각 기본값은 SQLite의 localtime 함수를 쓴다 (CURRENT_TIMESTAMP는 UTC라서 사용하지 않음, 데이터 설계서 7.2절).
"""

from datetime import date, datetime

from sqlalchemy import (
    REAL,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

LOCAL_NOW_SQL = text("(datetime('now', 'localtime'))")

CATEGORY_VALUES = ("일상", "비즈니스", "미분류")
STATUS_VALUES = ("미학습", "학습중", "복습필요", "숙달")
EXAMPLE_SOURCE_VALUES = ("builtin", "user")
QUIZ_TYPE_VALUES = ("한→영", "영→한")
SESSION_PHASE_VALUES = ("basic", "bonus")
SELECTED_CATEGORY_VALUES = ("선택안함", "일상", "비즈니스")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class Base(DeclarativeBase):
    pass


class Word(Base):
    __tablename__ = "Word"
    __table_args__ = (
        CheckConstraint(_in_list("category", CATEGORY_VALUES), name="ck_word_category"),
        CheckConstraint("level BETWEEN 1 AND 5", name="ck_word_level"),
        Index("idx_word_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 대소문자 무시 중복 불가 (NOCASE). 앱에서 앞뒤 공백을 제거한 뒤 저장한다.
    english: Mapped[str] = mapped_column(String(100, collation="NOCASE"), nullable=False, unique=True)
    korean_meaning: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="미분류", server_default="미분류")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )
    updated_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )

    examples: Mapped[list["Example"]] = relationship(
        back_populates="word", cascade="all, delete-orphan"
    )
    progress: Mapped["Progress | None"] = relationship(
        back_populates="word", uselist=False, cascade="all, delete-orphan"
    )
    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="word", cascade="all, delete-orphan"
    )


class Example(Base):
    __tablename__ = "Example"
    __table_args__ = (
        CheckConstraint(_in_list("source", EXAMPLE_SOURCE_VALUES), name="ck_example_source"),
        Index("idx_example_word_id", "word_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("Word.id", ondelete="CASCADE"), nullable=False)
    sentence: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="builtin", server_default="builtin")
    created_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )

    word: Mapped[Word] = relationship(back_populates="examples")


class Progress(Base):
    __tablename__ = "Progress"
    __table_args__ = (
        CheckConstraint(_in_list("status", STATUS_VALUES), name="ck_progress_status"),
        Index("idx_progress_status", "status"),
        Index("idx_progress_next_review", "next_review_date"),
        Index("idx_progress_last_reviewed", "last_reviewed_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 단어당 1행
    word_id: Mapped[int] = mapped_column(
        ForeignKey("Word.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="미학습", server_default="미학습")
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    wrong_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    consecutive_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # 시도 0이면 NULL (화면에는 '-')
    correct_rate: Mapped[float | None] = mapped_column(REAL, nullable=True)
    last_reviewed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )
    updated_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )

    word: Mapped[Word] = relationship(back_populates="progress")


class Quiz(Base):
    __tablename__ = "Quiz"
    __table_args__ = (
        CheckConstraint(_in_list("quiz_type", QUIZ_TYPE_VALUES), name="ck_quiz_type"),
        Index("idx_quiz_word_id", "word_id"),
        Index("idx_quiz_created_date", "created_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("Word.id", ondelete="CASCADE"), nullable=False)
    quiz_type: Mapped[str] = mapped_column(String(10), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_bonus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    is_retry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    created_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )

    word: Mapped[Word] = relationship(back_populates="quizzes")


class QuizSession(Base):
    """퀴즈 이어 풀기용 단일 레코드 (FR-3.6). 세션이 끝나면 행을 지운다."""

    __tablename__ = "QuizSession"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_quiz_session_single"),
        CheckConstraint(_in_list("phase", SESSION_PHASE_VALUES), name="ck_quiz_session_phase"),
        CheckConstraint("total_count >= 1", name="ck_quiz_session_total"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    phase: Mapped[str] = mapped_column(String(10), nullable=False)
    is_retry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # 문항 목록(JSON). 재개 시 보기가 바뀌지 않도록 생성 시점의 보기를 함께 저장한다.
    items_json: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )


class Settings(Base):
    """학습 설정 단일 레코드."""

    __tablename__ = "Settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_settings_single"),
        CheckConstraint(_in_list("selected_category", SELECTED_CATEGORY_VALUES), name="ck_settings_category"),
        CheckConstraint("daily_word_count BETWEEN 1 AND 50", name="ck_settings_daily_count"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    selected_category: Mapped[str] = mapped_column(
        String(10), nullable=False, default="선택안함", server_default="선택안함"
    )
    daily_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    last_updated_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )


class DBVersion(Base):
    """스키마 버전 단일 레코드. v1.1 스키마는 '1.1'."""

    __tablename__ = "DBVersion"
    __table_args__ = (CheckConstraint("id = 1", name="ck_db_version_single"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.1", server_default="1.1")
    created_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=LOCAL_NOW_SQL
    )
