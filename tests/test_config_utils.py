#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-11 - 스마트보카 - 설정·경로·공용 유틸 단위 테스트
# 파일 위치: tests/test_config_utils.py

import sys
from datetime import date

import pytest

import config
from utils import normalize_english, resource_path, today_local


def test_default_mode_is_dev_under_pytest(monkeypatch):
    monkeypatch.delenv("SMARTVOCA_DEV", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert config.is_dev_mode() is True


def test_frozen_build_is_deploy_mode(monkeypatch):
    monkeypatch.delenv("SMARTVOCA_DEV", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert config.is_dev_mode() is False


def test_env_flag_forces_dev_mode_even_when_frozen(monkeypatch):
    monkeypatch.setenv("SMARTVOCA_DEV", "1")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert config.is_dev_mode() is True


def test_dev_mode_paths_live_inside_project(monkeypatch):
    monkeypatch.setenv("SMARTVOCA_DEV", "1")
    assert config.get_db_path() == config.PROJECT_ROOT / "data" / "smart_voca.db"
    assert config.get_backup_dir() == config.PROJECT_ROOT / "backups"
    assert config.get_log_dir() == config.PROJECT_ROOT / "logs"


@pytest.mark.skipif(sys.platform != "win32", reason="APPDATA 경로는 Windows 기준")
def test_deploy_mode_paths_live_in_app_data(monkeypatch, tmp_path):
    monkeypatch.delenv("SMARTVOCA_DEV", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert config.get_db_path() == tmp_path / "SmartVoca" / "smart_voca.db"
    assert config.get_log_dir() == tmp_path / "SmartVoca" / "logs"


def test_normalize_english_strips_surrounding_spaces_only():
    assert normalize_english("  Apple ") == "Apple"


def test_today_local_returns_a_date():
    assert isinstance(today_local(), date)


def test_resource_path_is_relative_to_project_root_in_dev(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert resource_path("data/words_common.csv") == config.PROJECT_ROOT / "data" / "words_common.csv"


def test_resource_path_uses_meipass_when_bundled(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_path("data/words_common.csv") == tmp_path / "data" / "words_common.csv"
