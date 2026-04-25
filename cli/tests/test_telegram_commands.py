from __future__ import annotations

import inspect
import asyncio

import pytest

from czm_cli.config import AppConfig, TelegramConfig
from czm_cli.errors import CzmError
from czm_cli.telegram.commands import TelegramCommandContext, handle_text_command
from czm_cli.telegram.parser import parse_telegram_command


class FakeClient:
    def __init__(self):
        self.requests = []

    def get(self, path, params=None):
        self.requests.append(("GET", path, params))
        if path == "/health":
            return {"status": "ok"}
        if path == "/subjects":
            return {"subjects": [{"id": 1, "display_name": "Child A"}]}
        if path == "/locations":
            return {"locations": [{"id": 2, "code": "left_elbow", "display_name": "Left elbow"}]}
        if path == "/episodes":
            return {
                "episodes": [
                    {
                        "id": 12,
                        "subject_id": 1,
                        "location_id": 2,
                        "status": "active_flare",
                        "current_phase_number": 1,
                    }
                ]
            }
        if path == "/episodes/12":
            return {
                "episode": {
                    "id": 12,
                    "subject_id": 1,
                    "location_id": 2,
                    "status": "active_flare",
                    "current_phase_number": 1,
                }
            }
        if path == "/episodes/due":
            return {"due": [{"episode_id": 12, "subject_id": 1, "location_id": 2, "current_phase_number": 1, "treatment_due_today": True}]}
        if path == "/episodes/12/events":
            return {"events": [{"id": 1, "event_type": "episode_created", "occurred_at": "2026-04-01T00:00:00Z"}]}
        if path == "/episodes/12/timeline":
            return {"timeline": [{"id": 1, "event_type": "episode_created", "occurred_at": "2026-04-01T00:00:00Z"}]}
        if path == "/adherence/summary":
            return {
                "from": "2026-04-01",
                "to": "2026-04-30",
                "expected_applications": 10,
                "credited_applications": 8,
                "adherence_score": 0.8,
                "missed_days": 2,
            }
        if path == "/adherence/calendar":
            return {
                "days": [
                    {
                        "date": "2026-04-01",
                        "status": "completed",
                        "credited_applications": 1,
                        "expected_applications": 1,
                        "episode_id": 12,
                        "phase_number": 2,
                    }
                ]
            }
        if path == "/adherence/missed":
            return {
                "days": [
                    {
                        "date": "2026-04-02",
                        "status": "missed",
                        "credited_applications": 0,
                        "expected_applications": 1,
                        "episode_id": 12,
                        "phase_number": 2,
                    }
                ]
            }
        raise AssertionError(path)

    def post(self, path, json=None, params=None):
        self.requests.append(("POST", path, json))
        if path == "/subjects":
            return {"id": 3, "display_name": json["display_name"]}
        if path == "/locations":
            return {"location": {"id": 4, "code": json["code"], "display_name": json["display_name"]}}
        if path == "/episodes":
            return {
                "episode": {
                    "id": 13,
                    "subject_id": json["subject_id"],
                    "location_id": json["location_id"],
                    "status": "active_flare",
                    "current_phase_number": 1,
                }
            }
        if path == "/applications":
            return {"application": {"id": 5, "episode_id": json["episode_id"]}}
        if path == "/adherence/rebuild":
            return {"episodes_processed": 1, "rows_persisted": 30}
        raise AssertionError(path)


def make_ctx(*, allow_writes=True, allow_rebuild=True):
    config = AppConfig(
        timezone="UTC",
        telegram=TelegramConfig(
            bot_token="token",
            allowed_chat_ids=[123],
            allow_writes=allow_writes,
            allow_adherence_rebuild=allow_rebuild,
        ),
    )
    client = FakeClient()
    return TelegramCommandContext(config=config, client=client), client


def test_parser_parses_key_values_and_quotes():
    parsed = parse_telegram_command('/episode_create subject:"Child A" location:left_elbow')
    assert parsed.command == "episode_create"
    assert parsed.options == {"subject": "Child A", "location": "left_elbow"}


def test_parser_rejects_zema_passthrough_and_shell_like_text():
    with pytest.raises(CzmError):
        parse_telegram_command("/zema subject list")
    with pytest.raises(CzmError):
        parse_telegram_command("/subjects; rm -rf /")


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/status", ("GET", "/health")),
        ("/subjects", ("GET", "/subjects")),
        ("/subject_create Child A", ("POST", "/subjects")),
        ("/locations", ("GET", "/locations")),
        ("/location_create left_knee Left knee", ("POST", "/locations")),
        ("/episodes", ("GET", "/episodes")),
        ("/episode 12", ("GET", "/episodes/12")),
        ('/episode_create subject:"Child A" location:left_elbow', ("POST", "/episodes")),
        ("/due", ("GET", "/episodes/due")),
        ("/log episode:12", ("POST", "/applications")),
        ("/events episode:12", ("GET", "/episodes/12/events")),
        ("/timeline episode:12", ("GET", "/episodes/12/timeline")),
        ("/adherence 30", ("GET", "/adherence/summary")),
        ("/adherence_calendar episode:12 days:30", ("GET", "/adherence/calendar")),
        ("/adherence_missed episode:12 days:30", ("GET", "/adherence/missed")),
        ("/adherence_rebuild episode:12 from:2026-04-01 to:2026-04-30", ("POST", "/adherence/rebuild")),
    ],
)
def test_command_mapping(text, expected):
    ctx, client = make_ctx()
    reply = run(handle_text_command(ctx, text))
    assert reply
    assert any(request[0] == expected[0] and request[1] == expected[1] for request in client.requests)


def test_write_command_rejected_when_writes_disabled():
    ctx, _ = make_ctx(allow_writes=False)
    with pytest.raises(CzmError) as exc:
        run(handle_text_command(ctx, "/subject_create Child A"))
    assert "write commands are disabled" in str(exc.value)


def test_adherence_rebuild_rejected_when_disabled():
    ctx, _ = make_ctx(allow_rebuild=False)
    with pytest.raises(CzmError) as exc:
        run(handle_text_command(ctx, "/adherence_rebuild episode:12 from:2026-04-01 to:2026-04-30"))
    assert "adherence rebuild is disabled" in str(exc.value)


def test_parser_module_does_not_use_subprocess():
    import czm_cli.telegram.parser as parser_module
    import czm_cli.telegram.commands as commands_module

    assert "subprocess" not in inspect.getsource(parser_module)
    assert "subprocess" not in inspect.getsource(commands_module)
