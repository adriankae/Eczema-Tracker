from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO
from typing import Any


STATUS_ORDER = ["completed", "partial", "missed", "not_due", "future"]
STATUS_COLORS = {
    "completed": "#2f9e44",
    "partial": "#f59f00",
    "missed": "#e03131",
    "not_due": "#dee2e6",
    "future": "#d0ebff",
}
MAX_HEATMAP_ROWS = 30


@dataclass(slots=True)
class HeatmapRow:
    key: tuple[int, int, int]
    label: str
    statuses: list[str]
    annotations: list[str]


@dataclass(slots=True)
class HeatmapGrid:
    title: str
    dates: list[date]
    rows: list[HeatmapRow]
    omitted_rows: int = 0


def date_range(from_date: date, to_date: date) -> list[date]:
    if to_date < from_date:
        return []
    return [from_date + timedelta(days=offset) for offset in range((to_date - from_date).days + 1)]


def build_heatmap_grid(
    calendar_payload: dict[str, Any],
    subjects_payload: dict[str, Any],
    locations_payload: dict[str, Any],
    *,
    from_date: date,
    to_date: date,
    max_rows: int = MAX_HEATMAP_ROWS,
) -> HeatmapGrid:
    dates = date_range(from_date, to_date)
    subject_names = {item.get("id"): item.get("display_name") for item in subjects_payload.get("subjects", [])}
    location_names = {item.get("id"): item.get("display_name") for item in locations_payload.get("locations", [])}
    grouped: dict[tuple[int, int, int], dict[date, dict[str, Any]]] = {}
    for item in calendar_payload.get("days", []):
        try:
            row_date = date.fromisoformat(str(item["date"]))
            key = (int(item["episode_id"]), int(item["location_id"]), int(item["subject_id"]))
        except (KeyError, TypeError, ValueError):
            continue
        if from_date <= row_date <= to_date:
            grouped.setdefault(key, {})[row_date] = item

    labels = _row_labels(list(grouped), subject_names, location_names)
    rows = []
    for key, label in labels.items():
        statuses = []
        annotations = []
        for day in dates:
            item = grouped[key].get(day)
            status = str(item.get("status", "not_due")) if item else "not_due"
            statuses.append(status if status in STATUS_COLORS else "not_due")
            expected = int(item.get("expected_applications", 0)) if item else 0
            credited = int(item.get("credited_applications", 0)) if item else 0
            annotations.append(f"{credited}/{expected}" if expected > 0 else "")
        rows.append(HeatmapRow(key=key, label=label, statuses=statuses, annotations=annotations))
    rows.sort(key=lambda row: row.label.casefold())
    return HeatmapGrid(
        title=f"Adherence Heatmap - {from_date.isoformat()} to {to_date.isoformat()}",
        dates=dates,
        rows=rows[:max_rows],
        omitted_rows=max(0, len(rows) - max_rows),
    )


def should_annotate(grid: HeatmapGrid) -> bool:
    return len(grid.dates) <= 30


def render_heatmap_png(grid: HeatmapGrid, *, annotate: bool | None = None) -> bytes:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch

    if annotate is None:
        annotate = should_annotate(grid)
    if not grid.rows or not grid.dates:
        return _render_empty_png(grid.title)

    status_index = {status: index for index, status in enumerate(STATUS_ORDER)}
    matrix = [[status_index.get(status, status_index["not_due"]) for status in row.statuses] for row in grid.rows]

    width = min(14.0, max(6.0, 2.8 + len(grid.dates) * 0.26))
    height = min(18.0, max(3.2, 2.4 + len(grid.rows) * 0.42))
    fig, ax = plt.subplots(figsize=(width, height), dpi=160)
    cmap = ListedColormap([STATUS_COLORS[status] for status in STATUS_ORDER])
    norm = BoundaryNorm(range(len(STATUS_ORDER) + 1), cmap.N)
    ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")

    ax.set_title(_title_with_omission(grid), fontsize=12, pad=12)
    ax.set_yticks(range(len(grid.rows)))
    ax.set_yticklabels([row.label for row in grid.rows], fontsize=8)
    tick_step = max(1, len(grid.dates) // 12)
    tick_positions = list(range(0, len(grid.dates), tick_step))
    if tick_positions[-1] != len(grid.dates) - 1:
        tick_positions.append(len(grid.dates) - 1)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels([grid.dates[index].strftime("%m-%d") for index in tick_positions], rotation=45, ha="right", fontsize=8)

    ax.set_xticks([position - 0.5 for position in range(1, len(grid.dates))], minor=True)
    ax.set_yticks([position - 0.5 for position in range(1, len(grid.rows))], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.7)
    ax.tick_params(which="minor", bottom=False, left=False)
    if annotate:
        for row_index, row in enumerate(grid.rows):
            for col_index, text in enumerate(row.annotations):
                if text:
                    ax.text(col_index, row_index, text, ha="center", va="center", fontsize=6, color="#212529")

    legend = [Patch(facecolor=STATUS_COLORS[status], label=status.replace("_", " ")) for status in STATUS_ORDER]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=min(5, len(legend)), fontsize=8, frameon=False)
    fig.tight_layout()
    output = BytesIO()
    fig.savefig(output, format="png", bbox_inches="tight")
    plt.close(fig)
    return output.getvalue()


def _row_labels(keys: list[tuple[int, int, int]], subject_names: dict[int, str], location_names: dict[int, str]) -> dict[tuple[int, int, int], str]:
    base = {key: location_names.get(key[1]) or f"Location {key[1]}" for key in keys}
    base_counts = {label: list(base.values()).count(label) for label in set(base.values())}
    with_subject = {}
    for key, label in base.items():
        subject_name = subject_names.get(key[2]) or f"Subject {key[2]}"
        with_subject[key] = f"{label} - {subject_name}" if base_counts[label] > 1 else label
    subject_counts = {label: list(with_subject.values()).count(label) for label in set(with_subject.values())}
    return {key: (f"{label} - #{key[0]}" if subject_counts[label] > 1 else label) for key, label in with_subject.items()}


def _title_with_omission(grid: HeatmapGrid) -> str:
    if grid.omitted_rows:
        return f"{grid.title}\nShowing {len(grid.rows)} of {len(grid.rows) + grid.omitted_rows} rows"
    return grid.title


def _render_empty_png(title: str) -> bytes:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3), dpi=160)
    ax.axis("off")
    ax.set_title(title, fontsize=12, pad=12)
    ax.text(0.5, 0.5, "No adherence data for this range.", ha="center", va="center", fontsize=11)
    output = BytesIO()
    fig.savefig(output, format="png", bbox_inches="tight")
    plt.close(fig)
    return output.getvalue()
