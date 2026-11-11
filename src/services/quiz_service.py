#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 퀴즈 세션 시작·답변·재개·보너스·종료 (FR-3.1~3.6)
# 파일 위치: src/services/quiz_service.py

"""퀴즈 유스케이스. 설계서 4.11절, 데이터 설계서 2.4·2.5절 기준.

세션 상태는 QuizSession 한 행(items_json)에 들어 있다. 답변을 낼 때마다 Quiz 기록과
세션 위치를 같은 트랜잭션에서 저장하므로 앱을 닫아도 답변은 남는다.
- 그만하기(stop_session): 세션 행을 지운다. 이미 낸 답변 기록은 남는다.
- 앱 종료(save_and_exit): 세션을 지우지 않는다. 다음 실행 때 이어서 풀 수 있다.
- 같은 날 첫 기본 세션만 Progress에 반영한다. 재풀이와 보너스는 Quiz 기록만 남긴다 (FR-3.3-A, FR-3.4).
"""

import json
import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import session_scope
from domain.bonus import select_bonus
from domain.distractors import pick_distractor_candidates
from domain.quiz_builder import WordCandidate, build_quiz_plan, split_quiz_types
from logger import LOGGER_NAME
from models import Progress, Quiz, QuizSession, Word
from services.progress_service import apply_result
from services.settings_service import get_settings
from utils import today_local

log = logging.getLogger(LOGGER_NAME)

PHASE_BASIC = "basic"
PHASE_BONUS = "bonus"
QUIZ_TYPE_KO_TO_EN = "한→영"
QUIZ_TYPE_EN_TO_KO = "영→한"
ALL_CATEGORY_VALUES = ("선택안함", "전체")
SESSION_ID = 1
OPTION_COUNT = 4


class QuizSessionExistsError(RuntimeError):
    """이미 저장된 세션이 있다. 이어 풀기 또는 그만하기 후에 새로 시작한다."""


class QuizSessionNotFoundError(LookupError):
    pass


class NoWordsError(ValueError):
    """선택한 분야에 퀴즈로 쓸 단어가 없다."""


@dataclass(frozen=True)
class QuizAvailability:
    available: bool
    candidate_count: int


@dataclass(frozen=True)
class QuizItemView:
    index: int
    word_id: int
    quiz_type: str
    question: str
    options: list[str]
    answer_index: int
    selected_index: int | None
    is_correct: bool | None


@dataclass(frozen=True)
class QuizSessionView:
    session_id: int
    phase: str
    is_retry: bool
    requested_count: int
    total_count: int
    current_index: int
    items: list[QuizItemView]

    @property
    def shortage(self) -> int:
        """요청 문항 수보다 모자란 개수 (단어 부족, 보기 부족으로 빠진 문항 포함)."""
        return self.requested_count - self.total_count


@dataclass(frozen=True)
class AnswerResult:
    is_correct: bool
    correct_index: int
    finished: bool


@dataclass(frozen=True)
class SessionSummary:
    phase: str
    total_count: int
    answered_count: int
    correct_count: int


def _category_filter(selected_category: str | None) -> str | None:
    if selected_category is None or selected_category in ALL_CATEGORY_VALUES:
        return None
    return selected_category


def _load_candidates(session: Session, category: str | None) -> list[WordCandidate]:
    statement = select(Word, Progress).outerjoin(Progress, Progress.word_id == Word.id)
    if category is not None:
        statement = statement.where(Word.category == category)
    candidates: list[WordCandidate] = []
    for word, progress in session.execute(statement).all():
        attempts = (progress.correct_count + progress.wrong_count) if progress else 0
        candidates.append(WordCandidate(
            word_id=word.id,
            english=word.english,
            meaning=word.korean_meaning,
            level=word.level,
            category=word.category,
            attempts=attempts,
            correct_rate=progress.correct_rate if progress else None,
            last_reviewed=progress.last_reviewed_date if progress else None,
            next_review=progress.next_review_date if progress else None,
        ))
    return candidates


def _day_range(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def _has_basic_answers_on(session: Session, day: date) -> bool:
    """오늘 기본 퀴즈 답변이 이미 있으면 재풀이 세션이다 (FR-3.3-A)."""
    start, end = _day_range(day)
    count = session.scalar(
        select(func.count(Quiz.id)).where(
            Quiz.created_date >= start,
            Quiz.created_date < end,
            Quiz.is_bonus == False,  # noqa: E712
            Quiz.is_retry == False,  # noqa: E712
        )
    )
    return bool(count)


def _build_items(
    candidates: list[WordCandidate],
    word_ids: list[int],
    rng: random.Random,
) -> list[dict]:
    """단어마다 문항을 만든다. 보기가 3개 안 나오는 단어는 건너뛴다 (FR-3.1-E)."""
    by_id = {candidate.word_id: candidate for candidate in candidates}
    korean_count, _ = split_quiz_types(len(word_ids))
    quiz_types = [QUIZ_TYPE_KO_TO_EN] * korean_count + [QUIZ_TYPE_EN_TO_KO] * (len(word_ids) - korean_count)
    rng.shuffle(quiz_types)

    items: list[dict] = []
    for word_id, quiz_type in zip(word_ids, quiz_types):
        answer = by_id[word_id]
        distractors = pick_distractor_candidates(answer, candidates, rng)
        if distractors is None:
            log.info("보기 부족으로 문항 제외: word_id=%s", word_id)
            continue
        if quiz_type == QUIZ_TYPE_KO_TO_EN:
            question, correct = answer.meaning, answer.english
            wrong = [candidate.english for candidate in distractors]
        else:
            question, correct = answer.english, answer.meaning
            wrong = [candidate.meaning for candidate in distractors]
        options = [correct] + wrong
        order = list(range(OPTION_COUNT))
        rng.shuffle(order)
        items.append({
            "word_id": word_id,
            "quiz_type": quiz_type,
            "question": question,
            "options": [options[i] for i in order],
            "answer_index": order.index(0),
            "selected_index": None,
            "is_correct": None,
        })
    return items


def _to_view(row: QuizSession, items: list[dict], requested_count: int) -> QuizSessionView:
    return QuizSessionView(
        session_id=row.id,
        phase=row.phase,
        is_retry=row.is_retry,
        requested_count=requested_count,
        total_count=len(items),
        current_index=row.current_index,
        items=[
            QuizItemView(
                index=index,
                word_id=item["word_id"],
                quiz_type=item["quiz_type"],
                question=item["question"],
                options=list(item["options"]),
                answer_index=item["answer_index"],
                selected_index=item["selected_index"],
                is_correct=item["is_correct"],
            )
            for index, item in enumerate(items)
        ],
    )


def can_start_quiz(category: str | None = None) -> QuizAvailability:
    """선택한 분야에 퀴즈를 만들 단어가 있는지 확인한다."""
    with session_scope() as session:
        count = len(_load_candidates(session, _category_filter(category)))
    return QuizAvailability(available=count > 0, candidate_count=count)


def has_basic_answers_on(day: date) -> bool:
    """그날 기본 퀴즈 답변이 있는지. 준비 화면의 '다시 풀기' 안내에 쓴다."""
    with session_scope() as session:
        return _has_basic_answers_on(session, day)


def start_session(today: date | None = None, rng: random.Random | None = None) -> QuizSessionView:
    """오늘의 기본 퀴즈를 만들어 세션으로 저장한다 (FR-3.1, FR-3.2, FR-3.6)."""
    today = today or today_local()
    rng = rng or random.Random()
    settings = get_settings()
    requested = settings.daily_count
    with session_scope() as session:
        if session.get(QuizSession, SESSION_ID) is not None:
            raise QuizSessionExistsError("저장된 퀴즈가 있습니다. 이어서 풀거나 그만한 뒤 시작하세요.")
        candidates = _load_candidates(session, _category_filter(settings.selected_category))
        if not candidates:
            raise NoWordsError("선택한 분야에 퀴즈로 풀 단어가 없습니다.")

        is_retry = _has_basic_answers_on(session, today)
        plan = build_quiz_plan(candidates, total=requested, today=today, rng=rng)
        items = _build_items(candidates, plan.word_ids, rng)
        if not items:
            raise NoWordsError("문항을 만들 수 없습니다. 단어 수를 늘려 주세요.")

        row = QuizSession(
            id=SESSION_ID,
            session_date=today,
            phase=PHASE_BASIC,
            is_retry=is_retry,
            total_count=len(items),
            current_index=0,
            items_json=json.dumps(items, ensure_ascii=False),
            started_at=datetime.now(),
        )
        session.add(row)
        session.flush()
        log.info("퀴즈 세션 시작: %d문항 (요청 %d, 재풀이 %s)", len(items), requested, is_retry)
        return _to_view(row, items, requested)


def resume_session() -> QuizSessionView | None:
    """저장된 세션을 돌려준다. 이미 지워진 단어의 문항은 건너뛴다 (데이터 설계서 2.5절)."""
    with session_scope() as session:
        row = session.get(QuizSession, SESSION_ID)
        if row is None:
            return None
        items = json.loads(row.items_json)
        existing_ids = set(session.scalars(select(Word.id)).all())
        kept = [item for item in items if item["word_id"] in existing_ids]
        if len(kept) != len(items):
            log.info("재개 중 삭제된 단어 %d문항 제외", len(items) - len(kept))
            first_unanswered = next(
                (index for index, item in enumerate(kept) if item["selected_index"] is None),
                len(kept),
            )
            row.items_json = json.dumps(kept, ensure_ascii=False)
            row.total_count = len(kept)
            row.current_index = first_unanswered
        return _to_view(row, kept, requested_count=len(kept))


def submit_answer(session_id: int, item_index: int, selected_index: int) -> AnswerResult:
    """답변을 기록한다. Quiz 행 추가, 기본 첫 세션이면 Progress 갱신, 세션 위치 증가를 한 트랜잭션으로 한다."""
    today = today_local()
    with session_scope() as session:
        row = session.get(QuizSession, session_id)
        if row is None:
            raise QuizSessionNotFoundError("진행 중인 퀴즈 세션이 없습니다.")
        items = json.loads(row.items_json)
        if item_index != row.current_index:
            raise ValueError("이미 답한 문항이거나 순서가 맞지 않습니다.")
        item = items[item_index]
        if not 0 <= selected_index < OPTION_COUNT:
            raise ValueError("선택지 번호가 올바르지 않습니다.")

        is_correct = selected_index == item["answer_index"]
        item["selected_index"] = selected_index
        item["is_correct"] = is_correct
        session.add(Quiz(
            word_id=item["word_id"],
            quiz_type=item["quiz_type"],
            is_correct=is_correct,
            is_bonus=row.phase == PHASE_BONUS,
            is_retry=row.is_retry,
            created_date=datetime.now(),
        ))

        if row.phase == PHASE_BASIC and not row.is_retry:
            word = session.get(Word, item["word_id"])
            if word is not None:
                if word.progress is None:
                    word.progress = Progress(status="미학습", correct_count=0, wrong_count=0, consecutive_correct=0)
                apply_result(word.progress, is_correct, today)

        row.items_json = json.dumps(items, ensure_ascii=False)
        row.current_index = item_index + 1
        session.flush()
        return AnswerResult(
            is_correct=is_correct,
            correct_index=item["answer_index"],
            finished=row.current_index >= len(items),
        )


def start_bonus(rng: random.Random | None = None) -> QuizSessionView | None:
    """기본 퀴즈를 끝낸 뒤 보너스 세션을 만든다. 대상이 없으면 None (FR-3.4)."""
    rng = rng or random.Random()
    today = today_local()
    settings = get_settings()
    with session_scope() as session:
        row = session.get(QuizSession, SESSION_ID)
        if row is None or row.phase != PHASE_BASIC:
            raise ValueError("기본 퀴즈가 끝난 뒤에만 보너스를 시작할 수 있습니다.")
        items = json.loads(row.items_json)
        if row.current_index < len(items):
            raise ValueError("기본 퀴즈를 모두 푼 뒤에 보너스를 시작할 수 있습니다.")

        candidates = _load_candidates(session, _category_filter(settings.selected_category))
        basic_ids = {item["word_id"] for item in items}
        bonus_ids = select_bonus(candidates, exclude_ids=basic_ids, today=today)
        if not bonus_ids:
            return None

        bonus_items = _build_items(candidates, bonus_ids, rng)
        if not bonus_items:
            return None
        row.phase = PHASE_BONUS
        row.total_count = len(bonus_items)
        row.current_index = 0
        row.items_json = json.dumps(bonus_items, ensure_ascii=False)
        session.flush()
        log.info("보너스 세션 시작: %d문항", len(bonus_items))
        return _to_view(row, bonus_items, requested_count=len(bonus_items))


def finish_session() -> SessionSummary:
    """세션을 끝내고 결과를 돌려준다. 세션 행은 지운다."""
    with session_scope() as session:
        row = session.get(QuizSession, SESSION_ID)
        if row is None:
            raise QuizSessionNotFoundError("진행 중인 퀴즈 세션이 없습니다.")
        items = json.loads(row.items_json)
        answered = [item for item in items if item["selected_index"] is not None]
        summary = SessionSummary(
            phase=row.phase,
            total_count=len(items),
            answered_count=len(answered),
            correct_count=sum(1 for item in answered if item["is_correct"]),
        )
        session.delete(row)
        return summary


def stop_session() -> None:
    """그만하기: 세션 행을 지운다. 이미 낸 답변 기록은 남는다 (FR-3.6)."""
    with session_scope() as session:
        row = session.get(QuizSession, SESSION_ID)
        if row is not None:
            session.delete(row)
            log.info("그만하기: 퀴즈 세션 삭제")


def discard_session() -> None:
    """이어 풀기 화면의 [세션 버리기]. 그만하기와 같은 동작이다."""
    stop_session()


def save_and_exit() -> None:
    """앱 종료 시 호출한다. 세션은 답변마다 이미 저장되어 있으므로 지우지 않는다."""
    with session_scope() as session:
        row = session.get(QuizSession, SESSION_ID)
        if row is not None:
            log.info("앱 종료: 퀴즈 세션 유지 (%d/%d)", row.current_index, row.total_count)
