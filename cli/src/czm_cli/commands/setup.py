from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..bootstrap import DEFAULT_BASE_URL, BootstrapResult, bootstrap_config, detect_local_timezone
from ..config import xdg_config_path


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("setup", parents=[parent], help="Create config.toml from backend login")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument("--api-key-name", default="czm-cli")
    parser.add_argument("--overwrite", action="store_true")
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
