from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..bootstrap import DEFAULT_BASE_URL, BootstrapResult, bootstrap_config, detect_local_timezone
from ..config import TelegramReminderConfig, apply_env_overrides, load_app_config, parse_bool, write_app_config, xdg_config_path
from ..errors import CzmError, EXIT_USAGE
from ..telegram.setup import (
    create_api_key_from_login,
    discover_chats,
    prompt,
    run_noninteractive_setup,
    secure_prompt,
    validate_backend,
    validate_bot_token,
)


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("setup", parents=[parent], help="Create config.toml from backend login")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--api-key-name", default="czm-cli")
    parser.add_argument("--overwrite", action="store_true")
    setup_subparsers = parser.add_subparsers(dest="setup_command")
    telegram = setup_subparsers.add_parser("telegram", parents=[parent], help="Configure Telegram bot support")
    telegram.add_argument("--bot-token")
    telegram.add_argument("--allowed-chat-id", type=int, action="append", default=[])
    telegram.add_argument("--allowed-user-id", type=int, action="append", default=[])
    telegram.add_argument("--default-subject", default="")
    telegram.add_argument("--default-location", default="")
    telegram.add_argument("--allow-adherence-rebuild", action="store_true")
    telegram.add_argument("--yes", action="store_true")
    telegram.add_argument("--overwrite", action="store_true")
    writes = telegram.add_mutually_exclusive_group()
    writes.add_argument("--allow-writes", dest="allow_writes", action="store_true", default=True)
    writes.add_argument("--no-allow-writes", dest="allow_writes", action="store_false")
    telegram.set_defaults(handler=handle_telegram_setup)
    parser.set_defaults(handler=handle_setup)


def _config_path(args) -> Path:
    return getattr(args, "config", None) or xdg_config_path()


def _timezone(args) -> str:
    return getattr(args, "timezone", None) or detect_local_timezone()


def _emit(result: BootstrapResult, *, json_output: bool) -> None:
    if json_output:
        print(
            json.dumps(
                {
                    "config_path": str(result.config_path),
                    "base_url": result.base_url,
                    "username": result.username,
                    "api_key_name": result.api_key_name,
                    "timezone": result.timezone,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"Wrote config to {result.config_path}")
        print("Next: run `czm subject list`")


def handle_setup(ctx, args) -> int:
    if getattr(args, "setup_command", None) == "telegram":
        return handle_telegram_setup(ctx, args)
    result = bootstrap_config(
        base_url=getattr(args, "base_url", DEFAULT_BASE_URL) or DEFAULT_BASE_URL,
        username=args.username,
        password=args.password,
        api_key_name=args.api_key_name,
        timezone=_timezone(args),
        config_path=_config_path(args),
        overwrite=args.overwrite,
    )
    _emit(result, json_output=bool(getattr(args, "json", False)))
    return 0


def _emit_telegram_setup(config_path: Path, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps({"config_path": str(config_path), "status": "ok"}, ensure_ascii=False))
    else:
        print(f"Wrote Telegram config to {config_path}")
        print("Next:")
        print("  zema telegram test")
        print("  zema telegram run")
        print("  docker compose --profile telegram up zema-telegram")


def _interactive_chat_ids(bot_token: str) -> list[int]:
    input("Send /start to your Telegram bot, then press Enter to discover chats.")
    chats = discover_chats(bot_token)
    if chats:
        print("Discovered chats:")
        for index, chat in enumerate(chats, start=1):
            print(f"  [{index}] {chat.id} - {chat.type} - {chat.title}")
        selected = prompt("Select chat numbers separated by comma, or paste chat IDs manually")
        selected_ids = []
        for part in selected.split(","):
            value = part.strip()
            if not value:
                continue
            if value.isdigit() and 1 <= int(value) <= len(chats):
                selected_ids.append(chats[int(value) - 1].id)
            else:
                selected_ids.append(int(value))
        return selected_ids
    manual = prompt("No chats found. Paste allowed chat IDs separated by comma")
    return [int(part.strip()) for part in manual.split(",") if part.strip()]


def handle_telegram_setup(ctx, args) -> int:
    config_path = _config_path(args)
    existing = apply_env_overrides(load_app_config(config_path))
    base_url = getattr(args, "base_url", None) or existing.base_url or DEFAULT_BASE_URL
    timezone = getattr(args, "timezone", None) or existing.timezone or detect_local_timezone()
    if args.yes:
        api_key = args.api_key or existing.api_key
        if not api_key:
            raise CzmError("--api-key is required for non-interactive Telegram setup", exit_code=EXIT_USAGE)
        if not args.bot_token:
            raise CzmError("--bot-token is required for non-interactive Telegram setup", exit_code=EXIT_USAGE)
        if not args.allowed_chat_id:
            raise CzmError("--allowed-chat-id is required for non-interactive Telegram setup", exit_code=EXIT_USAGE)
        run_noninteractive_setup(
            config_path=config_path,
            base_url=base_url,
            api_key=api_key,
            bot_token=args.bot_token,
            allowed_chat_ids=list(args.allowed_chat_id),
            allowed_user_ids=list(args.allowed_user_id),
            timezone=timezone,
            allow_writes=bool(args.allow_writes),
            allow_adherence_rebuild=bool(args.allow_adherence_rebuild),
            default_subject=args.default_subject,
            default_location=args.default_location,
            overwrite=True,
        )
        _emit_telegram_setup(config_path, json_output=bool(getattr(args, "json", False)))
        return 0

    print("Zema Telegram Setup")
    print(f"Config path: {config_path}")
    if config_path.exists() and not args.overwrite:
        answer = prompt("Config exists. Merge Telegram settings into this config?", default="Y")
        if answer.lower() not in {"y", "yes"}:
            raise CzmError("setup cancelled", exit_code=EXIT_USAGE)
    base_url = prompt("Backend base URL", default=base_url)
    validate_backend(base_url)
    api_key = existing.api_key
    api_key_choice = prompt("API key source: existing, paste, or login", default="existing" if api_key else "paste").lower()
    if api_key_choice == "paste":
        api_key = secure_prompt("Zema API key")
    elif api_key_choice == "login":
        username = prompt("Username", default="admin")
        password = secure_prompt("Password")
        api_key = create_api_key_from_login(base_url=base_url, username=username, password=password, api_key_name="zema-telegram")
    if not api_key:
        raise CzmError("API key is required", exit_code=EXIT_USAGE)
    bot_token = secure_prompt("Telegram bot token")
    bot = validate_bot_token(bot_token)
    print(f"Token check: OK (@{bot.username})")
    allowed_chat_ids = _interactive_chat_ids(bot_token)
    allowed_user_text = prompt("Allowed user IDs separated by comma (optional)")
    allowed_user_ids = [int(part.strip()) for part in allowed_user_text.split(",") if part.strip()]
    print("Write commands: enabled for allowlisted chats/users.")
    allow_rebuild = parse_bool(prompt("Enable adherence rebuild from Telegram? yes/no", default="no"), label="adherence rebuild")
    timezone = prompt("Timezone", default=timezone)
    default_subject = prompt("Default subject (optional)")
    default_location = prompt("Default location (optional)")
    existing.base_url = base_url
    existing.api_key = api_key
    existing.timezone = timezone
    existing.telegram.bot_token = bot_token
    existing.telegram.allowed_chat_ids = allowed_chat_ids
    existing.telegram.allowed_user_ids = allowed_user_ids
    existing.telegram.allow_writes = True
    existing.telegram.allow_adherence_rebuild = allow_rebuild
    existing.telegram.default_subject = default_subject
    existing.telegram.default_location = default_location
    existing.telegram.reminders = TelegramReminderConfig(timezone=timezone)
    write_app_config(config_path, existing, overwrite=True)
    _emit_telegram_setup(config_path, json_output=bool(getattr(args, "json", False)))
    return 0
