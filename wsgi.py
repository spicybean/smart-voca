#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 서버 진입점 (gunicorn wsgi:app)
# 파일 위치: wsgi.py

"""서버는 이 파일의 app 객체를 gunicorn 으로 띄운다 (Dockerfile CMD)."""

from app import create_app

app = create_app()
