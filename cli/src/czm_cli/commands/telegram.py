from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import (
    TelegramConfig,
    apply_env_overrides,
    load_app_config,
    parse_bool,
    parse_hhmm,
    parse_positive_int,
    render_app_config,
    validate_timezone_name,
    write_app_config,
    xdg_config_path,
)
from ..telegram.config import config_to_display, load_telegram_app_config, telegram_status_lines, validate_telegram_config
from ..telegram.runtime import run_polling
from ..telegram.setup import validate_backend, validate_bot_token


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("telegram", parents=[parent], help="Manage Telegram bot config")
    telegram_subparsers = parser.add_subparsers(dest="telegram_command", required=True)

    test = telegram_subparsers.add_parser("test", parents=[parent], help="Validate Telegram and backend connectivity")
    test.set_defaults(handler=handle_test)

    status = telegram_subparsers.add_parser("status", parents=[parent], help="Show Telegram config status")
    status.set_defaults(handler=handle_status)

    run = telegram_subparsers.add_parser("run", parents=[parent], help="Run Telegram bot long polling")
    run.set_defaults(handler=handle_run)

    config = telegram_subparsers.add_parser("config", parents=[parent], help="Inspect and edit Telegram config")
    config_subparsers = config.add_subparsers(dest="telegram_config_command", required=True)

    show = config_subparsers.add_parser("show", parents=[parent], help="Show Telegram config")
    show.add_argument("--show-secrets", action="store_true")
    show.set_defaults(handler=handle_config_show)

    validate = config_subparsers.add_parser("validate", parents=[parent], help="Validate Telegram config")
    validate.set_defaults(handler=handle_config_validate)

    set_token = config_subparsers.add_parser("set-token", parents=[parent], help="Set Telegram bot token")
    set_token.add_argument("token")
    set_token.set_defaults(handler=handle_set_token)

    add_chat = config_subparsers.add_parser("add-chat", parents=[parent], help="Allow a Telegram chat")
    add_chat.add_argument("chat_id", type=int)
    add_chat.set_defaults(handler=handle_add_chat)

    remove_chat = config_subparsers.add_parser("remove-chat", parents=[parent], help="Remove an allowed Telegram chat")
    remove_chat.add_argument("chat_id", type=int)
    remove_chat.set_defaults(handler=handle_remove_chat)

    add_user = config_subparsers.add_parser("add-user", parents=[parent], help="Allow a Telegram user")
    add_user.add_argument("user_id", type=int)
    add_user.set_defaults(handler=handle_add_user)

    remove_user = config_subparsers.add_parser("remove-user", parents=[parent], help="Remove an allowed Telegram user")
    remove_user.add_argument("user_id", type=int)
    remove_user.set_defaults(handler=handle_remove_user)

    allow_writes = config_subparsers.add_parser("allow-writes", parents=[parent], help="Enable or disable Telegram write commands")
    allow_writes.add_argument("value")
    allow_writes.set_defaults(handler=handle_allow_writes)

    allow_rebuild = config_subparsers.add_parser("allow-adherence-rebuild", parents=[parent], help="Enable or disable Telegram adherence rebuild")
    allow_rebuild.add_argument("value")
    allow_rebuild.set_defaults(handler=handle_allow_adherence_rebuild)

    reminders = config_subparsers.add_parser("reminders", parents=[parent], help="Inspect and edit Telegram reminders")
    reminders_subparsers = reminders.add_subparsers(dest="telegram_reminders_command", required=True)

    reminders_show = reminders_subparsers.add_parser("show", parents=[parent], help="Show reminder config")
    reminders_show.set_defaults(handler=handle_reminders_show)

    reminders_enable = reminders_subparsers.add_parser("enable", parents=[parent], help="Enable reminders")
    reminders_enable.set_defaults(handler=handle_reminders_enable)

    reminders_disable = reminders_subparsers.add_parser("disable", parents=[parent], help="Disable reminders")
    reminders_disable.set_defaults(handler=handle_reminders_disable)

    reminders_morning = reminders_subparsers.add_parser("set-morning", parents=[parent], help="Set morning reminder time")
    reminders_morning.add_argument("time")
    reminders_morning.set_defaults(handler=handle_reminders_set_morning)

    reminders_evening = reminders_subparsers.add_parser("set-evening", parents=[parent], help="Set evening reminder time")
    reminders_evening.add_argument("time")
    reminders_evening.set_defaults(handler=handle_reminders_set_evening)

    reminders_snooze = reminders_subparsers.add_parser("set-snooze", parents=[parent], help="Set reminder snooze minutes")
    reminders_snooze.add_argument("minutes")
    reminders_snooze.set_defaults(handler=handle_reminders_set_snooze)

    reminders_images = reminders_subparsers.add_parser("images", parents=[parent], help="Enable or disable reminder images")
    reminders_images.add_argument("value")
    reminders_images.set_defaults(handler=handle_reminders_images)


def _path(args) -> Path:
    return getattr(args, "config", None) or xdg_config_path()


def _emit(args, payload, text: str) -> None:
    if bool(getattr(args, "json", False)):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(text)


def _load(path: Path):
    return load_app_config(path)


def _save(path: Path, config) -> None:
    write_app_config(path, config, overwrite=True)


def _dedupe_append(values: list[int], value: int) -> list[int]:
    return values if value in values else [*values, value]


def handle_test(ctx, args) -> int:
    config = load_telegram_app_config(_path(args), include_env=True)
    validate_telegram_config(config)
    validate_backend(config.base_url)
    bot = validate_bot_token(config.telegram.bot_token or "")
    _emit(args, {"status": "ok", "bot_username": bot.username}, f"Telegram config OK (@{bot.username})")
    return 0


def handle_status(ctx, args) -> int:
    config = apply_env_overrides(_load(_path(args)))
    _emit(args, {"status": telegram_status_lines(config)}, "\n".join(telegram_status_lines(config)))
    return 0


def handle_run(ctx, args) -> int:
    config = load_telegram_app_config(_path(args), include_env=True)
    validate_backend(config.base_url)
    run_polling(config)
    return 0


def handle_config_show(ctx, args) -> int:
    config = apply_env_overrides(_load(_path(args)))
    output = config_to_display(config, show_secrets=args.show_secrets)
    if bool(getattr(args, "json", False)):
        print(json.dumps({"config": output}, ensure_ascii=False))
    else:
        print(output, end="")
    return 0


def handle_config_validate(ctx, args) -> int:
    validate_telegram_config(apply_env_overrides(_load(_path(args))))
    _emit(args, {"status": "ok"}, "Telegram config OK")
    return 0


def handle_set_token(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.bot_token = args.token
    _save(path, config)
    _emit(args, {"status": "ok"}, "Updated telegram.bot_token")
    return 0


def handle_add_chat(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.allowed_chat_ids = _dedupe_append(config.telegram.allowed_chat_ids, args.chat_id)
    _save(path, config)
    _emit(args, {"status": "ok", "allowed_chat_ids": config.telegram.allowed_chat_ids}, f"Added chat {args.chat_id}")
    return 0


def handle_remove_chat(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.allowed_chat_ids = [chat_id for chat_id in config.telegram.allowed_chat_ids if chat_id != args.chat_id]
    _save(path, config)
    _emit(args, {"status": "ok", "allowed_chat_ids": config.telegram.allowed_chat_ids}, f"Removed chat {args.chat_id}")
    return 0


def handle_add_user(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.allowed_user_ids = _dedupe_append(config.telegram.allowed_user_ids, args.user_id)
    _save(path, config)
    _emit(args, {"status": "ok", "allowed_user_ids": config.telegram.allowed_user_ids}, f"Added user {args.user_id}")
    return 0


def handle_remove_user(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.allowed_user_ids = [user_id for user_id in config.telegram.allowed_user_ids if user_id != args.user_id]
    _save(path, config)
    _emit(args, {"status": "ok", "allowed_user_ids": config.telegram.allowed_user_ids}, f"Removed user {args.user_id}")
    return 0


def handle_allow_writes(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.allow_writes = parse_bool(args.value, label="allow-writes")
    _save(path, config)
    _emit(args, {"status": "ok", "allow_writes": config.telegram.allow_writes}, f"allow_writes: {str(config.telegram.allow_writes).lower()}")
    return 0


def handle_allow_adherence_rebuild(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.allow_adherence_rebuild = parse_bool(args.value, label="allow-adherence-rebuild")
    _save(path, config)
    _emit(
        args,
        {"status": "ok", "allow_adherence_rebuild": config.telegram.allow_adherence_rebuild},
        f"allow_adherence_rebuild: {str(config.telegram.allow_adherence_rebuild).lower()}",
    )
    return 0


def _reminder_lines(config) -> list[str]:
    reminder_timezone = config.telegram.reminders.timezone or config.timezone
    return [
        f"enabled: {str(config.telegram.reminders.enabled).lower()}",
        f"morning_time: {config.telegram.reminders.morning_time}",
        f"evening_time: {config.telegram.reminders.evening_time}",
        f"timezone: {reminder_timezone}",
        f"send_location_images: {str(config.telegram.reminders.send_location_images).lower()}",
        f"snooze_minutes: {config.telegram.reminders.snooze_minutes}",
    ]


def handle_reminders_show(ctx, args) -> int:
    config = apply_env_overrides(_load(_path(args)))
    _emit(args, {"reminders": _reminder_lines(config)}, "\n".join(_reminder_lines(config)))
    return 0


def handle_reminders_enable(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.reminders.enabled = True
    _save(path, config)
    _emit(args, {"status": "ok", "enabled": True}, "reminders_enabled: true")
    return 0


def handle_reminders_disable(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    config.telegram.reminders.enabled = False
    _save(path, config)
    _emit(args, {"status": "ok", "enabled": False}, "reminders_enabled: false")
    return 0


def handle_reminders_set_morning(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    parse_hhmm(args.time, label="morning reminder time")
    config.telegram.reminders.morning_time = args.time
    _save(path, config)
    _emit(args, {"status": "ok", "morning_time": args.time}, f"morning_time: {args.time}")
    return 0


def handle_reminders_set_evening(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    parse_hhmm(args.time, label="evening reminder time")
    config.telegram.reminders.evening_time = args.time
    _save(path, config)
    _emit(args, {"status": "ok", "evening_time": args.time}, f"evening_time: {args.time}")
    return 0


def handle_reminders_set_snooze(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    minutes = parse_positive_int(args.minutes, label="snooze minutes")
    config.telegram.reminders.snooze_minutes = minutes
    _save(path, config)
    _emit(args, {"status": "ok", "snooze_minutes": minutes}, f"snooze_minutes: {minutes}")
    return 0


def handle_reminders_images(ctx, args) -> int:
    path = _path(args)
    config = _load(path)
    enabled = parse_bool(args.value, label="reminder images")
    config.telegram.reminders.send_location_images = enabled
    _save(path, config)
    _emit(args, {"status": "ok", "send_location_images": enabled}, f"send_location_images: {str(enabled).lower()}")
    return 0
