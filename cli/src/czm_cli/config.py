from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import os
import tomllib

from .errors import ConfigError, CzmError, EXIT_CONFLICT

DEFAULT_BASE_URL = "http://localhost:28173"
MASK = "********"


def xdg_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "czm" / "config.toml"


@dataclass(slots=True)
class RuntimeConfig:
    base_url: str
    api_key: str
    timezone: str = "UTC"

    def normalized_base_url(self) -> str:
        return normalize_base_url(self.base_url)


@dataclass(slots=True)
class TelegramConfig:
    bot_token: str | None = None
    allowed_chat_ids: list[int] = field(default_factory=list)
    allowed_user_ids: list[int] = field(default_factory=list)
    allow_writes: bool = True
    allow_adherence_rebuild: bool = False
    default_subject: str = ""
    default_location: str = ""
    command_mode: str = "buttons"


@dataclass(slots=True)
class AppConfig:
    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = None
    timezone: str = "UTC"
    telegram: TelegramConfig = field(default_factory=TelegramConfig)


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_int_list(values: list[int]) -> str:
    return "[" + ", ".join(str(value) for value in values) + "]"


def render_app_config(config: AppConfig, *, show_secrets: bool = True) -> str:
    api_key = config.api_key or ""
    bot_token = config.telegram.bot_token or ""
    if not show_secrets:
        api_key = MASK if api_key else ""
        bot_token = MASK if bot_token else ""
    return "\n".join(
        [
            f"base_url = {_toml_string(normalize_base_url(config.base_url))}",
            f"api_key = {_toml_string(api_key)}",
            f"timezone = {_toml_string(config.timezone)}",
            "",
            "[telegram]",
            f"bot_token = {_toml_string(bot_token)}",
            f"allowed_chat_ids = {_render_int_list(config.telegram.allowed_chat_ids)}",
            f"allowed_user_ids = {_render_int_list(config.telegram.allowed_user_ids)}",
            f"allow_writes = {str(config.telegram.allow_writes).lower()}",
            f"allow_adherence_rebuild = {str(config.telegram.allow_adherence_rebuild).lower()}",
            f"default_subject = {_toml_string(config.telegram.default_subject)}",
            f"default_location = {_toml_string(config.telegram.default_location)}",
            f"command_mode = {_toml_string(config.telegram.command_mode)}",
            "",
        ]
    )


def render_runtime_config(config: RuntimeConfig) -> str:
    return (
        f'base_url = "{config.normalized_base_url()}"\n'
        f'api_key = "{config.api_key}"\n'
        f'timezone = "{config.timezone}"\n'
    )


def write_runtime_config(path: Path, config: RuntimeConfig, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise CzmError(f"config file already exists: {path}", exit_code=EXIT_CONFLICT)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(render_runtime_config(config), encoding="utf-8")
    tmp_path.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def write_app_config(path: Path, config: AppConfig, *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise CzmError(f"config file already exists: {path}", exit_code=EXIT_CONFLICT)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(render_app_config(config), encoding="utf-8")
    tmp_path.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("base_url must be an http or https URL")
    normalized = value.rstrip("/")
    return normalized


def load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ConfigError(f"config file {path} must contain a TOML table")
    return data


def _as_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def _as_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key)
    return value if isinstance(value, bool) else default


def _as_int_list(data: dict[str, Any], key: str) -> list[int]:
    value = data.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, int) for item in value):
        raise ConfigError(f"telegram.{key} must be a list of integers")
    return list(value)


def parse_bool(value: str, *, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"{label} must be true or false")


def parse_int_list(value: str, *, label: str) -> list[int]:
    if value.strip() == "":
        return []
    parsed = []
    for part in value.split(","):
        try:
            parsed.append(int(part.strip()))
        except ValueError as exc:
            raise ConfigError(f"{label} must be a comma-separated list of integers") from exc
    return parsed


def load_app_config(path: Path | None = None) -> AppConfig:
    file_data = load_config_file(path or xdg_config_path())
    telegram_data = file_data.get("telegram")
    if telegram_data is None:
        telegram_data = {}
    if not isinstance(telegram_data, dict):
        raise ConfigError("telegram config must be a TOML table")
    telegram = TelegramConfig(
        bot_token=_as_str(telegram_data, "bot_token"),
        allowed_chat_ids=_as_int_list(telegram_data, "allowed_chat_ids"),
        allowed_user_ids=_as_int_list(telegram_data, "allowed_user_ids"),
        allow_writes=_as_bool(telegram_data, "allow_writes", True),
        allow_adherence_rebuild=_as_bool(telegram_data, "allow_adherence_rebuild", False),
        default_subject=_as_str(telegram_data, "default_subject") or "",
        default_location=_as_str(telegram_data, "default_location") or "",
        command_mode=_as_str(telegram_data, "command_mode") or "buttons",
    )
    return AppConfig(
        base_url=_as_str(file_data, "base_url") or DEFAULT_BASE_URL,
        api_key=_as_str(file_data, "api_key"),
        timezone=_as_str(file_data, "timezone") or "UTC",
        telegram=telegram,
    )


def apply_env_overrides(config: AppConfig) -> AppConfig:
    base_url = os.environ.get("CZM_BASE_URL") or config.base_url
    api_key = os.environ.get("CZM_API_KEY") or config.api_key
    timezone = os.environ.get("CZM_TIMEZONE") or config.timezone
    telegram = TelegramConfig(
        bot_token=os.environ.get("ZEMA_TELEGRAM_BOT_TOKEN") or config.telegram.bot_token,
        allowed_chat_ids=(
            parse_int_list(os.environ["ZEMA_TELEGRAM_ALLOWED_CHAT_IDS"], label="ZEMA_TELEGRAM_ALLOWED_CHAT_IDS")
            if "ZEMA_TELEGRAM_ALLOWED_CHAT_IDS" in os.environ
            else list(config.telegram.allowed_chat_ids)
        ),
        allowed_user_ids=(
            parse_int_list(os.environ["ZEMA_TELEGRAM_ALLOWED_USER_IDS"], label="ZEMA_TELEGRAM_ALLOWED_USER_IDS")
            if "ZEMA_TELEGRAM_ALLOWED_USER_IDS" in os.environ
            else list(config.telegram.allowed_user_ids)
        ),
        allow_writes=(
            parse_bool(os.environ["ZEMA_TELEGRAM_ALLOW_WRITES"], label="ZEMA_TELEGRAM_ALLOW_WRITES")
            if "ZEMA_TELEGRAM_ALLOW_WRITES" in os.environ
            else config.telegram.allow_writes
        ),
        allow_adherence_rebuild=(
            parse_bool(os.environ["ZEMA_TELEGRAM_ALLOW_ADHERENCE_REBUILD"], label="ZEMA_TELEGRAM_ALLOW_ADHERENCE_REBUILD")
            if "ZEMA_TELEGRAM_ALLOW_ADHERENCE_REBUILD" in os.environ
            else config.telegram.allow_adherence_rebuild
        ),
        default_subject=config.telegram.default_subject,
        default_location=config.telegram.default_location,
        command_mode=config.telegram.command_mode,
    )
    return AppConfig(base_url=base_url, api_key=api_key, timezone=timezone, telegram=telegram)


def _pick_value(flag_value: str | None, env_name: str, file_data: dict[str, Any], key: str) -> str | None:
    if flag_value is not None and flag_value != "":
        return flag_value
    env_value = os.environ.get(env_name)
    if env_value is not None and env_value != "":
        return env_value
    file_value = file_data.get(key)
    return file_value if isinstance(file_value, str) and file_value != "" else None


def resolve_runtime_config(*, base_url: str | None, api_key: str | None, timezone: str | None, config_path: Path | None) -> RuntimeConfig:
    file_data = load_config_file(config_path or xdg_config_path())
    resolved = {
        "base_url": _pick_value(base_url, "CZM_BASE_URL", file_data, "base_url") or DEFAULT_BASE_URL,
        "api_key": _pick_value(api_key, "CZM_API_KEY", file_data, "api_key"),
        "timezone": _pick_value(timezone, "CZM_TIMEZONE", file_data, "timezone") or "UTC",
    }
    missing = [key for key, value in resolved.items() if key in {"api_key"} and not value]
    if missing:
        raise ConfigError(
            "missing required configuration: "
            + ", ".join(sorted(missing))
            + f"; run `czm setup` or set CLI flags, CZM_* env vars, or {config_path or xdg_config_path()}"
        )
    return RuntimeConfig(base_url=normalize_base_url(str(resolved["base_url"])), api_key=str(resolved["api_key"]), timezone=str(resolved["timezone"]))
