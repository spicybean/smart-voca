# 스마트보카 서버 이미지 (학교 서버 조건: 0.0.0.0:8080, UID 10001, SQLite /data/voca.db, 인터넷 없이 실행)
# 규칙 근거: 과제 Dockerfile 구성 문서 R-01~R-16
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/voca.db

WORKDIR /app

# 의존성을 먼저 설치한다 (빌드 때만 인터넷 사용, R-07, R-13)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 실행 사용자 UID 10001 과 쓰기 가능한 /data 를 만든다 (빌드 단계에서만 root, R-05, R-06)
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin voca \
    && mkdir -p /data \
    && chown 10001:10001 /data

COPY app ./app
COPY wsgi.py ./

EXPOSE 8080

# 실행은 권한 없는 사용자로 한다 (마지막 USER, R-05)
USER 10001:10001

# 운영용 서버, exec 형식 (R-14, R-15)
# --preload: 앱(테이블 생성, 단어 등록)을 워커 띄우기 전에 한 번만 만든다. 워커 2개가 동시에 만들면 충돌한다.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--preload", "wsgi:app"]
