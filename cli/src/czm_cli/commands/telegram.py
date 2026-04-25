from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import (
    TelegramConfig,
    apply_env_overrides,
    load_app_config,
    parse_bool,
    render_app_config,
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
