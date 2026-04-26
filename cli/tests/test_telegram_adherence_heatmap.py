from __future__ import annotations

from datetime import date

from czm_cli.telegram.heatmap import STATUS_COLORS, build_heatmap_grid, render_heatmap_png, should_annotate


def _day(day: str, *, episode_id=1, location_id=10, subject_id=100, status="completed", credited=1, expected=1):
    return {
        "date": day,
        "episode_id": episode_id,
        "location_id": location_id,
        "subject_id": subject_id,
        "phase_number": 1,
        "expected_applications": expected,
        "completed_applications": credited,
        "credited_applications": credited,
        "status": status,
    }


def test_build_heatmap_grid_dates_and_location_first_labels():
    grid = build_heatmap_grid(
        {"days": [_day("2026-04-01"), _day("2026-04-02", status="partial", credited=1, expected=2)]},
        {"subjects": [{"id": 100, "display_name": "Child A"}]},
        {"locations": [{"id": 10, "display_name": "Left elbow"}]},
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 3),
    )
    assert [item.isoformat() for item in grid.dates] == ["2026-04-01", "2026-04-02", "2026-04-03"]
    assert grid.rows[0].label == "Left elbow"
    assert grid.rows[0].statuses == ["completed", "partial", "not_due"]
    assert grid.rows[0].annotations == ["1/1", "1/2", ""]


def test_duplicate_location_labels_are_disambiguated():
    grid = build_heatmap_grid(
        {
            "days": [
                _day("2026-04-01", episode_id=1, location_id=10, subject_id=100),
                _day("2026-04-01", episode_id=2, location_id=10, subject_id=101),
                _day("2026-04-01", episode_id=3, location_id=10, subject_id=101),
            ]
        },
        {"subjects": [{"id": 100, "display_name": "Child A"}, {"id": 101, "display_name": "Child B"}]},
        {"locations": [{"id": 10, "display_name": "Left elbow"}]},
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 1),
    )
    labels = [row.label for row in grid.rows]
    assert "Left elbow - Child A" in labels
    assert "Left elbow - Child B - #2" in labels
    assert "Left elbow - Child B - #3" in labels


def test_status_colors_are_stable():
    assert set(STATUS_COLORS) == {"completed", "partial", "missed", "not_due", "future"}
    assert STATUS_COLORS["completed"] != STATUS_COLORS["missed"]


def test_render_heatmap_png_and_empty_state():
    grid = build_heatmap_grid(
        {"days": [_day("2026-04-01", status="missed", credited=0, expected=1)]},
        {"subjects": [{"id": 100, "display_name": "Child A"}]},
        {"locations": [{"id": 10, "display_name": "Left elbow"}]},
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 1),
    )
    assert render_heatmap_png(grid).startswith(b"\x89PNG")

    empty = build_heatmap_grid({"days": []}, {"subjects": []}, {"locations": []}, from_date=date(2026, 4, 1), to_date=date(2026, 4, 7))
    assert render_heatmap_png(empty).startswith(b"\x89PNG")


def test_annotations_are_suppressed_for_90_day_views_and_rows_are_capped():
    days = [_day("2026-04-01", episode_id=index, location_id=index, subject_id=1) for index in range(1, 48)]
    locations = [{"id": index, "display_name": f"Location {index:02d}"} for index in range(1, 48)]
    grid = build_heatmap_grid(
        {"days": days},
        {"subjects": [{"id": 1, "display_name": "Child A"}]},
        {"locations": locations},
        from_date=date(2026, 4, 1),
        to_date=date(2026, 6, 29),
    )
    assert len(grid.dates) == 90
    assert len(grid.rows) == 30
    assert grid.omitted_rows == 17
    assert should_annotate(grid) is False
