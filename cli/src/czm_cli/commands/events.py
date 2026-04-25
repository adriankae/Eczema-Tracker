from __future__ import annotations

import argparse

from ..formatting import format_event_list
from ..schemas import EventListResponse, TimelineResponse
from ._common import emit, require_int


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("events", parents=[parent], help="Show event history")
    events_subparsers = parser.add_subparsers(dest="events_command", required=True)

    listing = events_subparsers.add_parser("list", parents=[parent], help="List episode events")
    listing.add_argument("--episode", required=True)
    listing.add_argument("--event-type")
    listing.set_defaults(handler=handle_list)

    timeline = events_subparsers.add_parser("timeline", parents=[parent], help="List episode timeline")
    timeline.add_argument("--episode", required=True)
    timeline.set_defaults(handler=handle_timeline)


def handle_list(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    params = {"event_type": args.event_type} if args.event_type else None
    payload = ctx.client.get(f"/episodes/{episode_id}/events", params=params)
    emit(ctx, payload, lambda data: format_event_list(EventListResponse.model_validate(data).events, ctx.config.timezone))
    return 0


def handle_timeline(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    payload = ctx.client.get(f"/episodes/{episode_id}/timeline")
    emit(ctx, payload, lambda data: format_event_list(TimelineResponse.model_validate(data).timeline, ctx.config.timezone))
    return 0
