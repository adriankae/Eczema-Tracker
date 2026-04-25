from __future__ import annotations

from dataclasses import dataclass


EXIT_SUCCESS = 0
EXIT_USAGE = 2
EXIT_NOT_FOUND = 3
EXIT_AMBIGUOUS = 4
EXIT_AUTH = 5
EXIT_CONFLICT = 6
EXIT_TRANSPORT = 7
EXIT_INTERNAL = 70


@dataclass(slots=True)
class CzmError(Exception):
    message: str
    exit_code: int = EXIT_INTERNAL

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.message


class ConfigError(CzmError):
    def __init__(self, message: str):
        super().__init__(message=message, exit_code=EXIT_USAGE)


class ResolutionError(CzmError):
    def __init__(self, message: str, *, exit_code: int = EXIT_AMBIGUOUS):
        super().__init__(message=message, exit_code=exit_code)


class ApiError(CzmError):
    def __init__(self, message: str, *, exit_code: int = EXIT_TRANSPORT, status_code: int | None = None, code: str | None = None):
        self.status_code = status_code
        self.code = code
        super().__init__(message=message, exit_code=exit_code)


class TransportError(ApiError):
    def __init__(self, message: str):
        super().__init__(message, exit_code=EXIT_TRANSPORT)

