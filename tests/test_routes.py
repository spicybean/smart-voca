#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - 스마트보카 - 화면 흐름 테스트 (단어, 암기, 시험, 통계) 및 서버 경로 규칙 (R-04)
# 파일 위치: tests/test_routes.py

import io
import re
from pathlib import Path

from app.models import Word, db

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "좋은 하루예요".encode() in response.data


def test_add_word_through_form(client, ctx):
    client.post("/words", data={"english": "apple", "meaning": "사과"})

    assert db.session.scalar(db.select(Word).where(Word.english == "apple")) is not None


def test_duplicate_word_shows_message(client, seeded):
    response = client.post("/words", data={"english": "APPLE", "meaning": "x"}, follow_redirects=True)

    assert "이미 등록된 단어입니다".encode() in response.data


def test_word_list_search(client, seeded):
    response = client.get("/words?q=river")

    assert "강".encode() in response.data
    assert b"window" not in response.data


def test_import_csv_upload_shows_result(client, ctx):
    raw = "영단어,뜻\nbook,책\nbook,책2\n".encode("utf-8-sig")
    response = client.post(
        "/words/import",
        data={"file": (io.BytesIO(raw), "words.csv")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert "추가 1개".encode() in response.data


def test_memorize_flow_records_card(client, seeded):
    first = client.get("/memorize?day=1&i=0&reveal=1")
    assert first.status_code == 200

    word = db.session.scalar(db.select(Word).order_by(Word.id))
    response = client.post(
        "/memorize/answer",
        data={"word_id": word.id, "day": 1, "i": 0, "action": "known"},
    )

    assert response.status_code == 302
    assert "/memorize?day=1&i=1" in response.headers["Location"]


def test_memorize_day_out_of_range_is_404(client, seeded):
    assert client.get("/memorize?day=99").status_code == 404


def test_exam_flow_from_start_to_result(client, seeded):
    response = client.post("/exam/start", data={"count": "2", "direction": "en_ko", "formats": ["short"]})
    assert response.status_code == 302
    session_url = response.headers["Location"]

    for _ in range(2):
        question = client.get(session_url)
        assert question.status_code == 200
        client.post(f"{session_url}/answer", data={"answer": "모름"})

    result = client.get(f"{session_url}/result")

    assert result.status_code == 200
    assert "시험 결과".encode() in result.data


def test_exam_start_without_format_shows_error(client, seeded):
    response = client.post("/exam/start", data={"count": "2", "direction": "en_ko"}, follow_redirects=True)

    assert "출제 형식".encode() in response.data


def test_stats_page_loads(client, seeded):
    response = client.get("/stats")

    assert response.status_code == 200
    assert "학습 통계".encode() in response.data


def test_templates_use_root_relative_quoted_links():
    """R-04: 주소는 / 로 시작하고 HTML 속성은 따옴표로 감싼다. 호스트 주소는 쓰지 않는다."""
    for path in TEMPLATES.glob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert "localhost" not in text, path.name
        assert not re.search(r"(href|src|action)=[^\"' >]", text), path.name
        assert not re.search(r"(href|src|action)=\"https?://", text), path.name


def test_exam_keeps_working_after_word_deleted_mid_exam(client, seeded):
    """이슈 #9: 시험 중 단어를 지워도 문항 화면과 답 제출이 계속 동작한다."""
    response = client.post("/exam/start", data={"count": "3", "direction": "en_ko", "formats": ["short"]})
    session_url = response.headers["Location"]
    first = client.get(session_url)
    assert first.status_code == 200

    word = db.session.scalar(db.select(Word).order_by(Word.id))
    client.post(f"/words/{word.id}/delete")

    for _ in range(3):
        page = client.get(session_url)
        assert page.status_code in (200, 302)
        if page.status_code == 302:
            break
        client.post(f"{session_url}/answer", data={"answer": "모름"})

    result = client.get(f"{session_url}/result")
    assert result.status_code == 200
