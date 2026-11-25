# 스마트보카 (영단어 학습 웹 앱)

AI기반프로그래밍 2026-2 기말과제 제출 리포입니다. 영단어를 등록하고, 하루 학습량에 따라 일차별로 카드를 외우고, 시험으로 확인하는 웹 앱입니다.

## 구현한 요구사항 ID

| 요구 ID | 내용 | 구현 |
|---|---|---|
| VOCA-FR-001 | 영단어와 뜻 직접 입력 | 구현 (`/words`) |
| VOCA-FR-002 | 단어 목록 보기 | 구현 (`/words`) |
| VOCA-FR-003 | 수정, 삭제 | 구현 (`/words/<id>/edit`, `/words/<id>/delete`) |
| VOCA-FR-004 | CSV 일괄 등록 (중복 처리 정책 문서화) | 구현 (`/words/import`) |
| VOCA-FR-004 | 영단어 또는 뜻으로 검색 | 구현 (`/words?q=`) |
| VOCA-FR-011 | 하루 학습량에 따른 일차별 진도 | 구현 (`/memorize`) |
| VOCA-FR-012 | 카드 한 장씩 보고 뜻 확인 | 구현 (`/memorize`) |
| VOCA-FR-013 | 이전 일차 단어와 자주 틀린 단어 섞기 | 구현 (`app/study_service.py`) |
| VOCA-FR-014 | 암기 이력(사용자, 시각, 단어, 일차) DB 저장 | 구현 (`study_log` 테이블) |
| VOCA-FR-021 | 문제 수 지정 | 구현 (`/exam`) |
| VOCA-FR-022 | 미시험·오래된·자주 틀린 단어가 더 많이 출제 | 구현 (`app/exam_service.py` 가중치) |
| VOCA-FR-023 | 출제 방향 (영→한, 한→영, 섞기) | 구현 (`/exam`) |
| VOCA-FR-024 | 출제 형식 2가지 이상 (단답형, 4지선다, OX) | 구현 (세 형식 모두) |
| VOCA-FR-025 | 점수, 틀린 문항과 정답 표시 | 구현 (`/exam/<id>/result`) |
| VOCA-FR-026 | 문항 단위 이력 (단어, 형식, 방향, 정오, 시각) DB 저장 | 구현 (`exam_item` 테이블) |
| VOCA-FR-031 | 현재 일차, 암기 단어 수 / 전체 수 | 구현 (`/`, `/stats`) |
| VOCA-FR-032 | 날짜별 정답률 추이, 회차별 점수 | 구현 (`/stats`) |
| VOCA-FR-033 | 자주 틀리는 단어 상위 10개 | 구현 (`/stats`) |
| VOCA-FR-034 | 통계는 DB 이력으로 계산 | 구현 (`app/stats_service.py`) |
| VOCA-FR-041~043 | 로그인, 비밀번호 해시, 계정별 이력 (도전) | 미구현 |
| VOCA-FR-051~053 | 다른 계정 이력 보기 (도전) | 미구현 |
| VOCA-FR-061~062 | 설정 (도전) | 부분 구현: 하루 학습량만 (`/memorize`) |

## 기술 스택

- Python 3.13, Flask 3.1 (서버 템플릿과 폼으로 화면을 만든다. 자바스크립트 없이 동작)
- SQLite (Flask-SQLAlchemy 3.1, SQLAlchemy 2.1)
- 운영 서버: gunicorn 23.0
- 배포: Dockerfile (학교 서버 조건: 0.0.0.0:8080, UID 10001, `/data/voca.db`, 인터넷 없이 실행)

## 실행 방법

### 개발 PC (Windows)

```
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements-dev.txt
venv\Scripts\python.exe -m pytest -q
venv\Scripts\python.exe -m flask --app wsgi run --port 8080
```

브라우저에서 `http://127.0.0.1:8080/` 를 엽니다. 개발 DB는 `data/voca.db` 에 만들어집니다 (`DB_PATH` 환경변수로 바꿀 수 있음). 개발 서버 명령은 개발용이며, 서버 이미지는 gunicorn으로 실행합니다.

### 서버 이미지 (Docker)

```
docker build -t voca-app .
docker run --rm -p 8080:8080 -e SECRET_KEY=change-me -v voca-data:/data voca-app
```

컨테이너는 `gunicorn --bind 0.0.0.0:8080 wsgi:app` 로 실행되고, DB는 `/data/voca.db` 에 저장됩니다.

## 단어 CSV 등록

`/words/import` 에서 CSV 파일을 올립니다. 첫 줄은 `영단어,뜻`, 인코딩은 UTF-8, 20MB 이하입니다.

- 이미 있는 단어(대소문자·공백 무시)와 파일 안에서 두 번째로 나온 같은 단어는 건너뜁니다. 먼저 나온 뜻을 씁니다.
- 영문자·공백·하이픈·아포스트로피만 있는 영단어만 받고, 나머지는 줄 번호와 함께 건너뛰었다고 알려 줍니다.

저장소 루트의 `단어사전_샘플.csv`(2,000행)를 올리면 1,998개가 추가되고, 중복 1개(`peck`), 형식 오류 1개(`gin하해`)가 건너뛰어집니다.

## 환경변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `DB_PATH` | `data/voca.db` | SQLite 파일 위치. 서버는 `/data/voca.db` |
| `SECRET_KEY` | 실행할 때마다 무작위 | 세션 서명 키. 서버에서는 환경변수로 준다 |

비밀값은 코드나 이미지에 넣지 않습니다. `.env` 는 커밋하지 않습니다.

## 프로젝트 구조

```
app/              Flask 앱 (설정, 모델, 서비스, 라우트, 템플릿, 정적 파일)
tests/            pytest 테스트
wsgi.py           서버 진입점 (gunicorn wsgi:app)
Dockerfile        서버 이미지
.github/workflows/docker-check.yml   과제 제공 점검 워크플로 (수정하지 않음)
docs/             기획·분석·설계 산출물
CLAUDE.md         AI 협업 지침과 작업 흐름
```

## 테스트

```
venv\Scripts\python.exe -m pytest -q
```

테스트는 임시 DB를 쓰므로 `data/voca.db` 를 건드리지 않습니다.

## 선택한 DB

SQLite. 과제 기본 DB이며, PostgreSQL은 사용하지 않습니다.

## 작성자

학생 (실명·학번은 과제 제출 규칙에 따라 적지 않음)
