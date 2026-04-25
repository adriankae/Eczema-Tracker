from __future__ import annotations

from dataclasses import dataclass

from .client import CzmClient
from .config import RuntimeConfig


@dataclass(slots=True)
class CommandContext:
    config: RuntimeConfig
    client: CzmClient
    json_output: bool
    quiet: bool
    no_color: bool

