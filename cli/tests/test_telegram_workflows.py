from __future__ import annotations

import asyncio

import pytest
from telegram.error import BadRequest

from czm_cli.config import AppConfig, TelegramConfig
from czm_cli.telegram.commands import TelegramCommandContext
from czm_cli.telegram.handlers import (
    TelegramHandlerContext,
    _location_code_from_display_name,
    handle_callback,
    handle_guided_text,
    handle_photo,
    safe_edit_callback_message,
)
from czm_cli.telegram.state import ConversationStore


class FakeClient:
    def __init__(self, *, subjects=None, locations=None):
        self.requests = []
        self.uploads = []
        self.subjects = subjects if subjects is not None else [{"id": 1, "display_name": "Child A"}]
        self.locations = locations if locations is not None else [
            {"id": 2, "code": "left_elbow", "display_name": "Left elbow", "image": None},
            {"id": 5, "code": "right_cheekbone", "display_name": "Right cheekbone", "image": None},
            {"id": 6, "code": "right_knee", "display_name": "Right knee", "image": None},
        ]

    def get(self, path, params=None):
        self.requests.append(("GET", path, params))
        if path == "/subjects":
            return {"subjects": self.subjects}
        if path == "/locations":
            return {"locations": self.locations}
        if path == "/episodes":
            return {
                "episodes": [
                    {"id": 10, "subject_id": 1, "location_id": 2, "status": "active_flare", "current_phase_number": 1, "healed_at": None, "obsolete_at": None},
                    {"id": 11, "subject_id": 1, "location_id": 2, "status": "in_taper", "current_phase_number": 2, "healed_at": "2026-04-01T00:00:00Z", "obsolete_at": None},
                    {"id": 12, "subject_id": 1, "location_id": 2, "status": "obsolete", "current_phase_number": 2, "healed_at": None, "obsolete_at": "2026-04-01T00:00:00Z"},
                    {"id": 13, "subject_id": 1, "location_id": 5, "status": "active_flare", "current_phase_number": 1, "healed_at": None, "obsolete_at": None},
                    {"id": 14, "subject_id": 1, "location_id": 6, "status": "healed", "current_phase_number": 2, "healed_at": "2026-04-02T00:00:00Z", "obsolete_at": None},
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
        if path == "/episodes/13/heal":
            return {"episode": {"id": 13, "status": "in_taper"}}
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
        if path == "/locations/5/image":
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
    def __init__(self, text="", photo=None, caption=None):
        self.text = text
        self.photo = photo or []
        self.caption = caption
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs.get("reply_markup")))

    async def reply_photo(self, **kwargs):
        self.replies.append((kwargs.get("caption"), kwargs.get("reply_markup"), kwargs.get("photo")))


class FakeQuery:
    def __init__(self, data, *, message=None, text_error=None, caption_error=None):
        self.data = data
        self.edits = []
        self.caption_edits = []
        self.message = message or FakeMessage()
        self.text_error = text_error
        self.caption_error = caption_error

    async def answer(self):
        return None

    async def edit_message_text(self, text, **kwargs):
        if self.text_error is not None:
            raise BadRequest(self.text_error)
        self.edits.append((text, kwargs.get("reply_markup")))

    async def edit_message_caption(self, caption, **kwargs):
        if self.caption_error is not None:
            raise BadRequest(self.caption_error)
        self.caption_edits.append((caption, kwargs.get("reply_markup")))


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run(coro):
    return asyncio.run(coro)


def make_ctx(*, allow_writes=True, allow_rebuild=False, chat_id=123, user_id=1, subjects=None, locations=None):
    config = AppConfig(
        timezone="UTC",
        telegram=TelegramConfig(
            bot_token="t",
            allowed_chat_ids=[123],
            allow_writes=allow_writes,
            allow_adherence_rebuild=allow_rebuild,
        ),
    )
    client = FakeClient(subjects=subjects, locations=locations)
    ctx = TelegramHandlerContext(TelegramCommandContext(config, client), ConversationStore())
    update = Obj(effective_chat=Obj(id=chat_id), effective_user=Obj(id=user_id))
    return ctx, client, update


def callback(ctx, update, data, *, query=None):
    query = query or FakeQuery(data)
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
    assert "Using subject: Child A" in query.edits[0][0]
    assert "Choose a location" in query.edits[0][0]
    labels = [button.text for row in query.edits[0][1].inline_keyboard for button in row]
    assert "Left elbow" in labels
    assert "Right knee" in labels
    assert "Create new location" in labels
    assert not any("Episode" in label or "#10" in label or "#14" in label for label in labels)
    query = callback(ctx, update, "epstart:loc:6")
    assert "Add or replace" in query.edits[0][0]
    query = callback(ctx, update, "epstart:skip_image")
    assert "Create episode" in query.edits[0][0]
    query = callback(ctx, update, "epstart:confirm")
    assert "Created episode 20" in query.edits[0][0]
    assert ("POST", "/episodes", {"subject_id": 1, "location_id": 6, "protocol_version": "v1"}) in client.requests


def test_start_episode_multiple_subjects_still_shows_subject_buttons():
    ctx, _client, update = make_ctx(subjects=[{"id": 1, "display_name": "Child A"}, {"id": 2, "display_name": "Child B"}])
    query = callback(ctx, update, "menu:start_episode")
    assert "choose a subject" in query.edits[0][0]
    labels = [button.text for row in query.edits[0][1].inline_keyboard for button in row]
    assert "Child A" in labels
    assert "Child B" in labels


def test_start_episode_zero_subjects_prompts_create_subject():
    ctx, _client, update = make_ctx(subjects=[])
    query = callback(ctx, update, "menu:start_episode")
    assert "create a subject first" in query.edits[0][0]
    labels = [button.text for row in query.edits[0][1].inline_keyboard for button in row]
    assert labels == ["Create new subject"]


def test_start_episode_no_locations_goes_directly_to_create_location():
    ctx, _client, update = make_ctx(locations=[])
    query = callback(ctx, update, "menu:start_episode")
    assert query.edits[0][0] == "Using subject: Child A.\nNo locations exist yet. Send the new location display name."
    message = text(ctx, "New ankle")
    assert "Add or replace" in message.replies[0][0]


def test_start_episode_create_subject_and_location_flow():
    ctx, client, update = make_ctx()
    callback(ctx, update, "menu:start_episode")
    callback(ctx, update, "epstart:loc_new")
    message = text(ctx, "Left ankle")
    assert "Add or replace" in message.replies[0][0]
    assert ("POST", "/locations", {"code": "left_ankle", "display_name": "Left ankle"}) in client.requests


def test_start_episode_create_subject_then_location_flow():
    ctx, client, update = make_ctx(subjects=[])
    callback(ctx, update, "menu:start_episode")
    callback(ctx, update, "epstart:subject_new")
    message = text(ctx, "Child B")
    assert "Choose a location" in message.replies[0][0]
    callback(ctx, update, "epstart:loc_new")
    message = text(ctx, "Rechter Wangenknochen")
    assert "Add or replace" in message.replies[0][0]
    assert ("POST", "/subjects", {"display_name": "Child B"}) in client.requests
    assert ("POST", "/locations", {"code": "rechter_wangenknochen", "display_name": "Rechter Wangenknochen"}) in client.requests


def test_start_episode_duplicate_created_location_can_use_existing_location():
    ctx, client, update = make_ctx()
    callback(ctx, update, "menu:start_episode")
    callback(ctx, update, "epstart:loc_new")
    message = text(ctx, "Left elbow")
    assert "already exists" in message.replies[0][0]
    labels = [button.text for row in message.replies[0][1].inline_keyboard for button in row]
    assert "Use existing location" in labels
    assert not any(request == ("POST", "/locations", {"code": "left_elbow", "display_name": "Left elbow"}) for request in client.requests)

    query = callback(ctx, update, "epstart:loc:2")
    assert "already an active episode" in query.edits[0][0]


def test_start_episode_blocks_active_location_without_showing_episode_choices():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "menu:start_episode")
    assert "Episode 10" not in query.edits[0][0]
    query = callback(ctx, update, "epstart:loc:2")
    assert "There is already an active episode for Left elbow." in query.edits[0][0]
    assert "Use Due now, Heal, or Relapse" in query.edits[0][0]
    labels = [button.text for row in query.edits[0][1].inline_keyboard for button in row]
    assert labels == ["Choose another location", "Create new location", "Open menu"]
    assert not any(request[0] == "POST" and request[1] == "/episodes" for request in client.requests)


def test_start_episode_duplicate_check_uses_status_before_stale_healed_at():
    ctx, _client, update = make_ctx()
    callback(ctx, update, "menu:start_episode")
    query = callback(ctx, update, "epstart:loc:2")
    assert "already an active episode" in query.edits[0][0]


def test_start_episode_duplicate_check_allows_healed_and_obsolete_statuses():
    ctx, client, update = make_ctx(
        locations=[
            {"id": 7, "code": "old_elbow", "display_name": "Old elbow", "image": None},
            {"id": 8, "code": "old_knee", "display_name": "Old knee", "image": None},
        ]
    )
    client.get = lambda path, params=None: {
        "/subjects": {"subjects": [{"id": 1, "display_name": "Child A"}]},
        "/locations": {
            "locations": [
                {"id": 7, "code": "old_elbow", "display_name": "Old elbow", "image": None},
                {"id": 8, "code": "old_knee", "display_name": "Old knee", "image": None},
            ]
        },
        "/episodes": {
            "episodes": [
                {"id": 21, "subject_id": 1, "location_id": 7, "status": "healed", "healed_at": None, "obsolete_at": None},
                {"id": 22, "subject_id": 1, "location_id": 8, "status": "obsolete", "healed_at": None, "obsolete_at": "2026-04-01T00:00:00Z"},
            ]
        },
    }[path]
    callback(ctx, update, "menu:start_episode")
    assert "Add or replace" in callback(ctx, update, "epstart:loc:7").edits[0][0]
    callback(ctx, update, "epstart:locations")
    assert "Add or replace" in callback(ctx, update, "epstart:loc:8").edits[0][0]


def test_start_episode_missing_status_blocks_unless_clearly_ended():
    ctx, client, update = make_ctx(
        locations=[
            {"id": 7, "code": "unknown_elbow", "display_name": "Unknown elbow", "image": None},
            {"id": 8, "code": "healed_knee", "display_name": "Healed knee", "image": None},
            {"id": 9, "code": "obsolete_ankle", "display_name": "Obsolete ankle", "image": None},
        ]
    )
    client.get = lambda path, params=None: {
        "/subjects": {"subjects": [{"id": 1, "display_name": "Child A"}]},
        "/locations": {
            "locations": [
                {"id": 7, "code": "unknown_elbow", "display_name": "Unknown elbow", "image": None},
                {"id": 8, "code": "healed_knee", "display_name": "Healed knee", "image": None},
                {"id": 9, "code": "obsolete_ankle", "display_name": "Obsolete ankle", "image": None},
            ]
        },
        "/episodes": {
            "episodes": [
                {"id": 31, "subject_id": 1, "location_id": 7},
                {"id": 32, "subject_id": 1, "location_id": 8, "healed_at": "2026-04-01T00:00:00Z"},
                {"id": 33, "subject_id": 1, "location_id": 9, "obsolete_at": "2026-04-01T00:00:00Z"},
            ]
        },
    }[path]
    callback(ctx, update, "menu:start_episode")
    assert "already an active episode" in callback(ctx, update, "epstart:loc:7").edits[0][0]
    callback(ctx, update, "epstart:locations")
    assert "Add or replace" in callback(ctx, update, "epstart:loc:8").edits[0][0]
    callback(ctx, update, "epstart:locations")
    assert "Add or replace" in callback(ctx, update, "epstart:loc:9").edits[0][0]


def test_location_code_from_display_name_rules():
    assert _location_code_from_display_name("Rechter Wangenknochen") == "rechter_wangenknochen"
    assert _location_code_from_display_name("Hüfte groß") == "huefte_gross"
    assert _location_code_from_display_name("Right cheekbone / jaw") == "right_cheekbone_jaw"
    assert _location_code_from_display_name("   ") is None


def test_start_episode_photo_upload_continues_to_confirmation():
    ctx, client, update = make_ctx()
    callback(ctx, update, "menu:start_episode")
    callback(ctx, update, "epstart:loc:6")
    callback(ctx, update, "epstart:image")
    message = FakeMessage(photo=[FakePhoto()])
    photo_update = Obj(effective_chat=Obj(id=123), effective_user=Obj(id=1), effective_message=message)
    run(handle_photo(photo_update, None, ctx))
    assert client.uploads[0][0] == "/locations/6/image"
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
    query = callback(ctx, update, "heal:confirm:10", query=FakeQuery("heal:confirm:10", message=FakeMessage(photo=[object()], caption="Mark Left elbow as healed?")))
    assert "Healed episode 10" in query.caption_edits[0][0]
    assert ("POST", "/episodes/10/heal", None) in client.requests


def test_relapsed_active_flare_episode_appears_in_heal_flow():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "menu:heal")
    callbacks = [button.callback_data for row in query.edits[0][1].inline_keyboard for button in row]
    assert "heal:select:13" in callbacks

    query = callback(ctx, update, "heal:select:13")
    assert "Mark Right cheekbone as healed" in query.message.replies[0][0]
    query = callback(ctx, update, "heal:confirm:13", query=FakeQuery("heal:confirm:13", message=FakeMessage(text="Mark Right cheekbone as healed?")))
    assert "Healed episode 13" in query.edits[0][0]
    assert ("POST", "/episodes/13/heal", None) in client.requests


def test_relapse_flow_lists_healed_episode_and_confirms():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "menu:relapse")
    assert "relapse" in query.edits[0][0]
    assert query.edits[0][1].inline_keyboard[0][0].text == "Left elbow"
    query = callback(ctx, update, "relapse:select:11")
    assert query.edits == []
    assert "Mark Left elbow as relapsed" in query.message.replies[0][0]
    assert query.message.replies[0][2] == b"image-bytes"
    query = callback(ctx, update, "relapse:confirm:11", query=FakeQuery("relapse:confirm:11", message=FakeMessage(photo=[object()], caption="Mark Left elbow as relapsed?")))
    assert "Relapsed episode 11" in query.caption_edits[0][0]
    assert ("POST", "/episodes/11/relapse", {"reason": "relapse"}) in client.requests


def test_photo_confirmation_cancel_edits_caption_for_heal_and_relapse():
    ctx, _client, update = make_ctx()
    heal_query = callback(ctx, update, "heal:cancel", query=FakeQuery("heal:cancel", message=FakeMessage(photo=[object()], caption="Mark Left elbow as healed?")))
    assert "Heal cancelled" in heal_query.caption_edits[0][0]

    relapse_query = callback(ctx, update, "relapse:cancel", query=FakeQuery("relapse:cancel", message=FakeMessage(photo=[object()], caption="Mark Left elbow as relapsed?")))
    assert "Relapse cancelled" in relapse_query.caption_edits[0][0]


def test_text_only_confirmation_still_edits_text():
    ctx, client, update = make_ctx()
    query = callback(ctx, update, "heal:confirm:10", query=FakeQuery("heal:confirm:10", message=FakeMessage(text="Heal episode 10?")))
    assert "Healed episode 10" in query.edits[0][0]
    assert query.caption_edits == []
    assert ("POST", "/episodes/10/heal", None) in client.requests


def test_photo_confirmation_falls_back_to_reply_when_text_edit_rejected():
    query = FakeQuery(
        "heal:confirm:10",
        message=FakeMessage(photo=[object()]),
        caption_error="There is no caption in the message to edit",
        text_error="There is no text in the message to edit",
    )
    run(safe_edit_callback_message(query, "Healed episode 10."))
    assert query.message.replies[0][0] == "Healed episode 10."


def test_unrelated_bad_request_is_not_swallowed():
    query = FakeQuery("heal:confirm:10", message=FakeMessage(text="Heal episode 10?"), text_error="message is not modified")
    with pytest.raises(BadRequest):
        run(safe_edit_callback_message(query, "Healed episode 10."))


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
