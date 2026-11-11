#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 도메인 규칙 상수 (임계값, 간격 표, 비율)
# 파일 위치: src/domain/rules.py

"""요구사항 명세서 v1.2의 규칙 값을 한 곳에 모은다.

값을 바꿀 때 로직 코드는 건드리지 않아도 되도록 상수만 둔다.
"""

# FR-3.1: 신규·약한 단어 기준 (정답률이 이 값 미만이면 약한 단어)
WEAK_RATE_THRESHOLD = 70

# FR-3.1, FR-3.4: 자주 틀린 단어 기준 (정답률이 이 값 미만)
WRONG_RATE_THRESHOLD = 60

# FR-3.1, FR-3.4: 마지막 복습 후 이 일수 이상 지나야 자주 틀린 단어로 본다
STALE_DAYS = 7

# FR-4.0: 숙달 기준 (연속 정답 횟수)
MASTERED_STREAK = 5

# FR-4.0: 연속 정답 횟수별 다음 복습까지 간격(일). 5회 이상은 마지막 값(30일)을 쓴다.
REVIEW_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}

# FR-4.0: 오답이면 다음 복습은 이 간격(일) 후
WRONG_INTERVAL_DAYS = 1

# FR-3.1-A: 자주 틀린 단어 기본 비율
RATIO_WRONG = 0.10

# FR-3.1-A: 복습 대상 기본 비율
RATIO_REVIEW = 0.20

# FR-3.4: 보너스 문제 최대 개수
BONUS_MAX = 5

# FR-3.1-E: 4지선다 문항에 필요한 단어 수 (정답 1 + 오답 3)
MIN_OPTION_WORDS = 4

# FR-3.1-E: 보기 선정 시 허용하는 난이도 차이 (±1)
DISTRACTOR_LEVEL_RANGE = 1
