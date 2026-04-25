from __future__ import annotations

import argparse

from ..formatting import format_due_list
from ..schemas import DueListResponse
from ._common import emit, resolve_subject_id


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("due", parents=[parent], help="Show due items")
    due_subparsers = parser.add_subparsers(dest="due_command", required=True)

    listing = due_subparsers.add_parser("list", parents=[parent], help="List due items")
    listing.add_argument("--subject")
    listing.set_defaults(handler=handle_list)


def handle_list(ctx, args) -> int:
    params = {}
    if args.subject:
        params["subject_id"] = resolve_subject_id(ctx, args.subject)
    payload = ctx.client.get("/episodes/due", params=params or None)
    emit(ctx, payload, lambda data: format_due_list(DueListResponse.model_validate(data).due, ctx.config.timezone))
    return 0
