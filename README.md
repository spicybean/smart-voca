# 스마트보카 (Smart-Voca)

간격 반복 학습과 기본 예문을 활용한 **영단어 개인 학습 시스템** (PyQt6 데스크톱 앱)

> **현재 상태**: 🛠️ 설계 완료, 구현 시작 전 (기획 2026-10-21 시작, 설계 확정 2026-11-11)
> **기술 스택**: Python 3.11+ | PyQt6 | SQLite

---

## 📋 프로젝트 개요

스마트보카는 학생이 **과학적 학습 방법**과 **예문**을 결합하여 영단어를 효율적으로 학습하는 PyQt6 데스크톱 시스템입니다.

### 핵심 특징

- **간격 반복 (Spaced Repetition)**: Ebbinghaus 망각곡선 기반 학습
- **기본 예문 제공**: 기본 단어마다 예문 3개를 CSV로 함께 제공 (외부 API 없이 오프라인 동작). 예문은 전수 검수하지 않았으므로 품질 확인이 필요합니다
- **진도 추적**: 개인의 단어별 습득 상태 실시간 시각화
- **능동적 회상**: 객관식, 단답형 퀴즈로 강화된 학습

---

## 🎯 주요 기능 (v1.0)

| 기능 | 설명 |
|------|------|
| **단어 등록/관리** | 학습할 단어를 등록하고 관리 |
| **예문 제공** | 기본 단어는 예문 3개 표시, 직접 추가한 단어는 학생이 예문 입력 |
| **간격 반복 퀴즈** | 약한 단어는 자주, 강한 단어는 천천히 복습 |
| **학습 진도 추적** | 단어별 습득도 및 진도 상황 확인 |

---

## 🛠️ 기술 스택

| 계층 | 기술 |
|------|------|
| **언어** | Python 3.11+ |
| **GUI 프레임워크** | PyQt6 |
| **프론트엔드** | PyQt (Python 기반) |
| **데이터베이스** | SQLite |
| **ORM** | SQLAlchemy 2.x |
| **배포** | PyInstaller (.exe / .app) |

---

## 📦 설치 (개발자용)

### 요구사항
- Python 3.11 이상
- pip (Python 패키지 관리자)

### 개발 환경 설정

```bash
# 1. 프로젝트 디렉토리로 이동
cd smart-voca

# 2. 가상 환경 생성 (권장)
python -m venv venv

# 3. 가상 환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. 의존성 설치
pip install -r requirements.txt

# 5. CSV 데이터로 DB 초기화 (첫 실행 시만)
python ai-agent/scripts/init_db.py
```

---

## ▶️ 실행

### 개발 중 (소스코드에서 직접 실행)
```bash
python src/main.py
```

PyQt 윈도우 창이 열립니다.

### 배포 후 (최종 사용자)
```bash
# Windows
SmartVoca.exe 더블클릭

# Mac
SmartVoca.app 더블클릭
```

**첫 실행 시**: DB 자동 초기화 → 설정 화면 → 학습 시작!

---

## 📁 프로젝트 구조

```
smart-voca/
├── CLAUDE.md                     # Claude Code 운용 지침
├── README.md                     # 본 문서
├── requirements.txt              # Python 의존성 (구현 단계에서 작성)
├── .env.example                  # 환경 변수 예시 (값은 비움)
├── docs/                         # 승인된 최종 산출물
├── ai-agent/
│   ├── claude/                   # Claude 작업 디렉토리 (기획·분석·설계 문서)
│   ├── uploads/                  # 외부 참고자료
│   └── scripts/
│       └── init_db.py            # DB 초기화 스크립트 (얇은 CLI 래퍼)
├── src/                          # 소스 코드 (구현 단계에서 작성)
│   ├── main.py                   # 진입점
│   ├── config.py                 # 경로, 환경 변수, 실행 모드
│   ├── logger.py                 # 로깅 설정
│   ├── utils.py                  # 공용 유틸
│   ├── database.py               # engine, session
│   ├── models.py                 # SQLAlchemy 모델 (7개 테이블)
│   ├── domain/                   # 순수 로직 (간격 반복, 퀴즈 구성, 보기, 보너스)
│   ├── services/                 # 유스케이스 조율 (단어, 예문, 퀴즈, 진도, 설정, 백업)
│   └── ui/                       # PyQt6 화면 (메인 창, 홈, 퀴즈, 단어, 설정)
├── tests/                        # pytest 단위 테스트 (구현 단계에서 작성)
├── data/                         # 초기 데이터 (Git 추적)
│   ├── words_common.csv          # 일상 단어 (1,000개)
│   └── words_business.csv        # 비즈니스 단어 (500개)
└── dist/                         # 빌드 결과 (배포용, Git 제외)
    ├── SmartVoca.exe             # Windows 실행 파일 (1차 배포)
    └── SmartVoca.app             # Mac 실행 파일 (후속 단계)

> 개발 중 DB는 `data/smart_voca.db`, 배포 exe의 DB는 `%APPDATA%\SmartVoca\smart_voca.db`에 생성된다 (시스템 구조 설계서 ADR-03).
```

---

## 📖 문서

- **프로젝트 기획서**: `docs/기획_261111_스마트보카 프로젝트 기획서 v1.3.md`
- **요구사항 명세서**: `docs/분석_261111_요구사항명세서 v1.4.md`
- **데이터 설계서**: `docs/분석_261111_데이터설계서 v1.3.md`
- **UI 설계서**: `docs/분석_261111_UI설계서 v1.3.md`
- **시스템 구조 설계서**: `docs/설계_261111_시스템 구조 v1.2.md`
- **개발 방법론**: `docs/개발방법론__AIsw.md`
- **Claude Code 지침**: `CLAUDE.md`

---

## 🧪 테스트 (구현 후)

```bash
# 단위 테스트 실행
pytest tests/ -v

# UI 테스트 (수동)
python src/main.py  # 실행 후 각 탭/기능 테스트

# 커버리지 확인
pytest --cov=src tests/
```

**테스트 항목**:
- 퀴즈 알고리즘 (보기 선정, 간격 반복)
- DB 쿼리 (단어 조회, 진도 업데이트)
- PyQt UI 이벤트

---

## 🚀 빌드 및 배포

### Windows 배포
```bash
# 1. PyInstaller로 exe 생성
pyinstaller --onefile --windowed --add-data "data/words_common.csv;data" --add-data "data/words_business.csv;data" --name "SmartVoca" src/main.py

# 2. 결과: dist/SmartVoca.exe (CSV만 포함, DB는 포함하지 않음)
# 3. 사용자에게 exe 파일 1개를 직접 전달 (설치 프로그램 없음)
```

### Mac 배포 (후속 단계, Mac 환경에서 빌드)
```bash
# 1. PyInstaller로 app 생성
pyinstaller --onefile --windowed --add-data "data/words_common.csv:data" --add-data "data/words_business.csv:data" \
  --osx-bundle-identifier=com.smartvoca --name "SmartVoca" src/main.py

# 2. 결과: dist/SmartVoca.app
```

### 최종 사용자 설치
```
1. SmartVoca.exe 파일 받기 (Python 설치 불필요)
2. 실행
3. 첫 실행 시 DB 자동 생성 (%APPDATA%\SmartVoca\)
4. 학습 시작!
```

---

## 📝 개발 진행 상황

### v1.0 (진행 중)
- [x] 기획 (완료 ✅ 2026-11-04, 기획서 v1.1)
- [x] 요구사항 분석 (완료 ✅ 2026-11-11, 요구사항 명세서 v1.2)
- [x] 시스템 설계 (완료 ✅ 2026-11-11, 데이터·UI 설계서 v1.2, 시스템 구조 설계서 v1.0)
- [ ] 기능 구현 (미착수, 다음: M1 `src/domain/` + 단위 테스트)
- [ ] 테스트 및 배포 (미착수)

### 인프라
- [x] Git 저장소 및 GitHub 연동 (2026-10-28, private 저장소 `spicybean/smart-voca`)

---

## 🤝 기여 및 문의

이 프로젝트는 학생 개인 학습용입니다.

질문이나 피드백은 프로젝트 작성자에게 문의하세요.

---

## 📄 라이선스

개인 프로젝트 (라이선스 미정)

---

**작성자**: 260312 박중희  
**시작일**: 2026-10-21  
**상태**: 🚀 기획 단계
