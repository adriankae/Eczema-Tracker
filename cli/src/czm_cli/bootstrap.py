from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from .config import DEFAULT_BASE_URL, RuntimeConfig, normalize_base_url, write_runtime_config
from .errors import CzmError, EXIT_CONFLICT, EXIT_USAGE


@dataclass(slots=True)
class BootstrapResult:
    config_path: Path
    base_url: str
    username: str
    api_key_name: str
    timezone: str


def detect_local_timezone() -> str:
    tzinfo = datetime.now().astimezone().tzinfo
    if tzinfo is None:
        return "UTC"
    key = getattr(tzinfo, "key", None) or getattr(tzinfo, "zone", None)
    return key or "UTC"


def _extract_token(payload: dict[str, object]) -> str:
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise CzmError("login response did not include an access token", exit_code=EXIT_USAGE)
    return token


def _extract_plaintext_key(payload: dict[str, object]) -> str:
    plaintext_key = payload.get("plaintext_key")
    if not isinstance(plaintext_key, str) or not plaintext_key:
        raise CzmError("API key response did not include a plaintext key", exit_code=EXIT_USAGE)
    return plaintext_key


def bootstrap_config(
    *,
    base_url: str,
    username: str,
    password: str,
    api_key_name: str,
    timezone: str,
    config_path: Path,
    overwrite: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> BootstrapResult:
    normalized_base_url = normalize_base_url(base_url)
    with httpx.Client(
        base_url=normalized_base_url,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        transport=transport,
    ) as client:
        login_response = client.post("/auth/login", json={"username": username, "password": password})
        if login_response.status_code >= 400:
            raise CzmError("backend login failed; check username/password and base_url", exit_code=EXIT_CONFLICT)
        token = _extract_token(login_response.json())

        api_key_response = client.post(
            "/api-keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": api_key_name},
        )
        if api_key_response.status_code >= 400:
            raise CzmError("API key creation failed; check backend access", exit_code=EXIT_CONFLICT)
        plaintext_key = _extract_plaintext_key(api_key_response.json())

    runtime_config = RuntimeConfig(base_url=normalized_base_url, api_key=plaintext_key, timezone=timezone)
    write_runtime_config(config_path, runtime_config, overwrite=overwrite)
    return BootstrapResult(
        config_path=config_path,
        base_url=normalized_base_url,
        username=username,
        api_key_name=api_key_name,
        timezone=timezone,
    )
