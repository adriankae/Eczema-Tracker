from __future__ import annotations

from pathlib import Path

from czm_cli.config import (
    AppConfig,
    MASK,
    TelegramConfig,
    apply_env_overrides,
    load_app_config,
    normalize_base_url,
    render_app_config,
    write_app_config,
)
from czm_cli.errors import ConfigError


def load_telegram_app_config(path: Path | None = None, *, include_env: bool = True) -> AppConfig:
    config = load_app_config(path)
    return apply_env_overrides(config) if include_env else config


def masked_token(value: str | None) -> str:
    return MASK if value else "not configured"


def validate_telegram_config(config: AppConfig) -> None:
    normalize_base_url(config.base_url)
    if not config.api_key:
        raise ConfigError("api_key is required")
    if not config.telegram.bot_token:
        raise ConfigError("telegram.bot_token is required")
    if not config.telegram.allowed_chat_ids:
        raise ConfigError("telegram.allowed_chat_ids must contain at least one chat id")
    if config.telegram.command_mode != "buttons":
        raise ConfigError('telegram.command_mode must be "buttons"')


def telegram_status_lines(config: AppConfig) -> list[str]:
    token = masked_token(config.telegram.bot_token)
    api_key = masked_token(config.api_key)
    chat_ids = ", ".join(str(chat_id) for chat_id in config.telegram.allowed_chat_ids) or "none"
    user_ids = ", ".join(str(user_id) for user_id in config.telegram.allowed_user_ids) or "none"
    return [
        f"backend_url: {config.base_url}",
        f"api_key: {api_key}",
        f"timezone: {config.timezone}",
        f"telegram_bot_token: {token}",
        f"allowed_chat_ids: {chat_ids}",
        f"allowed_user_ids: {user_ids}",
        f"allow_writes: {str(config.telegram.allow_writes).lower()}",
        f"allow_adherence_rebuild: {str(config.telegram.allow_adherence_rebuild).lower()}",
        f"default_subject: {config.telegram.default_subject or 'none'}",
        f"default_location: {config.telegram.default_location or 'none'}",
        f"command_mode: {config.telegram.command_mode}",
    ]


def config_to_display(config: AppConfig, *, show_secrets: bool) -> str:
    return render_app_config(config, show_secrets=show_secrets)


def update_telegram_config(path: Path, telegram: TelegramConfig, *, base: AppConfig | None = None) -> AppConfig:
    config = base or load_app_config(path)
    config.telegram = telegram
    write_app_config(path, config, overwrite=True)
    return config

