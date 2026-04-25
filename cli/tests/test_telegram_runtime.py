from __future__ import annotations

import asyncio

import pytest

from czm_cli.config import AppConfig, TelegramConfig
from czm_cli.errors import EXIT_AUTH
from czm_cli.telegram.runtime import TelegramRuntime, build_application, register_command_menu
from czm_cli.telegram.security import TelegramIdentity, ensure_allowed


class FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeBot:
    def __init__(self):
        self.commands = None

    async def set_my_commands(self, commands):
        self.commands = commands


class FakeObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeClient:
    def __init__(self):
        self.closed = False

    def get(self, path, params=None):
        if path == "/health":
            return {"status": "ok"}
        if path == "/subjects":
            return {"subjects": []}
        raise AssertionError(path)

    def close(self):
        self.closed = True


def run(coro):
    return asyncio.run(coro)


def config(*, chats=None, users=None, allow_writes=True, allow_rebuild=False):
    return AppConfig(
        base_url="http://example",
        api_key="api-secret",
        telegram=TelegramConfig(
            bot_token="bot-secret",
            allowed_chat_ids=chats or [123],
            allowed_user_ids=users or [],
            allow_writes=allow_writes,
            allow_adherence_rebuild=allow_rebuild,
        ),
    )


def test_build_application_registers_handlers():
    app = build_application(TelegramRuntime(config=config(), client=FakeClient()))
    assert app.handlers


def test_register_command_menu_sets_telegram_commands():
    bot = FakeBot()
    run(register_command_menu(FakeObj(bot=bot)))
    names = [command.command for command in bot.commands]
    assert names[:4] == ["start", "menu", "help", "status"]
    assert "due" in names
    assert "adherence" in names


def test_unknown_chat_rejected():
    with pytest.raises(Exception) as exc:
        ensure_allowed(config().telegram, TelegramIdentity(chat_id=999, user_id=1))
    assert getattr(exc.value, "exit_code") == EXIT_AUTH


def test_unknown_user_rejected_when_user_allowlist_configured():
    with pytest.raises(Exception) as exc:
        ensure_allowed(config(users=[42]).telegram, TelegramIdentity(chat_id=123, user_id=7))
    assert getattr(exc.value, "exit_code") == EXIT_AUTH


def test_allowed_chat_and_user_accepted():
    ensure_allowed(config(users=[42]).telegram, TelegramIdentity(chat_id=123, user_id=42))


def test_runtime_handler_rejects_unknown_chat():
    app = build_application(TelegramRuntime(config=config(chats=[123]), client=FakeClient()))
    handler = app.handlers[0][0].callback
    message = FakeMessage("/subjects")
    update = FakeObj(effective_chat=FakeObj(id=999), effective_user=FakeObj(id=1), effective_message=message)
    run(handler(update, None))
    assert message.replies == ["This Telegram chat is not allowed to use Zema."]


def test_runtime_handler_allows_read_command():
    app = build_application(TelegramRuntime(config=config(chats=[123]), client=FakeClient()))
    handler = app.handlers[0][0].callback
    message = FakeMessage("/subjects")
    update = FakeObj(effective_chat=FakeObj(id=123), effective_user=FakeObj(id=1), effective_message=message)
    run(handler(update, None))
    assert message.replies == ["No subjects."]


def test_runtime_handler_sanitizes_backend_errors():
    class FailingClient(FakeClient):
        def get(self, path, params=None):
            raise RuntimeError("api-secret bot-secret boom")

    app = build_application(TelegramRuntime(config=config(chats=[123]), client=FailingClient()))
    handler = app.handlers[0][0].callback
    message = FakeMessage("/subjects")
    update = FakeObj(effective_chat=FakeObj(id=123), effective_user=FakeObj(id=1), effective_message=message)
    run(handler(update, None))
    assert message.replies == ["Zema request failed."]
