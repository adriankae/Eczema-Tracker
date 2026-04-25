#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL_DIR = ROOT / "skills" / "czm"


def _install_copy(target_dir: Path, destination: Path, overwrite: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if not overwrite:
            raise FileExistsError(f"{destination} already exists; pass --overwrite to replace it")
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    shutil.copytree(SOURCE_SKILL_DIR, destination)


def _install_symlink(target_dir: Path, destination: Path, overwrite: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if not overwrite:
            raise FileExistsError(f"{destination} already exists; pass --overwrite to replace it")
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    os.symlink(SOURCE_SKILL_DIR, destination, target_is_directory=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the czm Agent Skill into a runtime skill directory"
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        type=Path,
        help="Directory that contains installed skills, e.g. an OpenClaw skill folder",
    )
    parser.add_argument(
        "--mode",
        choices=("copy", "symlink"),
        default="copy",
        help="How to install the skill folder",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing czm skill installation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not SOURCE_SKILL_DIR.exists():
        print(f"source skill directory missing: {SOURCE_SKILL_DIR}", file=sys.stderr)
        return 2

    target_dir = args.target_dir.expanduser()
    destination = target_dir / "czm"
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.mode == "copy":
            _install_copy(target_dir, destination, args.overwrite)
        else:
            _install_symlink(target_dir, destination, args.overwrite)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Installed czm skill to {destination}")
    print("Next: configure your agent runtime to read that skill directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
