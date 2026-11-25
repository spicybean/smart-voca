#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - Flask 앱 생성 (DB 연결, 테이블 자동 생성, 라우트 등록)
# 파일 위치: app/__init__.py

"""앱 팩토리. 서버는 wsgi.py 의 app 객체를 gunicorn 으로 띄운다."""

from pathlib import Path

from flask import Flask, render_template

from app.config import MAX_UPLOAD_BYTES, get_db_path, get_secret_key
from app.models import db


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

    from app.views import bp
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="페이지를 찾을 수 없습니다."), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("error.html", message="파일이 너무 큽니다. 20MB 이하로 올려 주세요."), 413

    return app
