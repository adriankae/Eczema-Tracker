from __future__ import annotations

import asyncio

from czm_cli.config import AppConfig, TelegramConfig
from czm_cli.telegram.commands import TelegramCommandContext
from czm_cli.telegram.handlers import TelegramHandlerContext, handle_callback, handle_guided_text, handle_photo
from czm_cli.telegram.state import ConversationStore


class FakeClient:
    def __init__(self):
        self.requests = []
        self.uploads = []

    def get(self, path, params=None):
        self.requests.append(("GET", path, params))
        if path == "/subjects":
            return {"subjects": [{"id": 1, "display_name": "Child A"}]}
        if path == "/locations":
            return {"locations": [{"id": 2, "code": "left_elbow", "display_name": "Left elbow", "image": None}]}
        if path == "/episodes":
            return {
                "episodes": [
                    {"id": 10, "subject_id": 1, "location_id": 2, "status": "active_flare", "current_phase_number": 1, "healed_at": None, "obsolete_at": None},
                    {"id": 11, "subject_id": 1, "location_id": 2, "status": "in_taper", "current_phase_number": 2, "healed_at": "2026-04-01T00:00:00Z", "obsolete_at": None},
                    {"id": 12, "subject_id": 1, "location_id": 2, "status": "obsolete", "current_phase_number": 2, "healed_at": None, "obsolete_at": "2026-04-01T00:00:00Z"},
                ]
            }
        raise AssertionError(path)

    def post(self, path, json=None, params=None):
        self.requests.append(("POST", path, json))
        if path == "/subjects":
            return {"id": 3, "display_name": json["display_name"]}
        if path == "/locations":
            return {"location": {"id": 4, "code": json["code"], "display_name": json["display_name"], "image": None}}
        if path == "/episodes":
            return {"episode": {"id": 20, "subject_id": json["subject_id"], "location_id": json["location_id"], "status": "active_flare"}}
        if path == "/episodes/10/heal":
            return {"episode": {"id": 10, "status": "in_taper"}}
        if path == "/episodes/11/relapse":
            return {"episode": {"id": 11, "status": "active_flare"}}
        if path == "/adherence/rebuild":
            return {"episodes_processed": 2, "rows_persisted": 14}
        raise AssertionError(path)

    def upload_bytes(self, path, *, field_name, filename, content, content_type=None):
        self.uploads.append((path, field_name, filename, content, content_type))
        return {"location": {"id": 2, "image": {"mime_type": "image/jpeg"}}}

    def download_file(self, path):
        self.requests.append(("DOWNLOAD", path, None))
        if path == "/locations/2/image":
            return b"image-bytes", "image/jpeg"
        raise AssertionError(path)


class FakeFile:
    async def download_as_bytearray(self):
        return bytearray(b"\xff\xd8\xffimage")


class FakePhoto:
    file_size = 10

    async def get_file(self):
        return FakeFile()


class FakeMessage:
    def __init__(self, text="", photo=None):
        self.text = text
        self.photo = photo or []
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs.get("reply_markup")))

    async def reply_photo(self, **kwargs):
        self.replies.append((kwargs.get("caption"), kwargs.get("reply_markup"), kwargs.get("photo")))


class FakeQuery:
    def __init__(self, data):
        self.data = data
        self.edits = []
        self.message = FakeMessage()

    async def answer(self):
        return None

    async def edit_message_text(self, text, **kwargs):
        self.edits.append((text, kwargs.get("reply_markup")))


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run(coro):
    return asyncio.run(coro)


def make_ctx(*, allow_writes=True, allow_rebuild=False, chat_id=123, user_id=1):
    config = AppConfig(
        timezone="UTC",
        telegram=TelegramConfig(
            bot_token="t",
            allowed_chat_ids=[123],
            allow_writes=allow_writes,
            allow_adherence_rebuild=allow_rebuild,
        ),
    )
    client = FakeClient()
    ctx = TelegramHandlerContext(TelegramCommandContext(config, client), ConversationStore())
    update = Obj(effective_chat=Obj(id=chat_id), effective_user=Obj(id=user_id))
    return ctx, client, update


def callback(ctx, update, data):
    query = FakeQuery(data)
    update.callback_query = query
    run(handle_callback(update, None, ctx))
    return query


def text(ctx, body):
    message = FakeMessage(body)
    update = Obj(effective_chat=Obj(id=123), effective_user=Obj(id=1), effective_message=message)
    run(handle_guided_text(update, None, ctx))
    return message


def test_start_episode_existing_subject_location_skip_image_creates_episode():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "menu:start_episode")
    assert "choose a subject" in query.edits[0][0]
    query = callback(ctx, update, "epstart:subject:1")
    assert "Choose a location" in query.edits[0][0]
    query = callback(ctx, update, "epstart:loc:2")
    assert "Add or replace" in query.edits[0][0]
    query = callback(ctx, update, "epstart:skip_image")
    assert "Create episode" in query.edits[0][0]
    query = callback(ctx, update, "epstart:confirm")
    assert "Created episode 20" in query.edits[0][0]
    assert ("POST", "/episodes", {"subject_id": 1, "location_id": 2, "protocol_version": "v1"}) in client.requests


def test_start_episode_create_subject_and_location_flow():
    ctx, client, update = make_ctx()
    callback(ctx, update, "menu:start_episode")
    callback(ctx, update, "epstart:subject_new")
    text(ctx, "Child B")
    callback(ctx, update, "epstart:loc_new")
    text(ctx, "right_knee")
    message = text(ctx, "Right knee")
    assert "Add or replace" in message.replies[0][0]
    assert ("POST", "/subjects", {"display_name": "Child B"}) in client.requests
    assert ("POST", "/locations", {"code": "right_knee", "display_name": "Right knee"}) in client.requests


def test_start_episode_photo_upload_continues_to_confirmation():
    ctx, client, update = make_ctx()
    callback(ctx, update, "menu:start_episode")
    callback(ctx, update, "epstart:subject:1")
    callback(ctx, update, "epstart:loc:2")
    callback(ctx, update, "epstart:image")
    message = FakeMessage(photo=[FakePhoto()])
    photo_update = Obj(effective_chat=Obj(id=123), effective_user=Obj(id=1), effective_message=message)
    run(handle_photo(photo_update, None, ctx))
    assert client.uploads[0][0] == "/locations/2/image"
    assert "Create episode" in message.replies[0][0]


def test_heal_flow_lists_selects_and_confirms():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "menu:heal")
    assert "heal" in query.edits[0][0]
    assert query.edits[0][1].inline_keyboard[0][0].text == "Left elbow"
    query = callback(ctx, update, "heal:select:10")
    assert query.edits == []
    assert "Mark Left elbow as healed" in query.message.replies[0][0]
    assert query.message.replies[0][2] == b"image-bytes"
    query = callback(ctx, update, "heal:confirm:10")
    assert "Healed episode 10" in query.edits[0][0]
    assert ("POST", "/episodes/10/heal", None) in client.requests


def test_relapse_flow_lists_healed_episode_and_confirms():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "menu:relapse")
    assert "relapse" in query.edits[0][0]
    assert query.edits[0][1].inline_keyboard[0][0].text == "Left elbow"
    query = callback(ctx, update, "relapse:select:11")
    assert query.edits == []
    assert "Mark Left elbow as relapsed" in query.message.replies[0][0]
    assert query.message.replies[0][2] == b"image-bytes"
    query = callback(ctx, update, "relapse:confirm:11")
    assert "Relapsed episode 11" in query.edits[0][0]
    assert ("POST", "/episodes/11/relapse", {"reason": "relapse"}) in client.requests


def test_adherence_rebuild_button_hidden_when_disabled_and_confirmed_when_enabled():
    ctx, _client, update = make_ctx(allow_rebuild=False)
    query = callback(ctx, update, "menu:adherence")
    labels = [button.text for row in query.edits[0][1].inline_keyboard for button in row]
    assert "Rebuild snapshots" not in labels

    ctx, client, update = make_ctx(allow_rebuild=True)
    query = callback(ctx, update, "menu:adherence")
    labels = [button.text for row in query.edits[0][1].inline_keyboard for button in row]
    assert "Rebuild snapshots" in labels
    query = callback(ctx, update, "adh:rebuild")
    assert "Choose rebuild range" in query.edits[0][0]
    query = callback(ctx, update, "adh:rebuild:range:7")
    assert "Rebuild adherence snapshots" in query.edits[0][0]
    query = callback(ctx, update, "adh:rebuild:confirm:7")
    assert "Adherence rebuild complete" in query.edits[0][0]
    assert client.requests[-1][0:2] == ("POST", "/adherence/rebuild")
    assert client.requests[-1][2]["active_only"] is True


def test_write_permission_required_for_guided_workflows():
    ctx, _client, update = make_ctx(allow_writes=False)
    query = callback(ctx, update, "menu:start_episode")
    assert "disabled" in query.edits[0][0]


def test_rebuild_permission_required_for_callback():
    ctx, _client, update = make_ctx(allow_rebuild=False)
    query = callback(ctx, update, "adh:rebuild")
    assert "rebuild is disabled" in query.edits[0][0]
