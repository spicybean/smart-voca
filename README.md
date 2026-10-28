# 스마트보카 (Smart-Voca)

간격 반복 학습과 사전 API를 활용한 **영단어 개인 학습 시스템** (PyQt 데스크톱 앱)

> **현재 상태**: 🚀 기획 단계 (2026-10-21 시작)
> **기술 스택**: Python 3.11+ | PyQt5/6 | SQLite

---

## 📋 프로젝트 개요

스마트보카는 학생이 **과학적 학습 방법**과 **신뢰성 높은 예문**을 결합하여 영단어를 효율적으로 학습하는 웹 기반 시스템입니다.

### 핵심 특징

- **간격 반복 (Spaced Repetition)**: Ebbinghaus 망각곡선 기반 학습
- **사전 API 연동**: 공식 영어 사전에서 자동으로 예문 조회
- **진도 추적**: 개인의 단어별 습득 상태 실시간 시각화
- **능동적 회상**: 객관식, 단답형 퀴즈로 강화된 학습

---

## 🎯 주요 기능 (v1.0)

| 기능 | 설명 |
|------|------|
| **단어 등록/관리** | 학습할 단어를 등록하고 관리 |
| **예문 자동 조회** | 단어별 사전 기반 예문 3~5개 표시 |
| **간격 반복 퀴즈** | 약한 단어는 자주, 강한 단어는 천천히 복습 |
| **학습 진도 추적** | 단어별 습득도 및 진도 상황 확인 |

---

## 🛠️ 기술 스택

| 계층 | 기술 |
|------|------|
| **언어** | Python 3.11+ |
| **GUI 프레임워크** | PyQt5 또는 PyQt6 |
| **프론트엔드** | PyQt (Python 기반) |
| **데이터베이스** | SQLite |
| **ORM** | SQLAlchemy |
| **외부 API** | WordsAPI / Cambridge Dictionary |
| **배포** | PyInstaller (.exe / .app) |

---

## 📦 설치 (개발자용)

### 요구사항
- Python 3.11 이상
- pip (Python 패키지 관리자)
- 인터넷 연결 (사전 API 호출용)

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
├── requirements.txt              # Python 의존성
├── docs/                         # 승인된 최종 산출물
├── ai-agent/
│   ├── claude/                   # Claude 작업 디렉토리
│   │   └── 기획_261021_스마트보카 프로젝트 기획서 v1.0.md
│   ├── uploads/                  # 외부 참고자료
│   └── scripts/
│       └── init_db.py            # DB 초기화 스크립트
├── src/                          # 소스 코드
│   ├── main.py                   # PyQt 앱 진입점
│   ├── app.py                    # PyQt 메인 윈도우
│   ├── models.py                 # DB 모델 (SQLAlchemy)
│   ├── database.py               # DB 연결
│   ├── ui/                       # PyQt UI 화면들
│   │   ├── home_widget.py        # 홈 화면
│   │   ├── quiz_widget.py        # 퀴즈 화면
│   │   ├── word_widget.py        # 단어 관리 화면
│   │   └── settings_widget.py    # 설정 화면
│   └── utils.py                  # 유틸리티 함수
├── data/                         # 데이터
│   ├── smart_voca.db             # SQLite DB
│   ├── words_common.csv          # 일상 단어 (1,000개)
│   └── words_business.csv        # 비즈니스 단어 (500개)
└── dist/                         # 빌드 결과 (배포용)
    ├── SmartVoca.exe             # Windows 설치 파일
    └── SmartVoca.app             # Mac 설치 파일
```

---

## 📖 문서

- **프로젝트 기획서**: `ai-agent/claude/기획_261021_스마트보카 프로젝트 기획서 v1.0.md`
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
- API 호출 및 에러 처리
- PyQt UI 이벤트

---

## 🚀 빌드 및 배포

### Windows 배포
```bash
# 1. PyInstaller로 exe 생성
pyinstaller --onefile --windowed --add-data "data:data" --name "SmartVoca" src/main.py

# 2. 결과: dist/SmartVoca.exe
# 3. 사용자에게 배포
```

### Mac 배포
```bash
# 1. PyInstaller로 app 생성
pyinstaller --onefile --windowed --add-data "data:data" \
  --osx-bundle-identifier=com.smartvoca --name "SmartVoca" src/main.py

# 2. 결과: dist/SmartVoca.app
# 3. dmg로 변환 (선택사항)
hdiutil create -volname "SmartVoca" -srcfolder dist -ov -format UDZO SmartVoca.dmg
```

### 최종 사용자 설치
```
1. SmartVoca.exe (또는 SmartVoca.app) 다운로드
2. 설치 프로그램 또는 앱 실행
3. 첫 실행 시 DB 자동 초기화
4. 학습 시작!
```

---

## 📝 개발 진행 상황

### v1.0 (진행 중)
- [ ] 기획 (완료 ✅ 2026-10-21)
- [ ] 요구사항 분석
- [ ] 시스템 설계
- [ ] 기능 구현
- [ ] 테스트 및 배포

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
