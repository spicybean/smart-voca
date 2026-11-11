#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 색상과 공통 스타일 (UI 설계서 v1.5 4장: 밝은 배경, 파란 포인트, 카드 구성)
# 파일 위치: src/ui/styles.py

"""색상, 크기, 공통 QSS. 화면마다 색 값을 따로 쓰지 않도록 여기에 모은다."""

PRIMARY = "#1976D2"        # 주색: 주요 버튼, 선택 메뉴, 진도 막대
PRIMARY_SOFT = "#E3F0FC"   # 선택 배경, 강조 배경
SUCCESS = "#2E7D32"        # 정답, 숙달
DANGER = "#D32F2F"         # 오답, 삭제, 초기화
WARNING = "#ED6C02"        # 복습필요, 재풀이·보너스 배지
INFO = "#0288D1"           # 학습중 배지
WHITE = "#FFFFFF"          # 기본 배경
CARD = "#F7F9FC"           # 카드 배경
TEXT = "#1F2937"           # 본문 글자
MUTED = "#6B7280"          # 보조 글자
BORDER = "#E5E7EB"         # 구분선, 테두리
SIDEBAR = "#F3F6FB"        # 사이드바 배경

STATUS_COLORS = {
    "숙달": SUCCESS,
    "학습중": INFO,
    "복습필요": WARNING,
    "미학습": MUTED,
}

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
SIDEBAR_WIDTH = 180

APP_STYLESHEET = f"""
QWidget {{ background: {WHITE}; color: {TEXT}; font-size: 12pt; }}
QListWidget#sidebar {{ background: {SIDEBAR}; border: none; padding-top: 12px; font-size: 13pt; }}
QListWidget#sidebar::item {{ padding: 12px 20px; border-radius: 8px; margin: 2px 10px; }}
QListWidget#sidebar::item:selected {{ background: {PRIMARY}; color: {WHITE}; }}
QListWidget#sidebar::item:hover:!selected {{ background: {PRIMARY_SOFT}; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel#title {{ font-size: 20pt; font-weight: bold; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#question {{ font-size: 28pt; font-weight: bold; }}
QLineEdit, QComboBox, QSpinBox {{ border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 10px; background: {WHITE}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {PRIMARY}; }}
QPushButton {{ padding: 8px 16px; border: 1px solid {BORDER}; border-radius: 8px; background: {WHITE}; }}
QPushButton:hover {{ border-color: {PRIMARY}; color: {PRIMARY}; }}
QPushButton:disabled {{ color: {MUTED}; background: {CARD}; }}
QPushButton#primary {{ background: {PRIMARY}; color: {WHITE}; border: none; font-weight: bold; padding: 10px 20px; }}
QPushButton#primary:hover {{ background: #1565C0; color: {WHITE}; }}
QPushButton#primary:disabled {{ background: {BORDER}; color: {MUTED}; }}
QPushButton#danger {{ background: {DANGER}; color: {WHITE}; border: none; }}
QPushButton#option {{ text-align: left; padding: 14px 18px; font-size: 15pt; }}
QProgressBar {{ border: none; border-radius: 4px; background: {BORDER}; height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 4px; }}
QTableWidget {{ border: none; gridline-color: {BORDER}; selection-background-color: {PRIMARY_SOFT}; selection-color: {TEXT}; }}
QHeaderView::section {{ background: {WHITE}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 8px; font-weight: bold; }}
"""
