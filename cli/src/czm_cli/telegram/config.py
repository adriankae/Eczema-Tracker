from __future__ import annotations

from pathlib import Path

from czm_cli.config import (
    AppConfig,
    MASK,
    TelegramConfig,
    apply_env_overrides,
    load_app_config,
    normalize_base_url,
    parse_hhmm,
    render_app_config,
    validate_timezone_name,
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
    parse_hhmm(config.telegram.reminders.morning_time, label="telegram.reminders.morning_time")
    parse_hhmm(config.telegram.reminders.evening_time, label="telegram.reminders.evening_time")
    reminder_timezone = config.telegram.reminders.timezone or config.timezone
    validate_timezone_name(reminder_timezone, label="telegram.reminders.timezone")
    if config.telegram.reminders.snooze_minutes < 1:
        raise ConfigError("telegram.reminders.snooze_minutes must be a positive integer")


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
        f"reminders_enabled: {str(config.telegram.reminders.enabled).lower()}",
        f"reminder_morning_time: {config.telegram.reminders.morning_time}",
        f"reminder_evening_time: {config.telegram.reminders.evening_time}",
        f"reminder_timezone: {config.telegram.reminders.timezone or config.timezone}",
        f"reminder_send_location_images: {str(config.telegram.reminders.send_location_images).lower()}",
        f"reminder_snooze_minutes: {config.telegram.reminders.snooze_minutes}",
    ]


def config_to_display(config: AppConfig, *, show_secrets: bool) -> str:
    return render_app_config(config, show_secrets=show_secrets)


def update_telegram_config(path: Path, telegram: TelegramConfig, *, base: AppConfig | None = None) -> AppConfig:
    config = base or load_app_config(path)
    config.telegram = telegram
    write_app_config(path, config, overwrite=True)
    return config
