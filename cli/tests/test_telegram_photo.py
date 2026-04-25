from __future__ import annotations

import asyncio

from czm_cli.config import AppConfig, TelegramConfig
from czm_cli.telegram.commands import TelegramCommandContext
from czm_cli.telegram.handlers import TelegramHandlerContext, handle_callback, handle_photo
from czm_cli.telegram.state import ConversationStore, EXPIRED_STATE_MESSAGE


class FakeClient:
    def __init__(self):
        self.uploads = []

    def upload_bytes(self, path, *, field_name, filename, content, content_type=None):
        self.uploads.append((path, field_name, filename, content, content_type))
        return {"location": {"id": 2}}


class FakeFile:
    async def download_as_bytearray(self):
        return bytearray(b"\xff\xd8\xffimage")


class FakePhoto:
    file_size = 10

    async def get_file(self):
        return FakeFile()


class FakeMessage:
    def __init__(self, photo=None):
        self.photo = photo or []
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.edits = []
        self.message = FakeMessage()

    async def answer(self):
        return None

    async def edit_message_text(self, text, **kwargs):
        self.edits.append(text)


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run(coro):
    return asyncio.run(coro)


def make_ctx(*, chat_id=123, allow_writes=True):
    config = AppConfig(telegram=TelegramConfig(bot_token="t", allowed_chat_ids=[123], allow_writes=allow_writes))
    client = FakeClient()
    ctx = TelegramHandlerContext(TelegramCommandContext(config, client), ConversationStore())
    update = Obj(effective_chat=Obj(id=chat_id), effective_user=Obj(id=1))
    return ctx, client, update


def test_set_image_callback_stores_waiting_photo_state():
    ctx, client, update = make_ctx()
    query = FakeQuery("loc:image:2")
    update.callback_query = query
    run(handle_callback(update, None, ctx))
    assert ctx.state.get(123, 1).name == "waiting_location_photo"


def test_authorized_photo_uploads_to_backend():
    ctx, client, update = make_ctx()
    ctx.state.set(123, 1, "waiting_location_photo", {"location_id": 2})
    message = FakeMessage(photo=[FakePhoto()])
    update.effective_message = message
    run(handle_photo(update, None, ctx))
    assert client.uploads[0][0] == "/locations/2/image"
    assert client.uploads[0][3].startswith(b"\xff\xd8\xff")
    assert "updated" in message.replies[0]


def test_unauthorized_photo_rejected_before_download():
    ctx, client, update = make_ctx(chat_id=999)
    message = FakeMessage(photo=[FakePhoto()])
    update.effective_message = message
    run(handle_photo(update, None, ctx))
    assert client.uploads == []
    assert "not allowed" in message.replies[0]


def test_photo_without_state_gets_expired_message():
    ctx, client, update = make_ctx()
    message = FakeMessage(photo=[FakePhoto()])
    update.effective_message = message
    run(handle_photo(update, None, ctx))
    assert message.replies == [EXPIRED_STATE_MESSAGE]
