from __future__ import annotations

import argparse
from datetime import timedelta

from ..errors import CzmError, EXIT_USAGE
from ..formatting import (
    format_adherence_calendar,
    format_adherence_missed,
    format_adherence_rebuild,
    format_adherence_summary,
    format_episode_adherence,
)
from ..time_utils import local_today, parse_local_date
from ._common import emit, require_int, resolve_location_id, resolve_subject_id


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser], parent: argparse.ArgumentParser) -> None:
    parser = subparsers.add_parser("adherence", parents=[parent], help="Show and rebuild adherence snapshots")
    adherence_subparsers = parser.add_subparsers(dest="adherence_command", required=True)

    calendar = adherence_subparsers.add_parser("calendar", parents=[parent], help="Show adherence calendar")
    _add_read_options(calendar, include_episode_filter=True, include_subject_location=True)
    calendar.set_defaults(handler=handle_calendar)

    summary = adherence_subparsers.add_parser("summary", parents=[parent], help="Show adherence summary")
    _add_read_options(summary, include_episode_filter=True, include_subject_location=True)
    summary.set_defaults(handler=handle_summary)

    missed = adherence_subparsers.add_parser("missed", parents=[parent], help="Show missed adherence days")
    _add_read_options(missed, include_episode_filter=True, include_subject_location=True)
    missed.add_argument("--include-partial", action="store_true")
    missed.set_defaults(handler=handle_missed)

    episode = adherence_subparsers.add_parser("episode", parents=[parent], help="Show adherence for one episode")
    episode.add_argument("episode")
    _add_read_options(episode, include_episode_filter=False, include_subject_location=False)
    episode.set_defaults(handler=handle_episode)

    rebuild = adherence_subparsers.add_parser("rebuild", parents=[parent], help="Persist adherence snapshots")
    rebuild.add_argument("--episode")
    rebuild.add_argument("--from", dest="from_date", required=True)
    rebuild.add_argument("--to", dest="to_date", required=True)
    rebuild.add_argument("--active-only", action="store_true", default=True)
    rebuild.add_argument("--source", choices=["rebuild", "backfill", "calculated", "system"], default="rebuild")
    rebuild.set_defaults(handler=handle_rebuild)


def _add_read_options(parser: argparse.ArgumentParser, *, include_episode_filter: bool, include_subject_location: bool) -> None:
    if include_episode_filter:
        parser.add_argument("--episode")
    if include_subject_location:
        parser.add_argument("--subject")
        parser.add_argument("--location")
    parser.add_argument("--from", dest="from_date")
    parser.add_argument("--to", dest="to_date")
    parser.add_argument("--last", type=int)
    parser.add_argument("--persisted", action="store_true")


def _date_range(ctx, args) -> tuple[str, str]:
    if args.last is not None:
        if args.last < 1:
            raise CzmError("--last must be greater than zero", exit_code=EXIT_USAGE)
        if args.from_date or args.to_date:
            raise CzmError("--last cannot be combined with --from or --to", exit_code=EXIT_USAGE)
        today = local_today(ctx.config.timezone)
        return ((today - timedelta(days=args.last - 1)).isoformat(), today.isoformat())

    if bool(args.from_date) != bool(args.to_date):
        raise CzmError("--from and --to must be provided together", exit_code=EXIT_USAGE)
    if not args.from_date or not args.to_date:
        raise CzmError("provide --last or both --from and --to", exit_code=EXIT_USAGE)
    try:
        from_date = parse_local_date(args.from_date)
        to_date = parse_local_date(args.to_date)
    except ValueError as exc:
        raise CzmError("dates must use YYYY-MM-DD", exit_code=EXIT_USAGE) from exc
    if from_date > to_date:
        raise CzmError("--from must be on or before --to", exit_code=EXIT_USAGE)
    return (from_date.isoformat(), to_date.isoformat())


def _read_params(ctx, args, *, include_episode_filter: bool) -> tuple[dict, str, str]:
    from_date, to_date = _date_range(ctx, args)
    params = {"from": from_date, "to": to_date}
    if include_episode_filter and getattr(args, "episode", None):
        params["episode_id"] = require_int(args.episode, "episode")
    if getattr(args, "subject", None):
        params["subject_id"] = resolve_subject_id(ctx, args.subject)
    if getattr(args, "location", None):
        params["location_id"] = resolve_location_id(ctx, args.location)
    if args.persisted:
        params["persisted"] = True
    return params, from_date, to_date


def handle_calendar(ctx, args) -> int:
    params, from_date, to_date = _read_params(ctx, args, include_episode_filter=True)
    payload = ctx.client.get("/adherence/calendar", params=params)
    emit(ctx, payload, lambda data: format_adherence_calendar(data, from_date, to_date))
    return 0


def handle_summary(ctx, args) -> int:
    params, _, _ = _read_params(ctx, args, include_episode_filter=True)
    payload = ctx.client.get("/adherence/summary", params=params)
    emit(ctx, payload, format_adherence_summary)
    return 0


def handle_missed(ctx, args) -> int:
    params, from_date, to_date = _read_params(ctx, args, include_episode_filter=True)
    if args.include_partial:
        params["include_partial"] = True
    payload = ctx.client.get("/adherence/missed", params=params)
    emit(ctx, payload, lambda data: format_adherence_missed(data, from_date, to_date))
    return 0


def handle_episode(ctx, args) -> int:
    episode_id = require_int(args.episode, "episode")
    params, _, _ = _read_params(ctx, args, include_episode_filter=False)
    payload = ctx.client.get(f"/episodes/{episode_id}/adherence", params=params)
    emit(ctx, payload, format_episode_adherence)
    return 0


def handle_rebuild(ctx, args) -> int:
    try:
        from_date = parse_local_date(args.from_date).isoformat()
        to_date = parse_local_date(args.to_date).isoformat()
    except ValueError as exc:
        raise CzmError("dates must use YYYY-MM-DD", exit_code=EXIT_USAGE) from exc
    if from_date > to_date:
        raise CzmError("--from must be on or before --to", exit_code=EXIT_USAGE)
    payload = {"from": from_date, "to": to_date, "active_only": True, "source": args.source}
    if args.episode:
        payload["episode_id"] = require_int(args.episode, "episode")
    response = ctx.client.post("/adherence/rebuild", json=payload)
    emit(ctx, response, format_adherence_rebuild)
    return 0
