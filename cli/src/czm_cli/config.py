from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import os
import tomllib

from .errors import ConfigError, CzmError, EXIT_CONFLICT

DEFAULT_BASE_URL = "http://localhost:28173"


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
