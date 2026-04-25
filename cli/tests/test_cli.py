from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from czm_cli import cli as cli_module
from czm_cli.errors import EXIT_CONFLICT, EXIT_USAGE


class FakeClient:
    def __init__(self, responses: dict[tuple[str, str], object]):
        self.responses = responses
        self.requests = []

    def get(self, path, params=None):
        self.requests.append(("GET", path, params))
        response = self.responses[("GET", path)]
        if isinstance(response, Exception):
            raise response
        return response

    def post(self, path, json=None, params=None):
        self.requests.append(("POST", path, json))
        response = self.responses[("POST", path)]
        if isinstance(response, Exception):
            raise response
        return response

    def patch(self, path, json=None, params=None):
        self.requests.append(("PATCH", path, json))
        response = self.responses[("PATCH", path)]
        if isinstance(response, Exception):
            raise response
        return response

    def delete(self, path, json=None, params=None):
        self.requests.append(("DELETE", path, json))
        response = self.responses[("DELETE", path)]
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        pass


class DummyConfig:
    base_url = "http://example"
    api_key = "k"
    timezone = "UTC"

    def normalized_base_url(self):
        return "http://example"


def test_cli_json_output(monkeypatch, capsys):
    fake = FakeClient(
        {
            ("GET", "/subjects"): {"subjects": [{"id": 1, "display_name": "Child"}]},
        }
    )
    monkeypatch.setattr(cli_module, "CzmClient", lambda *args, **kwargs: fake)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", lambda **kwargs: DummyConfig())
    exit_code = cli_module.main(["--json", "--base-url", "http://example", "--api-key", "k", "subject", "list"])
    assert exit_code == 0
    output = capsys.readouterr().out.strip()
    assert json.loads(output) == {"subjects": [{"id": 1, "display_name": "Child"}]}


def test_cli_missing_config_exit_code(monkeypatch, capsys):
    from pathlib import Path

    monkeypatch.delenv("CZM_BASE_URL", raising=False)
    monkeypatch.delenv("CZM_API_KEY", raising=False)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", cli_module.resolve_runtime_config)
    monkeypatch.setattr("czm_cli.cli.resolve_runtime_config", cli_module.resolve_runtime_config)
    monkeypatch.setattr("czm_cli.config.xdg_config_path", lambda: Path("/tmp/nonexistent-czm-config.toml"))
    exit_code = cli_module.main(["subject", "list"])
    assert exit_code == EXIT_USAGE
    assert "missing required configuration" in capsys.readouterr().err


def test_cli_conflict_exit_code_json(monkeypatch, capsys):
    fake = FakeClient({("GET", "/subjects"): cli_module.CzmError("conflict happened", exit_code=EXIT_CONFLICT)})
    monkeypatch.setattr(cli_module, "CzmClient", lambda *args, **kwargs: fake)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", lambda **kwargs: DummyConfig())
    exit_code = cli_module.main(["--json", "--base-url", "http://example", "--api-key", "k", "subject", "list"])
    assert exit_code == EXIT_CONFLICT
    assert json.loads(capsys.readouterr().out) == {"error": {"code": "conflict", "message": "conflict happened"}}


def test_cli_json_preserves_datetime_payloads(monkeypatch, capsys):
    fake = FakeClient(
        {
            ("GET", "/episodes/1"): {
                "episode": {
                    "id": 1,
                    "subject_id": 1,
                    "location_id": 1,
                    "status": "active_flare",
                    "current_phase_number": 1,
                    "phase_started_at": datetime(2026, 4, 15, 23, 30, tzinfo=timezone.utc),
                    "phase_due_end_at": None,
                    "protocol_version": "v1",
                    "healed_at": None,
                    "obsolete_at": None,
                }
            }
        }
    )
    monkeypatch.setattr(cli_module, "CzmClient", lambda *args, **kwargs: fake)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", lambda **kwargs: DummyConfig())
    exit_code = cli_module.main(["--json", "--base-url", "http://example", "--api-key", "k", "episode", "get", "1"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["episode"]["phase_started_at"] == "2026-04-15T23:30:00Z"


def test_cli_setup_command(monkeypatch, tmp_path, capsys):
    from czm_cli.commands import setup as setup_module

    config_path = tmp_path / "config.toml"

    def fake_bootstrap_config(**kwargs):
        config_path.write_text("base_url = \"http://localhost:28173\"\napi_key = \"secret\"\ntimezone = \"UTC\"\n", encoding="utf-8")
        assert kwargs["base_url"] == "http://localhost:28173"
        assert kwargs["username"] == "admin"
        assert kwargs["password"] == "admin"
        assert kwargs["api_key_name"] == "czm-cli"
        assert kwargs["config_path"] == config_path
        return type("R", (), {"config_path": config_path, "base_url": kwargs["base_url"], "username": kwargs["username"], "api_key_name": kwargs["api_key_name"], "timezone": kwargs["timezone"]})()

    monkeypatch.setattr(setup_module, "bootstrap_config", fake_bootstrap_config)
    exit_code = cli_module.main(["setup", "--config", str(config_path)])
    assert exit_code == 0
    assert "Wrote config to" in capsys.readouterr().out
    assert config_path.exists()


def test_cli_setup_command_custom_base_url(monkeypatch, tmp_path):
    from czm_cli.commands import setup as setup_module

    config_path = tmp_path / "config.toml"
    custom_base_url = "http://backend-host:28173"

    def fake_bootstrap_config(**kwargs):
        assert kwargs["base_url"] == custom_base_url
        assert kwargs["config_path"] == config_path
        return type(
            "R",
            (),
            {
                "config_path": config_path,
                "base_url": kwargs["base_url"],
                "username": kwargs["username"],
                "api_key_name": kwargs["api_key_name"],
                "timezone": kwargs["timezone"],
            },
        )()

    monkeypatch.setattr(setup_module, "bootstrap_config", fake_bootstrap_config)
    exit_code = cli_module.main(["setup", "--config", str(config_path), "--base-url", custom_base_url])
    assert exit_code == 0


def test_cli_uses_configured_base_url(monkeypatch, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(
        'base_url = "http://backend-host:28173"\napi_key = "secret"\ntimezone = "UTC"\n',
        encoding="utf-8",
    )
    seen = {}

    class RecordingClient(FakeClient):
        def __init__(self, base_url, api_key, **kwargs):
            seen["base_url"] = base_url
            seen["api_key"] = api_key
            super().__init__({("GET", "/subjects"): {"subjects": []}})

    monkeypatch.setattr(cli_module, "CzmClient", RecordingClient)
    exit_code = cli_module.main(["--config", str(config), "subject", "list"])
    assert exit_code == 0
    assert seen["base_url"] == "http://backend-host:28173"
    assert seen["api_key"] == "secret"


def test_cli_setup_rejects_invalid_base_url(monkeypatch, tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    exit_code = cli_module.main(["setup", "--config", str(config_path), "--base-url", "not-a-url"])
    assert exit_code == EXIT_USAGE
    assert "base_url must be an http or https URL" in capsys.readouterr().err


def test_episode_relapse_uses_explicit_reason(monkeypatch):
    fake = FakeClient(
        {
            ("POST", "/episodes/1/relapse"): {
                "episode": {
                    "id": 1,
                    "subject_id": 1,
                    "location_id": 1,
                    "status": "active_flare",
                    "current_phase_number": 1,
                    "phase_started_at": "2026-04-15T18:00:00Z",
                    "phase_due_end_at": None,
                    "protocol_version": "v1",
                    "healed_at": None,
                    "obsolete_at": None,
                }
            }
        }
    )
    monkeypatch.setattr(cli_module, "CzmClient", lambda *args, **kwargs: fake)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", lambda **kwargs: DummyConfig())
    exit_code = cli_module.main(
        [
            "--json",
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "episode",
            "relapse",
            "1",
            "--reason",
            "symptoms_returned",
        ]
    )
    assert exit_code == 0
    assert fake.requests[-1] == (
        "POST",
        "/episodes/1/relapse",
        {"reason": "symptoms_returned"},
    )


def test_episode_relapse_defaults_reason_when_omitted(monkeypatch):
    fake = FakeClient(
        {
            ("POST", "/episodes/1/relapse"): {
                "episode": {
                    "id": 1,
                    "subject_id": 1,
                    "location_id": 1,
                    "status": "active_flare",
                    "current_phase_number": 1,
                    "phase_started_at": "2026-04-15T18:00:00Z",
                    "phase_due_end_at": None,
                    "protocol_version": "v1",
                    "healed_at": None,
                    "obsolete_at": None,
                }
            }
        }
    )
    monkeypatch.setattr(cli_module, "CzmClient", lambda *args, **kwargs: fake)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", lambda **kwargs: DummyConfig())
    exit_code = cli_module.main(
        [
            "--json",
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "episode",
            "relapse",
            "1",
            "--reported-at",
            "2026-04-15T21:00:00",
        ]
    )
    assert exit_code == 0
    assert fake.requests[-1] == (
        "POST",
        "/episodes/1/relapse",
        {"reason": "relapse", "reported_at": "2026-04-15T21:00:00Z"},
    )


def test_episode_relapse_help_text_marks_reason_optional(capsys):
    with pytest.raises(SystemExit):
        cli_module.main(["episode", "relapse", "--help"])
    out = capsys.readouterr().out
    assert "--reason" in out
    assert "Optional human-readable relapse reason" in out
