from __future__ import annotations

import shlex
from dataclasses import dataclass, field

from czm_cli.errors import CzmError, EXIT_USAGE


SUPPORTED_COMMANDS = {
    "start",
    "menu",
    "help",
    "status",
    "subjects",
    "subject_create",
    "locations",
    "location_create",
    "location_image_set",
    "episodes",
    "episode",
    "episode_create",
    "due",
    "log",
    "events",
    "timeline",
    "adherence",
    "adherence_calendar",
    "adherence_missed",
    "adherence_rebuild",
}

UNSAFE_TOKENS = {";", "|", "&", "$", "`", "<", ">"}


@dataclass(slots=True)
class ParsedTelegramCommand:
    command: str
    positionals: list[str] = field(default_factory=list)
    options: dict[str, str] = field(default_factory=dict)


def parse_telegram_command(text: str) -> ParsedTelegramCommand:
    stripped = text.strip()
    if not stripped.startswith("/"):
        raise CzmError("send /help for available commands", exit_code=EXIT_USAGE)
    if any(token in stripped for token in UNSAFE_TOKENS):
        raise CzmError("unsupported command syntax; send /help", exit_code=EXIT_USAGE)
    try:
        parts = shlex.split(stripped)
    except ValueError as exc:
        raise CzmError("could not parse command; check quotes", exit_code=EXIT_USAGE) from exc
    if not parts:
        raise CzmError("send /help for available commands", exit_code=EXIT_USAGE)
    command = parts[0].split("@", 1)[0].removeprefix("/")
    if command == "zema":
        raise CzmError("/zema passthrough is not supported; send /help", exit_code=EXIT_USAGE)
    if command not in SUPPORTED_COMMANDS:
        raise CzmError("unknown command; send /help", exit_code=EXIT_USAGE)
    positionals: list[str] = []
    options: dict[str, str] = {}
    for token in parts[1:]:
        if ":" in token:
            key, value = token.split(":", 1)
            if not key or not value:
                raise CzmError("invalid key:value argument; send /help", exit_code=EXIT_USAGE)
            if key in options:
                raise CzmError(f"duplicate argument: {key}", exit_code=EXIT_USAGE)
            options[key] = value
        else:
            positionals.append(token)
    return ParsedTelegramCommand(command=command, positionals=positionals, options=options)


def require_no_options(parsed: ParsedTelegramCommand) -> None:
    if parsed.options:
        raise CzmError("unsupported arguments; send /help", exit_code=EXIT_USAGE)


def require_options(parsed: ParsedTelegramCommand, allowed: set[str]) -> None:
    unknown = set(parsed.options) - allowed
    if unknown:
        raise CzmError(f"unsupported argument: {sorted(unknown)[0]}", exit_code=EXIT_USAGE)


def require_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CzmError(f"{label} must be an integer", exit_code=EXIT_USAGE) from exc
