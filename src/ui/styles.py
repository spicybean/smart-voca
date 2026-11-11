#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 색상과 공통 스타일 상수 (UI 설계서 4장)
# 파일 위치: src/ui/styles.py

"""색상과 공통 스타일. 화면마다 색 값을 따로 쓰지 않도록 여기에 모은다."""

PRIMARY = "#4CAF50"      # 진행 바, 정답, 주요 버튼, 숙달 배지
SECONDARY = "#2196F3"    # 탭 선택, 버튼 호버, 학습중 배지
DANGER = "#F44336"       # 오답, 삭제, 경고, 초기화
WARNING = "#FF9800"      # 복습필요 배지, 재풀이·보너스 배지
BACKGROUND = "#F5F5F5"   # 윈도우 배경
TEXT = "#333333"         # 일반 텍스트
BORDER = "#CCCCCC"       # 테이블 경계, 구분선

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700

APP_STYLESHEET = f"""
QMainWindow, QWidget {{ background-color: {BACKGROUND}; color: {TEXT}; }}
QTabBar::tab:selected {{ color: {SECONDARY}; font-weight: bold; }}
QPushButton {{ padding: 6px 14px; border: 1px solid {BORDER}; border-radius: 4px; background: white; }}
QPushButton:hover {{ border-color: {SECONDARY}; }}
QPushButton#primary {{ background: {PRIMARY}; color: white; border: none; }}
QPushButton#danger {{ background: {DANGER}; color: white; border: none; }}
"""
