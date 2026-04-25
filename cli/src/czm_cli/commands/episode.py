from __future__ import annotations

import argparse

from ..formatting import format_episode, format_episode_list
from ..schemas import EpisodeListResponse
from ..time_utils import parse_local_datetime
from ._common import emit, resolve_location_id, resolve_subject_id, require_int


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("episode", parents=[parent], help="Manage episodes")
    episode_subparsers = parser.add_subparsers(dest="episode_command", required=True)

    create = episode_subparsers.add_parser("create", parents=[parent], help="Create an episode")
    create.add_argument("--subject", required=True)
    create.add_argument("--location", required=True)
    create.add_argument("--protocol-version", default="v1")
    create.set_defaults(handler=handle_create)

    listing = episode_subparsers.add_parser("list", parents=[parent], help="List episodes")
    listing.add_argument("--subject")
    listing.add_argument("--status")
    listing.set_defaults(handler=handle_list)

    get = episode_subparsers.add_parser("get", parents=[parent], help="Get an episode")
    get.add_argument("episode")
    get.set_defaults(handler=handle_get)

    heal = episode_subparsers.add_parser("heal", parents=[parent], help="Mark an episode healed")
    heal.add_argument("episode")
    heal.add_argument("--healed-at")
    heal.set_defaults(handler=handle_heal)

    relapse = episode_subparsers.add_parser("relapse", parents=[parent], help="Mark an episode relapsed")
    relapse.add_argument("episode")
    relapse.add_argument("--reported-at")
    relapse.add_argument(
        "--reason",
        help='Optional human-readable relapse reason; defaults to the repo-defined transition reason "relapse"',
    )
    relapse.set_defaults(handler=handle_relapse)


def handle_create(ctx, args) -> int:
    subject_id = resolve_subject_id(ctx, args.subject)
    location_id = resolve_location_id(ctx, args.location)
    payload = ctx.client.post(
        "/episodes",
        json={"subject_id": subject_id, "location_id": location_id, "protocol_version": args.protocol_version},
    )
    emit(ctx, payload, lambda data: format_episode(data["episode"], ctx.config.timezone))
    return 0


def handle_list(ctx, args) -> int:
    params = {}
    if args.subject:
        params["subject_id"] = resolve_subject_id(ctx, args.subject)
    if args.status:
        params["status"] = args.status
    payload = ctx.client.get("/episodes", params=params or None)
    emit(ctx, payload, lambda data: format_episode_list(EpisodeListResponse.model_validate(data).episodes))
    return 0


def handle_get(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    payload = ctx.client.get(f"/episodes/{episode_id}")
    emit(ctx, payload, lambda data: format_episode(data["episode"], ctx.config.timezone))
    return 0


def handle_heal(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    json_payload = {}
    if args.healed_at:
        json_payload["healed_at"] = parse_local_datetime(args.healed_at, ctx.config.timezone).isoformat().replace("+00:00", "Z")
    payload = ctx.client.post(f"/episodes/{episode_id}/heal", json=json_payload or None)
    emit(ctx, payload, lambda data: format_episode(data["episode"], ctx.config.timezone))
    return 0


def handle_relapse(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    json_payload = {"reason": args.reason or "relapse"}
    if args.reported_at:
        json_payload["reported_at"] = parse_local_datetime(args.reported_at, ctx.config.timezone).isoformat().replace("+00:00", "Z")
    payload = ctx.client.post(f"/episodes/{episode_id}/relapse", json=json_payload)
    emit(ctx, payload, lambda data: format_episode(data["episode"], ctx.config.timezone))
    return 0
