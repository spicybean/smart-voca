#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 화면 라우트 (단어, 암기, 시험, 통계). 모든 주소는 / 기준 (R-04)
# 파일 위치: app/views.py

"""화면 라우트. 입력 확인은 서비스 계층이 하고, 여기서는 요청을 연결만 한다."""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request

from app import exam_service, settings_service, stats_service, study_service, word_service
from app.auth import current_user, current_user_id
from app.models import ExamSession, User, Word, db

bp = Blueprint("voca", __name__)

# 로그인 없이 볼 수 있는 화면 (처음 화면은 로그인 안내를 보여 준다)
PUBLIC_ENDPOINTS = {"voca.index"}


@bp.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if current_user_id() is None:
        flash("로그인한 뒤 이용할 수 있습니다.", "error")
        return redirect("/login")
    return None


def _own_session(session_id: int) -> ExamSession:
    """다른 계정의 시험 회차는 찾을 수 없는 것으로 보여 준다."""
    session = db.get_or_404(ExamSession, session_id)
    if session.user_id != current_user_id():
        abort(404)
    return session


@bp.route("/")
def index():
    if current_user_id() is None:
        return render_template("index.html", progress=None)
    return render_template("index.html", progress=stats_service.progress_summary(current_user_id()))


# 단어 (VOCA-FR-001~004) ------------------------------------------------

@bp.route("/words")
def words():
    query = request.args.get("q", "")
    return render_template(
        "words.html",
        words=word_service.search_words(query),
        query=query,
        total=word_service.count_words(),
    )


@bp.route("/words", methods=["POST"])
def add_word():
    try:
        word_service.add_word(request.form.get("english", ""), request.form.get("meaning", ""))
        flash("단어를 추가했습니다.", "ok")
    except word_service.WordError as error:
        flash(str(error), "error")
    return redirect("/words")


@bp.route("/words/<int:word_id>/edit")
def edit_word(word_id: int):
    word = db.get_or_404(Word, word_id)
    return render_template("word_edit.html", word=word)


@bp.route("/words/<int:word_id>/edit", methods=["POST"])
def update_word(word_id: int):
    try:
        word_service.update_word(word_id, request.form.get("english", ""), request.form.get("meaning", ""))
        flash("단어를 수정했습니다.", "ok")
        return redirect("/words")
    except word_service.WordError as error:
        flash(str(error), "error")
        return redirect(f"/words/{word_id}/edit")


@bp.route("/words/<int:word_id>/delete", methods=["POST"])
def delete_word(word_id: int):
    word_service.delete_word(word_id)
    flash("단어를 삭제했습니다. 이 단어의 암기·시험 기록도 함께 지워집니다.", "ok")
    return redirect("/words")


@bp.route("/words/import")
def import_page():
    return render_template("import.html")


@bp.route("/words/import", methods=["POST"])
def import_words():
    uploaded = request.files.get("file")
    if uploaded is None or uploaded.filename == "":
        flash("CSV 파일을 골라 주세요.", "error")
        return redirect("/words/import")
    try:
        report = word_service.import_csv(uploaded.read())
    except word_service.WordError as error:
        flash(str(error), "error")
        return redirect("/words/import")
    return render_template("import_result.html", report=report)


# 암기 (VOCA-FR-011~014) -------------------------------------------------

@bp.route("/memorize")
def memorize():
    today = study_service.current_day(current_user_id())
    day_no = request.args.get("day", type=int) or today
    last_day = study_service.total_days()
    if last_day == 0:
        return render_template("memorize.html", empty=True, day_no=1, last_day=0)
    if not 1 <= day_no <= last_day:
        abort(404)

    card_ids = study_service.day_word_ids(day_no, current_user_id())
    index = request.args.get("i", default=0, type=int)
    if index >= len(card_ids):
        return render_template("memorize_done.html", day_no=day_no, last_day=last_day, count=len(card_ids))
    word = db.session.get(Word, card_ids[index])
    return render_template(
        "memorize.html",
        empty=False,
        day_no=day_no,
        last_day=last_day,
        index=index,
        total=len(card_ids),
        word=word,
        reveal=request.args.get("reveal") == "1",
        daily=study_service.get_daily_amount(),
        min_daily=study_service.MIN_DAILY_AMOUNT,
        max_daily=study_service.MAX_DAILY_AMOUNT,
    )


@bp.route("/memorize/answer", methods=["POST"])
def memorize_answer():
    word_id = request.form.get("word_id", type=int)
    day_no = request.form.get("day", type=int)
    index = request.form.get("i", type=int)
    action = request.form.get("action", "")
    if word_id is None or day_no is None or index is None:
        abort(400)
    study_service.record_card(word_id, day_no, action, current_user_id())
    return redirect(f"/memorize?day={day_no}&i={index + 1}")


@bp.route("/memorize/daily", methods=["POST"])
def set_daily():
    try:
        study_service.set_daily_amount(request.form.get("daily_amount", type=int) or 0)
        flash("하루 학습량을 바꿨습니다. 일차 구성이 바뀝니다.", "ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect("/memorize")


# 시험 (VOCA-FR-021~026) -------------------------------------------------

@bp.route("/exam")
def exam_setup():
    return render_template(
        "exam_setup.html",
        formats=exam_service.FORMAT_LABELS,
        directions=exam_service.DIRECTION_LABELS,
        max_questions=exam_service.MAX_QUESTIONS,
        learned=len(study_service.memorized_words(current_user_id())),
        today=study_service.current_day(current_user_id()),
        defaults=settings_service.get_exam_defaults(),
    )


@bp.route("/exam/start", methods=["POST"])
def exam_start():
    formats = request.form.getlist("formats")
    try:
        session = exam_service.create_session(
            count=request.form.get("count", type=int) or 0,
            direction_mode=request.form.get("direction", ""),
            formats=formats,
            user_id=current_user_id(),
            day_from=request.form.get("day_from", type=int),
            day_to=request.form.get("day_to", type=int),
        )
    except exam_service.ExamError as error:
        flash(str(error), "error")
        return redirect("/exam")
    return redirect(f"/exam/{session.id}")


@bp.route("/exam/<int:session_id>")
def exam_question(session_id: int):
    session = _own_session(session_id)
    item = exam_service.current_item(session)
    if item is None:
        return redirect(f"/exam/{session_id}/result")
    choices = json.loads(item.choices) if item.choices else []
    return render_template(
        "exam_question.html",
        session=session,
        item=item,
        choices=choices,
        number=exam_service.progress(session)[0] + 1,
        total=exam_service.progress(session)[1],
        direction_label=exam_service.DIRECTION_LABELS.get(item.direction, ""),
        format_label=exam_service.FORMAT_LABELS.get(item.fmt, ""),
    )


@bp.route("/exam/<int:session_id>/answer", methods=["POST"])
def exam_answer(session_id: int):
    session = _own_session(session_id)
    given = request.form.get("answer", "")
    try:
        exam_service.answer_item(session, given)
    except exam_service.ExamError as error:
        flash(str(error), "error")
    if session.status == "done":
        return redirect(f"/exam/{session_id}/result")
    return redirect(f"/exam/{session_id}")


@bp.route("/exam/<int:session_id>/result")
def exam_result(session_id: int):
    session = _own_session(session_id)
    if session.status != "done":
        return redirect(f"/exam/{session_id}")
    correct, total = exam_service.score(session)
    return render_template(
        "exam_result.html",
        session=session,
        correct=correct,
        total=total,
        wrong=exam_service.wrong_items(session),
        rate=round(correct * 100 / total) if total else 0,
    )


# 통계 (VOCA-FR-031~034) -------------------------------------------------

@bp.route("/stats")
def stats():
    return render_template(
        "stats.html",
        title="내 학습 통계",
        progress=stats_service.progress_summary(current_user_id()),
        trend=stats_service.daily_accuracy_trend(current_user_id()),
        history=stats_service.session_history(current_user_id()),
        frequent=stats_service.frequent_wrong_words(10, current_user_id()),
    )


@bp.route("/users")
def users():
    """통계를 공개한 계정 목록 (VOCA-FR-051). 읽기 전용."""
    public = db.session.scalars(db.select(User).where(User.stats_public == True).order_by(User.username))  # noqa: E712
    return render_template("users.html", users=list(public))


@bp.route("/users/<int:user_id>/stats")
def user_stats(user_id: int):
    """다른 계정의 통계는 공개한 계정만 본다. 읽기 전용 (VOCA-FR-051~053)."""
    owner = db.get_or_404(User, user_id)
    me = current_user()
    if not owner.stats_public and owner.id != me.id:
        abort(404)
    return render_template(
        "stats.html",
        title=f"{owner.username} 님의 학습 통계",
        progress=stats_service.progress_summary(owner.id),
        trend=stats_service.daily_accuracy_trend(owner.id),
        history=stats_service.session_history(owner.id),
        frequent=stats_service.frequent_wrong_words(10, owner.id),
    )


# 설정 (VOCA-FR-061~062) -------------------------------------------------

@bp.route("/settings")
def settings_page():
    return render_template(
        "settings.html",
        daily=study_service.get_daily_amount(),
        min_daily=study_service.MIN_DAILY_AMOUNT,
        max_daily=study_service.MAX_DAILY_AMOUNT,
        review_percent=settings_service.get_review_percent(),
        min_review=settings_service.MIN_REVIEW_PERCENT,
        max_review=settings_service.MAX_REVIEW_PERCENT,
        exam=settings_service.get_exam_defaults(),
        stats_public=current_user().stats_public,
        formats=exam_service.FORMAT_LABELS,
        directions=exam_service.DIRECTION_LABELS,
        max_questions=exam_service.MAX_QUESTIONS,
    )


@bp.route("/settings", methods=["POST"])
def save_settings():
    try:
        study_service.set_daily_amount(request.form.get("daily_amount", type=int) or 0)
        settings_service.set_review_percent(request.form.get("review_percent", type=int) or 0)
        me = current_user()
        me.stats_public = request.form.get("stats_public") == "1"
        settings_service.set_exam_defaults(
            count=request.form.get("exam_count", type=int) or 0,
            direction=request.form.get("exam_direction", ""),
            formats=request.form.getlist("exam_formats"),
            allowed_directions=exam_service.DIRECTION_LABELS,
            allowed_formats=exam_service.FORMAT_LABELS,
            max_count=exam_service.MAX_QUESTIONS,
        )
        flash("설정을 저장했습니다.", "ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect("/settings")
