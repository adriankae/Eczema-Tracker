from __future__ import annotations

import json
import tomllib
from pathlib import Path

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

    def close(self):
        pass


class DummyConfig:
    base_url = "http://example"
    api_key = "k"
    timezone = "UTC"

    def normalized_base_url(self):
        return "http://example"


def _install_fake(monkeypatch, fake: FakeClient):
    monkeypatch.setattr(cli_module, "CzmClient", lambda *args, **kwargs: fake)
    monkeypatch.setattr(cli_module, "resolve_runtime_config", lambda **kwargs: DummyConfig())


def _day(status: str = "missed") -> dict:
    expected = 2 if status == "partial" else 1
    credited = 1 if status == "partial" else 0
    return {
        "date": "2026-04-03",
        "episode_id": 1,
        "subject_id": 1,
        "location_id": 1,
        "phase_number": 2,
        "expected_applications": expected,
        "completed_applications": credited,
        "credited_applications": credited,
        "status": status,
        "source": "calculated",
        "calculated_at": "2026-04-24T10:00:00Z",
        "finalized_at": None,
    }


def test_command_registration_and_entrypoints(capsys):
    parser = cli_module.build_parser()
    help_text = parser.format_help()
    assert "adherence" in help_text
    assert help_text.startswith("usage: zema")

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts["zema"] == "czm_cli.__main__:main"
    assert scripts["czm"] == "czm_cli.__main__:main"

    with pytest.raises(SystemExit):
        cli_module.main(["adherence", "--help"])
    assert "calendar" in capsys.readouterr().out


def test_calendar_request_params_and_json_output(monkeypatch, capsys):
    payload = {"days": [_day("partial")]}
    fake = FakeClient({("GET", "/adherence/calendar"): payload})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--json",
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "calendar",
            "--episode",
            "1",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
            "--persisted",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == payload
    assert fake.requests[-1] == (
        "GET",
        "/adherence/calendar",
        {"from": "2026-04-01", "to": "2026-04-30", "episode_id": 1, "persisted": True},
    )


def test_default_read_commands_do_not_force_persisted(monkeypatch):
    fake = FakeClient({("GET", "/adherence/summary"): _summary_payload()})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "summary",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
        ]
    )

    assert exit_code == 0
    assert fake.requests[-1] == ("GET", "/adherence/summary", {"from": "2026-04-01", "to": "2026-04-30"})


def test_missed_request_params(monkeypatch):
    fake = FakeClient({("GET", "/adherence/missed"): {"days": [_day("missed"), _day("partial")]}})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "missed",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
            "--include-partial",
        ]
    )

    assert exit_code == 0
    assert fake.requests[-1] == (
        "GET",
        "/adherence/missed",
        {"from": "2026-04-01", "to": "2026-04-30", "include_partial": True},
    )


def test_episode_request_params(monkeypatch):
    payload = {"episode_id": 7, "from": "2026-04-01", "to": "2026-04-30", "summary": _summary_payload(), "days": []}
    fake = FakeClient({("GET", "/episodes/7/adherence"): payload})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "episode",
            "7",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
            "--persisted",
        ]
    )

    assert exit_code == 0
    assert fake.requests[-1] == ("GET", "/episodes/7/adherence", {"from": "2026-04-01", "to": "2026-04-30", "persisted": True})


def test_rebuild_request_body(monkeypatch, capsys):
    payload = {"episodes_processed": 1, "rows_persisted": 30}
    fake = FakeClient({("POST", "/adherence/rebuild"): payload})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "rebuild",
            "--episode",
            "1",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
            "--source",
            "backfill",
        ]
    )

    assert exit_code == 0
    assert fake.requests[-1] == (
        "POST",
        "/adherence/rebuild",
        {"from": "2026-04-01", "to": "2026-04-30", "active_only": True, "source": "backfill", "episode_id": 1},
    )
    assert "Adherence rebuild complete" in capsys.readouterr().out


def test_last_n_date_range(monkeypatch):
    from czm_cli.commands import adherence as adherence_module

    monkeypatch.setattr(adherence_module, "local_today", lambda timezone_name: adherence_module.parse_local_date("2026-04-30"))
    fake = FakeClient({("GET", "/adherence/calendar"): {"days": []}})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "calendar",
            "--last",
            "7",
        ]
    )

    assert exit_code == 0
    assert fake.requests[-1] == ("GET", "/adherence/calendar", {"from": "2026-04-24", "to": "2026-04-30"})


def test_last_with_explicit_dates_is_usage_error(monkeypatch, capsys):
    fake = FakeClient({})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "adherence",
            "calendar",
            "--last",
            "7",
            "--from",
            "2026-04-01",
        ]
    )

    assert exit_code == EXIT_USAGE
    assert "--last cannot be combined" in capsys.readouterr().err


def test_subject_and_location_resolution(monkeypatch):
    fake = FakeClient(
        {
            ("GET", "/subjects"): {"subjects": [{"id": 2, "display_name": "Child"}]},
            ("GET", "/locations"): {"locations": [{"id": 3, "code": "left_elbow", "display_name": "Left elbow"}]},
            ("GET", "/adherence/calendar"): {"days": []},
        }
    )
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "calendar",
            "--subject",
            "Child",
            "--location",
            "left_elbow",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
        ]
    )

    assert exit_code == 0
    assert fake.requests[-1] == (
        "GET",
        "/adherence/calendar",
        {"from": "2026-04-01", "to": "2026-04-30", "subject_id": 2, "location_id": 3},
    )


def test_human_outputs(monkeypatch, capsys):
    fake = FakeClient(
        {
            ("GET", "/adherence/summary"): _summary_payload(),
            ("GET", "/adherence/calendar"): {"days": [_day("missed")]},
            ("GET", "/adherence/missed"): {"days": [_day("missed")]},
        }
    )
    _install_fake(monkeypatch, fake)

    assert cli_module.main(["--base-url", "http://example", "--api-key", "k", "adherence", "summary", "--from", "2026-04-01", "--to", "2026-04-30"]) == 0
    assert "Score: 85.0%" in capsys.readouterr().out

    assert cli_module.main(["--base-url", "http://example", "--api-key", "k", "adherence", "calendar", "--from", "2026-04-01", "--to", "2026-04-30"]) == 0
    assert "2026-04-03  missed  0/1  episode=1 phase=2" in capsys.readouterr().out

    assert cli_module.main(["--base-url", "http://example", "--api-key", "k", "adherence", "missed", "--from", "2026-04-01", "--to", "2026-04-30"]) == 0
    assert "Missed adherence days 2026-04-01 -> 2026-04-30" in capsys.readouterr().out


def test_backend_errors_preserve_existing_handling(monkeypatch, capsys):
    fake = FakeClient({("GET", "/adherence/calendar"): cli_module.CzmError("conflict happened", exit_code=EXIT_CONFLICT)})
    _install_fake(monkeypatch, fake)

    exit_code = cli_module.main(
        [
            "--json",
            "--base-url",
            "http://example",
            "--api-key",
            "k",
            "adherence",
            "calendar",
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-30",
        ]
    )

    assert exit_code == EXIT_CONFLICT
    assert json.loads(capsys.readouterr().out) == {"error": {"code": "conflict", "message": "conflict happened"}}


def _summary_payload() -> dict:
    return {
        "from": "2026-04-01",
        "to": "2026-04-30",
        "expected_applications": 20,
        "completed_applications": 18,
        "credited_applications": 17,
        "adherence_score": 0.85,
        "completed_days": 12,
        "partial_days": 2,
        "missed_days": 3,
        "not_due_days": 13,
        "future_days": 0,
    }
