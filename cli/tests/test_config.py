from __future__ import annotations

from pathlib import Path

import pytest

from czm_cli.errors import ConfigError
from czm_cli.config import DEFAULT_BASE_URL, resolve_runtime_config


def test_config_precedence(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text('base_url = "http://file.example"\napi_key = "file-key"\ntimezone = "Europe/Paris"\n', encoding="utf-8")
    monkeypatch.setenv("CZM_BASE_URL", "http://env.example")
    monkeypatch.setenv("CZM_API_KEY", "env-key")
    monkeypatch.setenv("CZM_TIMEZONE", "UTC")
    resolved = resolve_runtime_config(base_url="http://flag.example", api_key="flag-key", timezone="Asia/Tokyo", config_path=config)
    assert resolved.base_url == "http://flag.example"
    assert resolved.api_key == "flag-key"
    assert resolved.timezone == "Asia/Tokyo"


def test_config_uses_env_then_file(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text('base_url = "http://file.example"\napi_key = "file-key"\n', encoding="utf-8")
    monkeypatch.setenv("CZM_BASE_URL", "http://env.example")
    monkeypatch.setenv("CZM_API_KEY", "env-key")
    resolved = resolve_runtime_config(base_url=None, api_key=None, timezone=None, config_path=config)
    assert resolved.base_url == "http://env.example"
    assert resolved.api_key == "env-key"
    assert resolved.timezone == "UTC"


def test_config_defaults_base_url_when_missing(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text('api_key = "file-key"\n', encoding="utf-8")
    monkeypatch.delenv("CZM_BASE_URL", raising=False)
    monkeypatch.delenv("CZM_API_KEY", raising=False)
    resolved = resolve_runtime_config(base_url=None, api_key=None, timezone=None, config_path=config)
    assert resolved.base_url == DEFAULT_BASE_URL
    assert resolved.api_key == "file-key"


def test_config_missing(monkeypatch, tmp_path: Path):
    config = tmp_path / "config.toml"
    config.write_text("", encoding="utf-8")
    monkeypatch.delenv("CZM_BASE_URL", raising=False)
    monkeypatch.delenv("CZM_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        resolve_runtime_config(base_url=None, api_key=None, timezone=None, config_path=config)
