from __future__ import annotations

import getpass
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from czm_cli.config import AppConfig, DEFAULT_BASE_URL, TelegramConfig, TelegramReminderConfig, normalize_base_url, write_app_config
from czm_cli.errors import CzmError, EXIT_CONFLICT, EXIT_USAGE
from czm_cli.telegram.config import validate_telegram_config


@dataclass(slots=True)
class TelegramBotInfo:
    username: str
    id: int | None = None


@dataclass(slots=True)
class DiscoveredChat:
    id: int
    type: str
    title: str
    user_id: int | None = None


def validate_backend(base_url: str) -> None:
    try:
        response = httpx.get(f"{normalize_base_url(base_url)}/health", timeout=10)
    except httpx.HTTPError as exc:
        raise CzmError("backend health check failed; check base_url", exit_code=EXIT_CONFLICT) from exc
    if response.status_code >= 400:
        raise CzmError("backend health check failed; check base_url", exit_code=EXIT_CONFLICT)


def create_api_key_from_login(*, base_url: str, username: str, password: str, api_key_name: str = "zema-telegram") -> str:
    normalized = normalize_base_url(base_url)
    with httpx.Client(base_url=normalized, headers={"Accept": "application/json", "Content-Type": "application/json"}) as client:
        login = client.post("/auth/login", json={"username": username, "password": password})
        if login.status_code >= 400:
            raise CzmError("backend login failed; check username/password and base_url", exit_code=EXIT_CONFLICT)
        token = login.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise CzmError("login response did not include an access token", exit_code=EXIT_USAGE)
        api_key = client.post("/api-keys", headers={"Authorization": f"Bearer {token}"}, json={"name": api_key_name})
        if api_key.status_code >= 400:
            raise CzmError("API key creation failed; check backend access", exit_code=EXIT_CONFLICT)
        plaintext_key = api_key.json().get("plaintext_key")
        if not isinstance(plaintext_key, str) or not plaintext_key:
            raise CzmError("API key response did not include a plaintext key", exit_code=EXIT_USAGE)
        return plaintext_key


def validate_bot_token(bot_token: str) -> TelegramBotInfo:
    try:
        response = httpx.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
    except httpx.HTTPError as exc:
        raise CzmError("Telegram bot token validation failed", exit_code=EXIT_CONFLICT) from exc
    if response.status_code >= 400:
        raise CzmError("Telegram bot token validation failed", exit_code=EXIT_CONFLICT)
    result = response.json().get("result")
    if not isinstance(result, dict) or not result.get("username"):
        raise CzmError("Telegram getMe response did not include a bot username", exit_code=EXIT_USAGE)
    bot_id = result.get("id")
    return TelegramBotInfo(username=str(result["username"]), id=bot_id if isinstance(bot_id, int) else None)


def discover_chats(bot_token: str) -> list[DiscoveredChat]:
    try:
        response = httpx.get(f"https://api.telegram.org/bot{bot_token}/getUpdates", timeout=20)
    except httpx.HTTPError as exc:
        raise CzmError("Telegram chat discovery failed", exit_code=EXIT_CONFLICT) from exc
    if response.status_code >= 400:
        raise CzmError("Telegram chat discovery failed", exit_code=EXIT_CONFLICT)
    updates = response.json().get("result")
    if not isinstance(updates, list):
        return []
    chats: dict[int, DiscoveredChat] = {}
    for update in updates:
        chat, user = _chat_from_update(update)
        if chat:
            chats[chat.id] = DiscoveredChat(id=chat.id, type=chat.type, title=chat.title, user_id=user)
    return list(chats.values())


def _chat_from_update(update: Any) -> tuple[DiscoveredChat | None, int | None]:
    if not isinstance(update, dict):
        return None, None
    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return None, None
    chat_data = message.get("chat")
    if not isinstance(chat_data, dict) or not isinstance(chat_data.get("id"), int):
        return None, None
    user_data = message.get("from")
    user_id = user_data.get("id") if isinstance(user_data, dict) and isinstance(user_data.get("id"), int) else None
    title = chat_data.get("title") or chat_data.get("username") or " ".join(str(chat_data.get(key) or "") for key in ("first_name", "last_name")).strip() or "unknown"
    return DiscoveredChat(id=chat_data["id"], type=str(chat_data.get("type") or "unknown"), title=str(title), user_id=user_id), user_id


def run_noninteractive_setup(
    *,
    config_path: Path,
    base_url: str,
    api_key: str,
    bot_token: str,
    allowed_chat_ids: list[int],
    allowed_user_ids: list[int],
    timezone: str,
    allow_writes: bool,
    allow_adherence_rebuild: bool,
    default_subject: str,
    default_location: str,
    overwrite: bool,
) -> AppConfig:
    validate_backend(base_url)
    validate_bot_token(bot_token)
    config = AppConfig(
        base_url=normalize_base_url(base_url),
        api_key=api_key,
        timezone=timezone,
        telegram=TelegramConfig(
            bot_token=bot_token,
            allowed_chat_ids=allowed_chat_ids,
            allowed_user_ids=allowed_user_ids,
            allow_writes=allow_writes,
            allow_adherence_rebuild=allow_adherence_rebuild,
            default_subject=default_subject,
            default_location=default_location,
            reminders=TelegramReminderConfig(timezone=timezone),
        ),
    )
    validate_telegram_config(config)
    write_app_config(config_path, config, overwrite=overwrite)
    return config


def prompt(text: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def secure_prompt(text: str) -> str:
    return getpass.getpass(f"{text}: ").strip()
