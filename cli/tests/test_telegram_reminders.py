from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from czm_cli.config import AppConfig, TelegramConfig, TelegramReminderConfig
from czm_cli.telegram.commands import TelegramCommandContext
from czm_cli.telegram.handlers import TelegramHandlerContext, handle_callback
from czm_cli.telegram.reminders import SnoozeStore, schedule_reminders, send_due_reminders
from czm_cli.telegram.state import ConversationStore


class FakeClient:
    def __init__(self, *, image: bytes | None = None):
        self.image = image
        self.requests = []

    def get(self, path, params=None):
        self.requests.append(("GET", path, params))
        if path == "/episodes/due":
            return {
                "due": [
                    {
                        "episode_id": 12,
                        "subject_id": 1,
                        "location_id": 2,
                        "current_phase_number": 1,
                        "treatment_due_today": True,
                    },
                    {
                        "episode_id": 13,
                        "subject_id": 1,
                        "location_id": 3,
                        "current_phase_number": 2,
                        "treatment_due_today": True,
                    },
                ]
            }
        if path == "/subjects":
            return {"subjects": [{"id": 1, "display_name": "Child A"}]}
        if path == "/locations":
            return {
                "locations": [
                    {"id": 2, "code": "left_elbow", "display_name": "Left elbow"},
                    {"id": 3, "code": "right_knee", "display_name": "Right knee"},
                ]
            }
        raise AssertionError(path)

    def download_file(self, path):
        self.requests.append(("DOWNLOAD", path, None))
        if self.image is None:
            raise RuntimeError("not found")
        return self.image, "image/jpeg"


class FakeBot:
    def __init__(self):
        self.messages = []
        self.photos = []
        self.commands = None

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)

    async def send_photo(self, **kwargs):
        self.photos.append(kwargs)

    async def set_my_commands(self, commands):
        self.commands = commands


class FakeJobQueue:
    def __init__(self):
        self.jobs = []

    def run_daily(self, callback, *, time, name, data):
        self.jobs.append((callback, time, name, data))


class FakeApplication:
    def __init__(self):
        self.job_queue = FakeJobQueue()


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.edits = []
        self.message = FakeMessage()

    async def answer(self):
        return None

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs.get("reply_markup")))


class FakeMessage:
    async def reply_text(self, text, **kwargs):
        return None


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run(coro):
    return asyncio.run(coro)


def make_ctx(*, allow_writes=True, image=None, reminders=None):
    config = AppConfig(
        timezone="Europe/Berlin",
        telegram=TelegramConfig(
            bot_token="t",
            allowed_chat_ids=[123],
            allow_writes=allow_writes,
            reminders=reminders or TelegramReminderConfig(timezone="Europe/Berlin"),
        ),
    )
    client = FakeClient(image=image)
    ctx = TelegramHandlerContext(TelegramCommandContext(config, client), ConversationStore(), SnoozeStore(30))
    return ctx, client


def test_scheduler_registers_morning_and_evening_jobs():
    ctx, _client = make_ctx()
    application = FakeApplication()
    schedule_reminders(application, ctx)
    assert [job[2] for job in application.job_queue.jobs] == ["zema-morning-reminder", "zema-evening-reminder"]
    assert application.job_queue.jobs[0][1].hour == 7
    assert application.job_queue.jobs[1][1].hour == 19
    assert str(application.job_queue.jobs[0][1].tzinfo) == "Europe/Berlin"


def test_disabled_reminders_register_no_jobs():
    ctx, _client = make_ctx(reminders=TelegramReminderConfig(enabled=False))
    application = FakeApplication()
    schedule_reminders(application, ctx)
    assert application.job_queue.jobs == []


def test_morning_reminder_sends_location_image_and_log_button():
    ctx, client = make_ctx(image=b"jpeg-bytes")
    bot = FakeBot()
    run(send_due_reminders(bot, ctx, reminder_kind="morning"))
    assert len(bot.photos) == 2
    assert bot.photos[0]["chat_id"] == 123
    assert bot.photos[0]["photo"] == b"jpeg-bytes"
    assert "Left elbow" in bot.photos[0]["caption"]
    labels = [button.text for row in bot.photos[0]["reply_markup"].inline_keyboard for button in row]
    assert "Log application" in labels
    assert "Snooze" in labels
    assert ("GET", "/episodes/due", None) in client.requests


def test_reminder_falls_back_to_text_when_image_missing():
    ctx, _client = make_ctx(image=None)
    bot = FakeBot()
    run(send_due_reminders(bot, ctx, reminder_kind="morning"))
    assert bot.photos == []
    assert len(bot.messages) == 2
    assert "Left elbow" in bot.messages[0]["text"]


def test_evening_reminder_uses_due_source_and_filters_to_phase_one():
    ctx, _client = make_ctx(image=None)
    bot = FakeBot()
    run(send_due_reminders(bot, ctx, reminder_kind="evening"))
    assert len(bot.messages) == 1
    assert "Left elbow" in bot.messages[0]["text"]
    assert "Right knee" not in bot.messages[0]["text"]


def test_log_button_hidden_when_writes_disabled():
    ctx, _client = make_ctx(allow_writes=False, image=None)
    bot = FakeBot()
    run(send_due_reminders(bot, ctx, reminder_kind="morning"))
    labels = [button.text for row in bot.messages[0]["reply_markup"].inline_keyboard for button in row]
    assert "Log application" not in labels
    assert "Snooze" in labels


def test_snooze_suppresses_until_expiry():
    now = datetime(2026, 4, 25, 7, 0, tzinfo=timezone.utc)
    store = SnoozeStore(30, clock=lambda: now)
    store.snooze(123, 12)
    assert store.is_snoozed(123, 12) is True
    store.clock = lambda: datetime(2026, 4, 25, 7, 31, tzinfo=timezone.utc)
    assert store.is_snoozed(123, 12) is False


def test_snooze_callback_records_episode():
    ctx, _client = make_ctx()
    query = FakeQuery("rem:snooze:12")
    update = Obj(effective_chat=Obj(id=123), effective_user=Obj(id=1), callback_query=query)
    run(handle_callback(update, None, ctx))
    assert "Snoozed episode 12" in query.edits[0][0]
    assert ctx.snoozes is not None
    assert ctx.snoozes.is_snoozed(123, 12) is True
