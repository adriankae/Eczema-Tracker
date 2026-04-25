from __future__ import annotations

import argparse
import json

from ..config import apply_env_overrides, load_app_config, parse_bool, render_app_config, write_app_config, xdg_config_path
from ..errors import CzmError, EXIT_USAGE


ROOT_KEYS = {"base_url", "api_key", "timezone"}


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("config", parents=[parent], help="Inspect and edit local CLI config")
    config_subparsers = parser.add_subparsers(dest="config_command", required=True)

    path = config_subparsers.add_parser("path", parents=[parent], help="Show config file path")
    path.set_defaults(handler=handle_path)

    show = config_subparsers.add_parser("show", parents=[parent], help="Show config")
    show.add_argument("--show-secrets", action="store_true")
    show.set_defaults(handler=handle_show)

    validate = config_subparsers.add_parser("validate", parents=[parent], help="Validate config")
    validate.set_defaults(handler=handle_validate)

    set_cmd = config_subparsers.add_parser("set", parents=[parent], help="Set a root config value")
    set_cmd.add_argument("key", choices=sorted(ROOT_KEYS))
    set_cmd.add_argument("value")
    set_cmd.set_defaults(handler=handle_set)


def _path(args):
    return getattr(args, "config", None) or xdg_config_path()


def _emit(args, payload, text: str) -> None:
    if bool(getattr(args, "json", False)):
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(text)


def handle_path(ctx, args) -> int:
    path = _path(args)
    _emit(args, {"config_path": str(path)}, str(path))
    return 0


def handle_show(ctx, args) -> int:
    config = apply_env_overrides(load_app_config(_path(args)))
    output = render_app_config(config, show_secrets=args.show_secrets)
    if bool(getattr(args, "json", False)):
        print(json.dumps({"config": output}, ensure_ascii=False))
    else:
        print(output, end="")
    return 0


def handle_validate(ctx, args) -> int:
    apply_env_overrides(load_app_config(_path(args)))
    _emit(args, {"status": "ok"}, "Config OK")
    return 0


def handle_set(ctx, args) -> int:
    path = _path(args)
    config = load_app_config(path)
    if args.key == "base_url":
        config.base_url = args.value
    elif args.key == "api_key":
        config.api_key = args.value
    elif args.key == "timezone":
        config.timezone = args.value
    else:  # pragma: no cover - argparse choices protect this
        raise CzmError("unsupported config key", exit_code=EXIT_USAGE)
    write_app_config(path, config, overwrite=True)
    _emit(args, {"status": "ok", "key": args.key}, f"Updated {args.key}")
    return 0


def parse_cli_bool(value: str) -> bool:
    return parse_bool(value, label="value")
