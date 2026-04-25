from __future__ import annotations

import argparse

from ..formatting import format_application, format_application_list
from ..schemas import ApplicationListResponse
from ..time_utils import parse_local_datetime
from ._common import emit, require_int


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("application", parents=[parent], help="Manage treatment applications")
    application_subparsers = parser.add_subparsers(dest="application_command", required=True)

    log = application_subparsers.add_parser("log", parents=[parent], help="Log an application")
    log.add_argument("--episode", required=True)
    log.add_argument("--applied-at")
    log.add_argument("--treatment-type", required=True)
    log.add_argument("--treatment-name")
    log.add_argument("--quantity-text")
    log.add_argument("--notes")
    log.set_defaults(handler=handle_log)

    update = application_subparsers.add_parser("update", parents=[parent], help="Update an application")
    update.add_argument("application")
    update.add_argument("--applied-at")
    update.add_argument("--treatment-type")
    update.add_argument("--treatment-name")
    update.add_argument("--quantity-text")
    update.add_argument("--notes")
    update.set_defaults(handler=handle_update)

    delete = application_subparsers.add_parser("delete", parents=[parent], help="Delete an application")
    delete.add_argument("application")
    delete.set_defaults(handler=handle_delete)

    listing = application_subparsers.add_parser("list", parents=[parent], help="List applications for an episode")
    listing.add_argument("--episode", required=True)
    listing.add_argument("--include-voided", action="store_true")
    listing.set_defaults(handler=handle_list)


def handle_log(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    json_payload = {
        "episode_id": episode_id,
        "treatment_type": args.treatment_type,
    }
    if args.applied_at:
        json_payload["applied_at"] = parse_local_datetime(args.applied_at, ctx.config.timezone).isoformat().replace("+00:00", "Z")
    if args.treatment_name is not None:
        json_payload["treatment_name"] = args.treatment_name
    if args.quantity_text is not None:
        json_payload["quantity_text"] = args.quantity_text
    if args.notes is not None:
        json_payload["notes"] = args.notes
    payload = ctx.client.post("/applications", json=json_payload)
    emit(ctx, payload, lambda data: format_application(data["application"], ctx.config.timezone))
    return 0


def handle_update(ctx, args) -> int:
    application_id = require_int(args.application, "application")
    json_payload = {}
    if args.applied_at:
        json_payload["applied_at"] = parse_local_datetime(args.applied_at, ctx.config.timezone).isoformat().replace("+00:00", "Z")
    if args.treatment_type is not None:
        json_payload["treatment_type"] = args.treatment_type
    if args.treatment_name is not None:
        json_payload["treatment_name"] = args.treatment_name
    if args.quantity_text is not None:
        json_payload["quantity_text"] = args.quantity_text
    if args.notes is not None:
        json_payload["notes"] = args.notes
    payload = ctx.client.patch(f"/applications/{application_id}", json=json_payload)
    emit(ctx, payload, lambda data: format_application(data["application"], ctx.config.timezone))
    return 0


def handle_delete(ctx, args) -> int:
    application_id = require_int(args.application, "application")
    payload = ctx.client.delete(f"/applications/{application_id}")
    emit(ctx, payload, lambda data: format_application(data["application"], ctx.config.timezone))
    return 0


def handle_list(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    payload = ctx.client.get(f"/episodes/{episode_id}/applications", params={"include_voided": str(args.include_voided).lower()})
    emit(ctx, payload, lambda data: format_application_list(ApplicationListResponse.model_validate(data).applications, ctx.config.timezone))
    return 0
