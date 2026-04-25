from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .errors import EXIT_AUTH, EXIT_CONFLICT, EXIT_NOT_FOUND, EXIT_TRANSPORT, EXIT_USAGE, ApiError, TransportError
from .schemas import ApiErrorResponse


class CzmClient:
    def __init__(self, base_url: str, api_key: str, *, transport: httpx.BaseTransport | None = None, timeout: float = 30.0):
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            },
        )

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        try:
            response = self._client.request(method, path, json=json, params=params)
        except httpx.HTTPError as exc:
            raise TransportError(f"request failed: {exc}") from exc
        if response.status_code >= 400:
            raise self._map_http_error(response)
        if response.content:
            return response.json()
        return None

    def _map_http_error(self, response: httpx.Response) -> ApiError:
        message = f"request failed with status {response.status_code}"
        code = None
        try:
            parsed = ApiErrorResponse.model_validate(response.json())
        except Exception:
            parsed = None
        if parsed is not None:
            message = parsed.error.message
            code = parsed.error.code
        status = response.status_code
        if status in {401, 403}:
            exit_code = EXIT_AUTH
        elif status == 404:
            exit_code = EXIT_NOT_FOUND
        elif status == 409:
            exit_code = EXIT_CONFLICT
        elif status == 422:
            exit_code = EXIT_USAGE
        else:
            exit_code = EXIT_TRANSPORT
        return ApiError(message, exit_code=exit_code, status_code=status, code=code)

    def get(self, path: str, *, params: Mapping[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        return self.request("POST", path, json=json, params=params)

    def patch(self, path: str, *, json: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        return self.request("PATCH", path, json=json, params=params)

    def delete(self, path: str, *, json: Mapping[str, Any] | None = None, params: Mapping[str, Any] | None = None) -> Any:
        return self.request("DELETE", path, json=json, params=params)

