from __future__ import annotations

import argparse

from ..formatting import format_location, format_location_list
from ..schemas import LocationListResponse
from ._common import emit


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("location", parents=[parent], help="Manage locations")
    location_subparsers = parser.add_subparsers(dest="location_command", required=True)

    create = location_subparsers.add_parser("create", parents=[parent], help="Create a location")
    create.add_argument("--code", required=True)
    create.add_argument("--display-name", required=True)
    create.set_defaults(handler=handle_create)

    listing = location_subparsers.add_parser("list", parents=[parent], help="List locations")
    listing.set_defaults(handler=handle_list)


def handle_create(ctx, args) -> int:
    payload = ctx.client.post("/locations", json={"code": args.code, "display_name": args.display_name})
    emit(ctx, payload, lambda data: format_location(data["location"]))
    return 0


def handle_list(ctx, args) -> int:
    payload = ctx.client.get("/locations")
    emit(ctx, payload, lambda data: format_location_list(LocationListResponse.model_validate(data).locations))
    return 0

