from __future__ import annotations

import json

import pytest

from czm_cli import cli as cli_module
from czm_cli.config import AppConfig, TelegramConfig, apply_env_overrides
from czm_cli.errors import EXIT_USAGE


def write_config(path):
    path.write_text(
        "\n".join(
            [
                'base_url = "http://localhost:28173"',
                'api_key = "secret-api-key"',
                'timezone = "Europe/Berlin"',
                "",
                "[telegram]",
                'bot_token = "123:secret-token"',
                "allowed_chat_ids = [123, 456]",
                "allowed_user_ids = [999]",
                "allow_writes = true",
                "allow_adherence_rebuild = false",
                'default_subject = "Child A"',
                'default_location = "left_elbow"',
                'command_mode = "buttons"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_config_path_command(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    exit_code = cli_module.main(["config", "path", "--config", str(config_path)])
    assert exit_code == 0
    assert str(config_path) in capsys.readouterr().out


def test_config_show_masks_secrets(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    exit_code = cli_module.main(["config", "show", "--config", str(config_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "********" in output
    assert "secret-api-key" not in output
    assert "123:secret-token" not in output


def test_config_show_can_reveal_secrets(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    exit_code = cli_module.main(["config", "show", "--show-secrets", "--config", str(config_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "secret-api-key" in output
    assert "123:secret-token" in output


def test_config_validate_and_set_root_keys(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    assert cli_module.main(["config", "validate", "--config", str(config_path)]) == 0
    assert "Config OK" in capsys.readouterr().out

    assert cli_module.main(["config", "set", "timezone", "UTC", "--config", str(config_path)]) == 0
    assert 'timezone = "UTC"' in config_path.read_text(encoding="utf-8")


def test_telegram_env_var_parsing(monkeypatch):
    config = AppConfig(telegram=TelegramConfig(allowed_chat_ids=[1]))
    monkeypatch.setenv("ZEMA_TELEGRAM_ALLOWED_CHAT_IDS", "123,456")
    monkeypatch.setenv("ZEMA_TELEGRAM_ALLOWED_USER_IDS", "999")
    monkeypatch.setenv("ZEMA_TELEGRAM_ALLOW_WRITES", "false")
    monkeypatch.setenv("ZEMA_TELEGRAM_ALLOW_ADHERENCE_REBUILD", "yes")
    monkeypatch.setenv("ZEMA_TELEGRAM_REMINDERS_ENABLED", "false")
    monkeypatch.setenv("ZEMA_TELEGRAM_REMINDER_MORNING_TIME", "06:30")
    monkeypatch.setenv("ZEMA_TELEGRAM_REMINDER_EVENING_TIME", "20:15")
    monkeypatch.setenv("ZEMA_TELEGRAM_REMINDER_SEND_IMAGES", "no")
    monkeypatch.setenv("ZEMA_TELEGRAM_REMINDER_SNOOZE_MINUTES", "45")
    resolved = apply_env_overrides(config)
    assert resolved.telegram.allowed_chat_ids == [123, 456]
    assert resolved.telegram.allowed_user_ids == [999]
    assert resolved.telegram.allow_writes is False
    assert resolved.telegram.allow_adherence_rebuild is True
    assert resolved.telegram.reminders.enabled is False
    assert resolved.telegram.reminders.morning_time == "06:30"
    assert resolved.telegram.reminders.evening_time == "20:15"
    assert resolved.telegram.reminders.send_location_images is False
    assert resolved.telegram.reminders.snooze_minutes == 45


def test_invalid_telegram_env_var(monkeypatch):
    config = AppConfig()
    monkeypatch.setenv("ZEMA_TELEGRAM_ALLOWED_CHAT_IDS", "abc")
    with pytest.raises(Exception) as exc:
        apply_env_overrides(config)
    assert "comma-separated list of integers" in str(exc.value)


def test_telegram_config_show_and_validate(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    assert cli_module.main(["telegram", "config", "show", "--config", str(config_path)]) == 0
    output = capsys.readouterr().out
    assert "********" in output
    assert "123:secret-token" not in output

    assert cli_module.main(["telegram", "config", "validate", "--config", str(config_path)]) == 0
    assert "Telegram config OK" in capsys.readouterr().out


def test_telegram_config_mutators(tmp_path):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    assert cli_module.main(["telegram", "config", "set-token", "new-token", "--config", str(config_path)]) == 0
    assert "new-token" in config_path.read_text(encoding="utf-8")

    assert cli_module.main(["telegram", "config", "add-chat", "777", "--config", str(config_path)]) == 0
    assert "777" in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "remove-chat", "777", "--config", str(config_path)]) == 0
    assert "777" not in config_path.read_text(encoding="utf-8")

    assert cli_module.main(["telegram", "config", "add-user", "888", "--config", str(config_path)]) == 0
    assert "888" in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "remove-user", "888", "--config", str(config_path)]) == 0
    assert "888" not in config_path.read_text(encoding="utf-8")

    assert cli_module.main(["telegram", "config", "allow-writes", "false", "--config", str(config_path)]) == 0
    assert "allow_writes = false" in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "allow-adherence-rebuild", "true", "--config", str(config_path)]) == 0
    assert "allow_adherence_rebuild = true" in config_path.read_text(encoding="utf-8")


def test_telegram_reminder_config_commands(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    assert cli_module.main(["telegram", "config", "reminders", "show", "--config", str(config_path)]) == 0
    assert "morning_time: 07:00" in capsys.readouterr().out

    assert cli_module.main(["telegram", "config", "reminders", "disable", "--config", str(config_path)]) == 0
    assert "enabled = false" in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "reminders", "enable", "--config", str(config_path)]) == 0
    assert "enabled = true" in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "reminders", "set-morning", "06:45", "--config", str(config_path)]) == 0
    assert 'morning_time = "06:45"' in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "reminders", "set-evening", "20:30", "--config", str(config_path)]) == 0
    assert 'evening_time = "20:30"' in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "reminders", "set-snooze", "45", "--config", str(config_path)]) == 0
    assert "snooze_minutes = 45" in config_path.read_text(encoding="utf-8")
    assert cli_module.main(["telegram", "config", "reminders", "images", "false", "--config", str(config_path)]) == 0
    assert "send_location_images = false" in config_path.read_text(encoding="utf-8")


def test_telegram_status_masks_secrets(tmp_path, capsys):
    config_path = tmp_path / "config.toml"
    write_config(config_path)
    assert cli_module.main(["telegram", "status", "--config", str(config_path)]) == 0
    output = capsys.readouterr().out
    assert "backend_url: http://localhost:28173" in output
    assert "api_key: ********" in output
    assert "telegram_bot_token: ********" in output
    assert "secret-api-key" not in output


def test_telegram_test_uses_validation(monkeypatch, tmp_path, capsys):
    from czm_cli.commands import telegram as telegram_commands

    config_path = tmp_path / "config.toml"
    write_config(config_path)
    monkeypatch.setattr(telegram_commands, "validate_backend", lambda base_url: None)
    monkeypatch.setattr(telegram_commands, "validate_bot_token", lambda token: type("Bot", (), {"username": "zema_bot"})())
    assert cli_module.main(["telegram", "test", "--config", str(config_path)]) == 0
    assert "Telegram config OK (@zema_bot)" in capsys.readouterr().out


def test_discover_chats_from_get_updates(monkeypatch):
    from czm_cli.telegram import setup as telegram_setup

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "result": [
                    {
                        "message": {
                            "chat": {"id": 123, "type": "private", "first_name": "Ada"},
                            "from": {"id": 999},
                        }
                    },
                    {
                        "message": {
                            "chat": {"id": -456, "type": "group", "title": "Family"},
                            "from": {"id": 888},
                        }
                    },
                ]
            }

    monkeypatch.setattr(telegram_setup.httpx, "get", lambda *args, **kwargs: FakeResponse())
    chats = telegram_setup.discover_chats("token")
    assert [(chat.id, chat.type, chat.title, chat.user_id) for chat in chats] == [
        (123, "private", "Ada", 999),
        (-456, "group", "Family", 888),
    ]


def test_telegram_run_starts_runtime(monkeypatch, tmp_path):
    from czm_cli.commands import telegram as telegram_commands

    config_path = tmp_path / "config.toml"
    write_config(config_path)
    called = {}
    monkeypatch.setattr(telegram_commands, "validate_backend", lambda base_url: called.setdefault("backend", base_url))
    monkeypatch.setattr(telegram_commands, "run_polling", lambda config: called.setdefault("run", config.telegram.bot_token))
    exit_code = cli_module.main(["telegram", "run", "--config", str(config_path)])
    assert exit_code == 0
    assert called == {"backend": "http://localhost:28173", "run": "123:secret-token"}


def test_setup_telegram_help_registered(capsys):
    with pytest.raises(SystemExit) as exc:
        cli_module.main(["setup", "telegram", "--help"])
    assert exc.value.code == 0
    assert "--bot-token" in capsys.readouterr().out


def test_setup_telegram_noninteractive(monkeypatch, tmp_path, capsys):
    from czm_cli.telegram import setup as telegram_setup

    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(telegram_setup, "validate_backend", lambda base_url: None)
    monkeypatch.setattr(telegram_setup, "validate_bot_token", lambda token: type("Bot", (), {"username": "zema_bot"})())
    exit_code = cli_module.main(
        [
            "setup",
            "telegram",
            "--config",
            str(config_path),
            "--base-url",
            "http://localhost:28173",
            "--api-key",
            "api-secret",
            "--bot-token",
            "bot-secret",
            "--allowed-chat-id",
            "123",
            "--allowed-chat-id",
            "456",
            "--timezone",
            "Europe/Berlin",
            "--yes",
        ]
    )
    assert exit_code == 0
    text = config_path.read_text(encoding="utf-8")
    assert 'api_key = "api-secret"' in text
    assert 'bot_token = "bot-secret"' in text
    assert "allowed_chat_ids = [123, 456]" in text
    assert "allow_writes = true" in text
    assert "Wrote Telegram config" in capsys.readouterr().out


def test_setup_telegram_no_allow_writes(monkeypatch, tmp_path):
    from czm_cli.telegram import setup as telegram_setup

    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(telegram_setup, "validate_backend", lambda base_url: None)
    monkeypatch.setattr(telegram_setup, "validate_bot_token", lambda token: type("Bot", (), {"username": "zema_bot"})())
    exit_code = cli_module.main(
        [
            "setup",
            "telegram",
            "--config",
            str(config_path),
            "--api-key",
            "api-secret",
            "--bot-token",
            "bot-secret",
            "--allowed-chat-id",
            "123",
            "--no-allow-writes",
            "--yes",
        ]
    )
    assert exit_code == 0
    assert "allow_writes = false" in config_path.read_text(encoding="utf-8")


def test_setup_telegram_json_does_not_leak_secrets(monkeypatch, tmp_path, capsys):
    from czm_cli.telegram import setup as telegram_setup

    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(telegram_setup, "validate_backend", lambda base_url: None)
    monkeypatch.setattr(telegram_setup, "validate_bot_token", lambda token: type("Bot", (), {"username": "zema_bot"})())
    exit_code = cli_module.main(
        [
            "setup",
            "telegram",
            "--json",
            "--config",
            str(config_path),
            "--api-key",
            "api-secret",
            "--bot-token",
            "bot-secret",
            "--allowed-chat-id",
            "123",
            "--yes",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert "api-secret" not in json.dumps(payload)
    assert "bot-secret" not in json.dumps(payload)
