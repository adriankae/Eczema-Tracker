from __future__ import annotations

import json
from typing import Any, Callable

from ..errors import CzmError, EXIT_AMBIGUOUS, EXIT_USAGE
from ..formatting import serialize_json_payload
from ..resolution import resolve_single
from ..schemas import LocationListResponse, SubjectListResponse


def emit(ctx, payload: Any, formatter: Callable[[Any], str]) -> None:
    if ctx.quiet and not ctx.json_output:
        return
    if ctx.json_output:
        print(json.dumps(serialize_json_payload(payload), ensure_ascii=False))
        return
    print(formatter(payload))


def resolve_subject_id(ctx, reference: str | int) -> int:
    subjects = SubjectListResponse.model_validate(ctx.client.get("/subjects")).subjects
    return resolve_single(reference, ((subject.id, (subject.display_name,)) for subject in subjects), label="subject")


def resolve_location_id(ctx, reference: str | int) -> int:
    locations = LocationListResponse.model_validate(ctx.client.get("/locations")).locations
    return resolve_single(
        reference,
        ((location.id, (location.code, location.display_name)) for location in locations),
        label="location",
    )


def require_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CzmError(f"{label} must be an integer", exit_code=EXIT_USAGE) from exc
