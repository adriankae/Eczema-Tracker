from __future__ import annotations

from pathlib import Path

import httpx
import json

from czm_cli.bootstrap import bootstrap_config


def test_bootstrap_config_writes_file(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/login":
            assert json.loads(request.content) == {"username": "admin", "password": "admin"}
            return httpx.Response(200, json={"access_token": "token"})
        if request.url.path == "/api-keys":
            assert request.headers["authorization"] == "Bearer token"
            return httpx.Response(200, json={"plaintext_key": "secret-key"})
        raise AssertionError(f"unexpected request {request.url.path}")

    config_path = tmp_path / "config.toml"
    result = bootstrap_config(
        base_url="http://localhost:28173",
        username="admin",
        password="admin",
        api_key_name="czm-cli",
        timezone="Europe/Berlin",
        config_path=config_path,
        transport=httpx.MockTransport(handler),
    )
    assert result.config_path == config_path
    assert config_path.read_text(encoding="utf-8") == (
        'base_url = "http://localhost:28173"\n'
        'api_key = "secret-key"\n'
        'timezone = "Europe/Berlin"\n'
    )
