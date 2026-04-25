from __future__ import annotations

from czm_cli.time_utils import parse_local_datetime, utc_isoformat


def test_parse_local_datetime_converts_to_utc():
    dt = parse_local_datetime("2026-04-15T10:00:00", "Europe/Berlin")
    assert utc_isoformat(dt) == "2026-04-15T08:00:00Z"

