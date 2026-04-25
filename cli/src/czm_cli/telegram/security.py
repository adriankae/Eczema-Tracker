from __future__ import annotations

from dataclasses import dataclass

from czm_cli.config import TelegramConfig
from czm_cli.errors import CzmError, EXIT_AUTH


@dataclass(slots=True)
class TelegramIdentity:
    chat_id: int | None
    user_id: int | None


def identity_from_update(update) -> TelegramIdentity:
    chat = getattr(update, "effective_chat", None)
    user = getattr(update, "effective_user", None)
    return TelegramIdentity(
        chat_id=getattr(chat, "id", None),
        user_id=getattr(user, "id", None),
    )


def ensure_allowed(config: TelegramConfig, identity: TelegramIdentity) -> None:
    if identity.chat_id not in config.allowed_chat_ids:
        raise CzmError("This Telegram chat is not allowed to use Zema.", exit_code=EXIT_AUTH)
    if config.allowed_user_ids and identity.user_id not in config.allowed_user_ids:
        raise CzmError("This Telegram user is not allowed to use Zema.", exit_code=EXIT_AUTH)


def ensure_writes_allowed(config: TelegramConfig) -> None:
    if not config.allow_writes:
        raise CzmError("Telegram write commands are disabled.", exit_code=EXIT_AUTH)


def ensure_rebuild_allowed(config: TelegramConfig) -> None:
    if not config.allow_adherence_rebuild:
        raise CzmError("Telegram adherence rebuild is disabled.", exit_code=EXIT_AUTH)

