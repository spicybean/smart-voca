# Dockerfile 생성 프롬프트

> v1.0 (2026-11-24). 블록 오른쪽 위 복사 버튼을 눌러 AI 도구(Claude, ChatGPT 등)에 붙여 넣으세요.

## 쓰는 법

1. 아래 **공통 프롬프트**를 복사합니다.
2. 내 스택에 맞는 **스택별 추가문**을 하나 복사해 공통 프롬프트 뒤에 붙입니다.
3. 맨 아래 `[내 앱 정보]` 를 내 앱에 맞게 고칩니다.
4. 리포 코드와 함께 AI에게 줍니다. Claude Code처럼 리포를 직접 읽는 도구라면 리포 폴더에서 실행합니다.
5. AI가 준 파일을 넣고 푸시한 뒤, **점검 워크플로가 초록이 되는지** 확인합니다. 실패하면 Actions 로그를 AI에게 보여 주고 고치게 합니다.

> AI가 답변 끝에 "직접 확인할 것"을 줍니다. 꼭 읽으세요. 특히 코드에 남은 `localhost` 주소와 변수로 만든 주소를 확인해야 합니다.

## 공통 프롬프트

```prompt
내 단어장 웹 앱을 학교 서버에 배포할 수 있게 Dockerfile과 관련 파일을 만들어 줘.
서버는 아래 조건으로 내 앱을 실행한다. 이 조건에서 그대로 동작해야 한다.
조건마다 이유를 적었으니, 필요하면 코드도 함께 고쳐 줘.

[서버 실행 조건]
1. 리포 루트에서 `docker build .` 한 번으로 이미지를 만든다.
   - 공식 이미지를 쓰고 버전 태그를 적는다(latest 금지). slim 계열을 쓴다.
2. 컨테이너는 0.0.0.0:8080 에서 들어야 한다. (localhost 로 들으면 서버 프록시가 닿지 않는다)
3. 앱은 / 를 기준으로 만든다. 서버가 /2026/voca-<학번>/ 아래로 옮겨 주면서 HTML·CSS·JS 안의 주소를 바꿔 준다.
   서버가 주소를 찾아 바꿀 수 있도록 다음을 지킨다.
   - 주소는 "/login" 처럼 / 로 시작하거나 "login" 처럼 상대 경로로 쓴다. http://localhost:8080 같은 호스트는 쓰지 않는다.
   - HTML 속성은 따옴표로 감싼다: href="/login" (href=/login 처럼 쓰지 않는다)
   - JS 에서는 fetch("/api/words") 처럼 호출하는 자리에 주소를 문자열로 쓴다.
     const API = "/api" 처럼 주소 앞부분을 변수로 빼지 않는다.
   - 주소를 JSON 응답에 담아 내려 주지 않는다.
4. 서버는 컨테이너를 UID 10001, 모든 리눅스 권한 제거(cap-drop ALL) 상태로 실행한다.
   - Dockerfile 에서 UID 10001 사용자를 만들고 마지막에 USER 로 지정한다.
   - 실행 중에 root 권한이 필요한 일(chown, 패키지 설치, 1024 미만 포트)을 하지 않는다.
5. DB 는 SQLite 를 쓴다.
   - 파일 위치는 환경변수 DB_PATH (값 /data/voca.db) 를 따른다.
   - Dockerfile 에서 /data 를 만들고 소유자를 10001 로 한다. (서버가 붙이는 저장 공간이 이 소유자를 물려받는다)
   - 처음 실행하면 테이블을 자동으로 만든다.
   - 실행 중 파일 쓰기는 /data 와 /tmp 에만 할 수 있다. 업로드한 CSV 는 메모리에서 처리한다.
6. 실행 중에는 인터넷에 접속할 수 없다. 의존성은 빌드할 때 모두 설치한다.
7. 비밀값(세션 키 등)을 코드나 이미지에 넣지 않는다. 세션 키는 환경변수 SECRET_KEY 로 받고, 없으면 실행 시 무작위로 만든다.
8. 운영용 서버로 실행한다(개발 서버, 자동 재시작, debug 모드 금지). CMD 는 ["...", "..."] 형식으로 쓴다.
9. 서버는 격리된 빌더로 빌드한다. Dockerfile 에 다음을 쓰지 않는다:
   첫 줄 # syntax= 지시어, RUN --mount=type=ssh 또는 type=secret, RUN --network=..., RUN --security=...

[함께 만들 파일]
- Dockerfile: 의존성 파일을 먼저 COPY 해서 설치한 뒤 소스를 COPY 한다.
- .dockerignore: .git, 가상환경, node_modules, __pycache__, *.db, .env, IDE 설정 제외
- .gitattributes: `* text=auto eol=lf` (내 PC 가 Windows 라 줄바꿈 문제 예방)
- 의존성 파일: 실제로 쓰는 패키지만, 버전 고정 (Windows 전용 패키지가 들어가지 않게)
- .github/workflows/docker-check.yml 은 학교에서 받은 파일을 그대로 쓰므로 만들거나 고치지 않는다.

[답변 형식]
1. 고친 파일과 새로 만든 파일 전체 내용
2. 위 조건 1~9 각각을 어느 파일 어느 부분에서 지켰는지 표로
3. 내가 직접 확인해야 할 것 (예: 코드에 남은 localhost 주소, 변수로 만든 주소)

[내 앱 정보]
- 스택: (예: Python 3.13 + Flask, 템플릿은 Jinja2)
- 시작 파일: (예: app.py 의 app 객체)
- DB 접속 코드 위치: (예: db.py)
```

## 스택별 추가문

### Flask

```prompt
[Flask 참고]
- 실행은 gunicorn --bind 0.0.0.0:8080 --workers 2 <모듈>:<앱> 으로 한다.
- 템플릿 링크는 url_for 를 써도 되고 "/login" 처럼 써도 된다.
- base 이미지는 python:3.13-slim, 환경 PYTHONDONTWRITEBYTECODE=1, PYTHONUNBUFFERED=1, pip 는 --no-cache-dir.
```

### FastAPI

```prompt
[FastAPI 참고]
- 실행은 uvicorn <모듈>:<앱> --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips "*" 로 한다.
- root_path 는 설정하지 않는다 (서버가 경로를 처리한다).
- base 이미지는 python:3.13-slim, pip 는 --no-cache-dir.
```

### Express (Node.js)

```prompt
[Express 참고]
- app.listen(8080, "0.0.0.0") 으로 듣는다.
- SQLite 는 better-sqlite3 를 쓴다. 네이티브 모듈이라 alpine 말고 node:24-slim 을 쓴다.
- 설치는 package-lock.json 과 npm ci --omit=dev, 환경 NODE_ENV=production, 실행은 node <시작 파일>.
```

### React·Vue 등 따로 빌드하는 프론트엔드 (권하지 않음)

기말 과제는 서버 템플릿과 바닐라 JS로 충분합니다. 꼭 쓰려면 아래를 붙이세요.

```prompt
[SPA 참고]
- 빌드 설정의 base 를 "./" 로 한다 (Vite: base: "./").
- 라우터는 해시 방식(createHashRouter, createWebHashHistory)을 쓴다.
- 빌드는 Dockerfile 의 첫 단계(multi-stage)에서 하고, 결과물만 백엔드가 서빙한다.
```

## PostgreSQL을 허락받은 경우만

공통 프롬프트의 **5번을 통째로 지우고** 아래로 바꿉니다. 허락받지 않았다면 쓰지 마세요.

```prompt
5. DB 는 PostgreSQL 17 을 쓴다.
   - 환경변수 DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS 로 접속한다.
   - 서버에서 DB 가 앱보다 늦게 뜰 수 있으니 접속을 몇 초 간격으로 재시도한다.
   - 처음 실행하면 테이블을 자동으로 만든다.
   - 실행 중 파일 쓰기는 /tmp 에만 한다. 업로드한 CSV 는 메모리에서 처리한다.
   - 드라이버: Python 은 psycopg[binary], Node 는 pg 를 쓴다.
```
