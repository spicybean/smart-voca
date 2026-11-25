#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 시험 출제, 답 채점, 결과 (VOCA-FR-021~026)
# 파일 위치: app/exam_service.py

"""시험 규칙.

출제 가중치 (정책, 문서화 대상):
- 한 번도 안 본 단어: 가중치 3.0 (가장 우선)
- 본 단어: 마지막으로 본 뒤 지난 날수가 길수록, 틀린 횟수가 많을수록 높음
- 가중치 순서대로 뽑되 같은 단어는 한 시험에 한 번만 나온다

형식:
- mc: 4지선다 (보기 4개 중 정답 1개)
- short: 단답형 (직접 입력, 뜻은 '/' 로 나뉜 각 뜻 중 하나만 맞아도 정답)
- ox: OX (제시한 뜻이 맞으면 O, 틀리면 X)
"""

import json
import random
from datetime import datetime

from sqlalchemy import func

from app.models import DEFAULT_USER_ID, ExamItem, ExamSession, Word, db

FORMAT_LABELS = {"mc": "4지선다", "short": "단답형", "ox": "OX"}
DIRECTION_LABELS = {"en_ko": "영→한", "ko_en": "한→영", "mix": "섞기"}
MAX_QUESTIONS = 50
MIN_WORDS_FOR_EXAM = 4
MC_CHOICE_COUNT = 4
MEANING_SEPARATORS = ("/", ",", ";")


class ExamError(ValueError):
    """시험을 만들 수 없을 때 (화면에 그대로 보여 준다)."""


def normalize_answer(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".")


def is_short_answer_correct(direction: str, expected: str, given: str) -> bool:
    answer = normalize_answer(given)
    if not answer:
        return False
    if direction == "en_ko":
        parts = [expected]
    else:
        parts = [expected]
        for separator in MEANING_SEPARATORS:
            parts = [piece for part in parts for piece in part.split(separator)]
    return any(answer == normalize_answer(part) for part in parts if part.strip())


def _last_answered_map() -> dict[int, datetime]:
    stmt = (
        db.select(ExamItem.word_id, func.max(ExamItem.answered_at))
        .where(ExamItem.answered_at.is_not(None))
        .group_by(ExamItem.word_id)
    )
    return {word_id: when for word_id, when in db.session.execute(stmt)}


def _wrong_count_map() -> dict[int, int]:
    stmt = (
        db.select(ExamItem.word_id, func.count(ExamItem.id))
        .where(ExamItem.is_correct == False)  # noqa: E712
        .group_by(ExamItem.word_id)
    )
    return {word_id: count for word_id, count in db.session.execute(stmt)}


def _weight(last: datetime | None, wrong: int, now: datetime) -> float:
    if last is None:
        return 3.0
    days = min((now - last).days, 14)
    return 1.0 + days / 7 + 0.5 * min(wrong, 5)


def pick_words(words: list[Word], count: int, rng: random.Random, now: datetime) -> list[Word]:
    """가중치 순서대로 count 개를 고른다 (Efraimidis-Spirakis 방식, 중복 없음)."""
    last = _last_answered_map()
    wrong = _wrong_count_map()
    keyed = []
    for word in words:
        weight = _weight(last.get(word.id), wrong.get(word.id, 0), now)
        keyed.append((rng.random() ** (1 / weight), word))
    keyed.sort(key=lambda pair: pair[0], reverse=True)
    return [word for _key, word in keyed[:count]]


def _mc_choices(answer: Word, others: list[Word], direction: str, rng: random.Random) -> list[str] | None:
    """정답 하나와 오답 셋. 뜻이 같은 단어는 오답에서 뺀다. 부족하면 None."""
    def shown(word: Word) -> str:
        return word.meaning if direction == "en_ko" else word.english

    correct = shown(answer)
    pool = [shown(word) for word in others if shown(word).strip().lower() != correct.strip().lower()]
    unique_pool = list(dict.fromkeys(pool))
    if len(unique_pool) < MC_CHOICE_COUNT - 1:
        return None
    options = [correct] + rng.sample(unique_pool, MC_CHOICE_COUNT - 1)
    rng.shuffle(options)
    return options


def _build_item(word: Word, position: int, direction: str, fmt: str, all_words: list[Word],
                rng: random.Random, now: datetime) -> ExamItem:
    if direction == "en_ko":
        prompt, expected = word.english, word.meaning
    else:
        prompt, expected = word.meaning, word.english

    choices = None
    if fmt == "mc":
        others = [other for other in all_words if other.id != word.id]
        options = _mc_choices(word, others, direction, rng)
        if options is None:
            fmt = "short"
        else:
            choices = json.dumps(options, ensure_ascii=False)
    if fmt == "ox":
        others = [other for other in all_words if other.id != word.id]
        truthful = rng.random() < 0.5
        if truthful or not others:
            candidate = expected
            expected_mark = "O"
        else:
            candidate_word = rng.choice(others)
            candidate = candidate_word.meaning if direction == "en_ko" else candidate_word.english
            expected_mark = "X" if candidate.strip().lower() != expected.strip().lower() else "O"
        choices = json.dumps([candidate], ensure_ascii=False)
        expected = expected_mark

    return ExamItem(
        position=position,
        word_id=word.id,
        direction=direction,
        fmt=fmt,
        prompt=prompt,
        expected=expected,
        choices=choices,
    )


def create_session(count: int, direction_mode: str, formats: list[str]) -> ExamSession:
    if not 1 <= count <= MAX_QUESTIONS:
        raise ExamError(f"문제 수는 1~{MAX_QUESTIONS}개 사이로 정해 주세요.")
    if direction_mode not in DIRECTION_LABELS:
        raise ExamError("출제 방향을 골라 주세요.")
    formats = [fmt for fmt in formats if fmt in FORMAT_LABELS]
    if not formats:
        raise ExamError("출제 형식을 하나 이상 골라 주세요.")

    words = list(db.session.scalars(db.select(Word).order_by(Word.id)))
    if len(words) < MIN_WORDS_FOR_EXAM:
        raise ExamError(f"단어가 {MIN_WORDS_FOR_EXAM}개 이상 있어야 시험을 볼 수 있습니다.")

    now = datetime.now()
    rng = random.Random(f"exam-{now.isoformat()}")
    chosen = pick_words(words, min(count, len(words)), rng, now)

    session = ExamSession(
        user_id=DEFAULT_USER_ID,
        question_count=len(chosen),
        direction_mode=direction_mode,
        formats=",".join(formats),
        position=0,
        status="active",
        created_at=now,
    )
    for index, word in enumerate(chosen):
        direction = rng.choice(["en_ko", "ko_en"]) if direction_mode == "mix" else direction_mode
        fmt = rng.choice(formats)
        session.items.append(_build_item(word, index, direction, fmt, words, rng, now))
    db.session.add(session)
    db.session.commit()
    return session


def _pending_items(session: ExamSession) -> list[ExamItem]:
    """아직 답하지 않은 문항 (순서대로). 단어가 지워진 문항은 DB에서 이미 빠져 있다."""
    return [item for item in session.items if item.answered_at is None]


def _finish(session: ExamSession) -> None:
    session.status = "done"
    session.finished_at = datetime.now()


def current_item(session: ExamSession) -> ExamItem | None:
    """지금 풀 문항 = 아직 답하지 않은 첫 문항. 남은 문항이 없으면 회차를 끝낸다 (이슈 #9)."""
    if session.status != "active":
        return None
    pending = _pending_items(session)
    if not pending:
        _finish(session)
        db.session.commit()
        return None
    return pending[0]


def progress(session: ExamSession) -> tuple[int, int]:
    """(답한 문항 수, 전체 문항 수). 시험 중 삭제된 단어의 문항은 전체에서도 빠진다."""
    total = len(session.items)
    return total - len(_pending_items(session)), total


def answer_item(session: ExamSession, given: str) -> ExamItem:
    item = current_item(session)
    if item is None:
        raise ExamError("이미 끝난 시험입니다.")
    given = given.strip()
    if item.fmt == "short":
        is_correct = is_short_answer_correct(item.direction, item.expected, given)
    else:
        is_correct = given == item.expected
    item.given = given[:300]
    item.is_correct = is_correct
    item.answered_at = datetime.now()
    session.position = progress(session)[0]
    if not _pending_items(session):
        _finish(session)
    db.session.commit()
    return item


def score(session: ExamSession) -> tuple[int, int]:
    answered = [item for item in session.items if item.is_correct is not None]
    return sum(1 for item in answered if item.is_correct), len(session.items)


def wrong_items(session: ExamSession) -> list[ExamItem]:
    return [item for item in session.items if item.is_correct is False]
