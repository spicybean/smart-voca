#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - Flask 앱 생성 (DB 연결, 테이블 자동 생성, 라우트 등록)
# 파일 위치: app/__init__.py

"""앱 팩토리. 서버는 wsgi.py 의 app 객체를 gunicorn 으로 띄운다."""

import hmac
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, render_template, request, session
from sqlalchemy import event
from sqlalchemy.engine import Engine

import logging

from app.config import MAX_UPLOAD_BYTES, SEED_CSV_PATH, get_db_path, get_secret_key
from app.models import db

log = logging.getLogger(__name__)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite는 외래키를 기본으로 끈다. 켜야 단어 삭제 때 기록이 ON DELETE CASCADE로 함께 지워진다 (이슈 #8)."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _csrf_token() -> str:
    """세션마다 토큰 하나를 만들어 폼에 넣는다 (외부 패키지 없이 구현)."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def _seed_words_once() -> None:
    """처음 실행할 때 단어 CSV를 한 번 넣는다. 이미 넣었으면 다시 넣지 않는다 (삭제한 단어가 되살아나지 않게)."""
    from app.models import Setting
    from app.word_service import count_words, import_csv

    if db.session.get(Setting, "seeded") is not None:
        return
    if count_words() == 0:
        report = import_csv(SEED_CSV_PATH.read_bytes())
        log.info("처음 실행: 단어 %d개 등록", report.added)
    db.session.add(Setting(key="seeded", value="1"))
    db.session.commit()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_secret_key()
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

    db_path = Path(get_db_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    if app.config.get("SEED_WORDS", True):
        with app.app_context():
            _seed_words_once()

    from app.auth import bp as auth_bp
    from app.views import bp
    app.register_blueprint(bp)
    app.register_blueprint(auth_bp)
    app.config.setdefault("CSRF_ENABLED", True)

    @app.context_processor
    def inject_common():
        from app.auth import current_user

        return {"csrf_token": _csrf_token, "me": current_user()}

    @app.before_request
    def check_csrf():
        """POST 요청은 세션의 토큰과 폼의 csrf_token 이 같을 때만 처리한다 (이슈 #14)."""
        if not app.config["CSRF_ENABLED"] or request.method != "POST":
            return None
        expected = session.get("csrf_token")
        sent = request.form.get("csrf_token", "")
        if not expected or not sent or not hmac.compare_digest(expected, sent):
            return render_template("error.html", message="요청을 확인할 수 없습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요."), 400
        return None

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("error.html", message="파일이 너무 큽니다. 20MB 이하로 올려 주세요."), 413

    return app
