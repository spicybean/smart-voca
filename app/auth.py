#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 회원가입, 로그인, 로그아웃, 현재 계정 확인 (VOCA-FR-041~042, 이슈 #10)
# 파일 위치: app/auth.py

"""계정은 이름과 비밀번호 해시로 저장한다. 세션에는 계정 번호만 넣는다 (VOCA-FR-042)."""

import re

from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import User, db

bp = Blueprint("auth", __name__)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD = 8


def current_user_id() -> int | None:
    return session.get("user_id")


def current_user() -> User | None:
    user_id = current_user_id()
    return db.session.get(User, user_id) if user_id is not None else None


def _log_in(user: User) -> None:
    session.clear()
    session["user_id"] = user.id


@bp.route("/signup")
def signup_page():
    return render_template("signup.html")


@bp.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    if not USERNAME_PATTERN.match(username):
        flash("아이디는 영문, 숫자, 밑줄(_) 3~20자로 정해 주세요.", "error")
        return redirect("/signup")
    if len(password) < MIN_PASSWORD:
        flash(f"비밀번호는 {MIN_PASSWORD}자 이상이어야 합니다.", "error")
        return redirect("/signup")
    if password != confirm:
        flash("비밀번호 확인이 맞지 않습니다.", "error")
        return redirect("/signup")
    if db.session.scalar(db.select(User).where(User.username == username)) is not None:
        flash("이미 있는 아이디입니다.", "error")
        return redirect("/signup")
    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    _log_in(user)
    flash(f"{username} 님, 가입을 환영합니다.", "ok")
    return redirect("/")


@bp.route("/login")
def login_page():
    return render_template("login.html")


@bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = db.session.scalar(db.select(User).where(User.username == username))
    if user is None or not check_password_hash(user.password_hash, password):
        # 아이디가 없는지 비밀번호가 틀린지는 알려 주지 않는다
        flash("아이디 또는 비밀번호가 맞지 않습니다.", "error")
        return redirect("/login")
    _log_in(user)
    return redirect("/")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("로그아웃했습니다.", "ok")
    return redirect("/")
