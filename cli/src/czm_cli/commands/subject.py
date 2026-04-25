from __future__ import annotations

import argparse

from ..formatting import format_subject, format_subject_list
from ..schemas import SubjectListResponse
from ._common import emit, resolve_subject_id


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("subject", parents=[parent], help="Manage subjects")
    subject_subparsers = parser.add_subparsers(dest="subject_command", required=True)

    create = subject_subparsers.add_parser("create", parents=[parent], help="Create a subject")
    create.add_argument("--display-name", required=True)
    create.set_defaults(handler=handle_create)

    listing = subject_subparsers.add_parser("list", parents=[parent], help="List subjects")
    listing.set_defaults(handler=handle_list)

    get = subject_subparsers.add_parser("get", parents=[parent], help="Get a subject")
    get.add_argument("subject")
    get.set_defaults(handler=handle_get)


def handle_create(ctx, args) -> int:
    payload = ctx.client.post("/subjects", json={"display_name": args.display_name})
    emit(ctx, payload, format_subject)
    return 0


def handle_list(ctx, args) -> int:
    payload = ctx.client.get("/subjects")
    emit(ctx, payload, lambda data: format_subject_list(SubjectListResponse.model_validate(data).subjects))
    return 0


def handle_get(ctx, args) -> int:
    subject_id = resolve_subject_id(ctx, args.subject)
    payload = ctx.client.get(f"/subjects/{subject_id}")
    emit(ctx, payload, format_subject)
    return 0

