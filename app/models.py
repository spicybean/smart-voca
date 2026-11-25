#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - DB 테이블 정의 (단어, 암기 이력, 시험 세션·문항, 설정)
# 파일 위치: app/models.py

"""SQLite 테이블. 첫 실행 때 create_all 로 자동 생성한다 (VOCA-NFR-003)."""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 로그인이 없으므로 모든 이력은 기본 사용자 1번에 기록한다 (FR-014 사용자 항목)
DEFAULT_USER_ID = 1


class Word(db.Model):
    """영단어와 뜻 (VOCA-FR-001~004)."""

    __tablename__ = "word"

    id = db.Column(db.Integer, primary_key=True)
    # 중복 검사용 키: 앞뒤 공백 제거 + 소문자 (FR-003 중복 처리 정책)
    english_key = db.Column(db.String(64), nullable=False, unique=True)
    english = db.Column(db.String(64), nullable=False)
    meaning = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class StudyLog(db.Model):
    """암기 카드 한 장의 기록 (VOCA-FR-014: 사용자, 시각, 단어, 일차)."""

    __tablename__ = "study_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, default=DEFAULT_USER_ID)
    word_id = db.Column(db.Integer, db.ForeignKey("word.id", ondelete="CASCADE"), nullable=False, index=True)
    day_no = db.Column(db.Integer, nullable=False)
    # known: 외웠어요, again: 아직이에요
    action = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)


class ExamSession(db.Model):
    """시험 한 회차 (VOCA-FR-021~025)."""

    __tablename__ = "exam_session"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, default=DEFAULT_USER_ID)
    question_count = db.Column(db.Integer, nullable=False)
    # en_ko: 영→한, ko_en: 한→영, mix: 섞기
    direction_mode = db.Column(db.String(10), nullable=False)
    # 선택한 출제 형식을 쉼표로 이어 쓴다 (예: "mc,short,ox")
    formats = db.Column(db.String(40), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(10), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    finished_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship(
        "ExamItem",
        backref="session",
        cascade="all, delete-orphan",
        order_by="ExamItem.position",
    )


class ExamItem(db.Model):
    """시험 문항 한 개와 답 (VOCA-FR-026: 단어, 형식, 방향, 정오, 시각)."""

    __tablename__ = "exam_item"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("exam_session.id", ondelete="CASCADE"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey("word.id", ondelete="CASCADE"), nullable=False, index=True)
    # en_ko 또는 ko_en
    direction = db.Column(db.String(10), nullable=False)
    # mc(4지선다), short(단답형), ox(OX)
    fmt = db.Column(db.String(10), nullable=False)
    prompt = db.Column(db.String(300), nullable=False)
    expected = db.Column(db.String(300), nullable=False)
    # 4지선다 보기 (JSON 문자열), OX 는 판정 대상 문장
    choices = db.Column(db.Text, nullable=True)
    given = db.Column(db.String(300), nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=True, index=True)


class Setting(db.Model):
    """키-값 설정. 지금은 하루 학습량만 쓴다 (FR-021 과 암기 일차 계산에 쓰임)."""

    __tablename__ = "setting"

    key = db.Column(db.String(40), primary_key=True)
    value = db.Column(db.String(200), nullable=False)
