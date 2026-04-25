from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Start episode", callback_data="menu:start_episode"), InlineKeyboardButton("Log treatment", callback_data="menu:log_treatment")],
            [InlineKeyboardButton("Due today", callback_data="menu:due"), InlineKeyboardButton("Adherence", callback_data="menu:adherence")],
            [InlineKeyboardButton("Heal episode", callback_data="menu:heal"), InlineKeyboardButton("Relapse episode", callback_data="menu:relapse")],
            [InlineKeyboardButton("Locations", callback_data="menu:locations"), InlineKeyboardButton("Subjects", callback_data="menu:subjects")],
        ]
    )


def due_keyboard(due_items: list[dict], *, allow_writes: bool) -> InlineKeyboardMarkup | None:
    if not allow_writes:
        return None
    rows = [[InlineKeyboardButton(f"Log episode {item['episode_id']}", callback_data=f"due:log:{item['episode_id']}")] for item in due_items[:10]]
    return InlineKeyboardMarkup(rows) if rows else None


def subjects_keyboard(*, allow_writes: bool) -> InlineKeyboardMarkup | None:
    if not allow_writes:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton("Create subject", callback_data="subject:create")]])


def locations_keyboard(locations: list[dict], *, allow_writes: bool) -> InlineKeyboardMarkup | None:
    rows = [[InlineKeyboardButton(location["display_name"], callback_data=f"loc:select:{location['id']}")] for location in locations[:10]]
    if allow_writes:
        rows.append([InlineKeyboardButton("Create location", callback_data="loc:create")])
    return InlineKeyboardMarkup(rows) if rows else None


def location_actions_keyboard(location_id: int, *, allow_writes: bool) -> InlineKeyboardMarkup | None:
    if not allow_writes:
        return None
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Set image / Replace image", callback_data=f"loc:image:{location_id}")],
            [InlineKeyboardButton("Back to locations", callback_data="menu:locations")],
        ]
    )


def location_image_prompt_keyboard(location_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Set image", callback_data=f"loc:image:{location_id}")],
            [InlineKeyboardButton("Skip image", callback_data="menu:locations")],
        ]
    )


def start_subject_keyboard(subjects: list[dict], *, allow_writes: bool) -> InlineKeyboardMarkup | None:
    rows = [[InlineKeyboardButton(subject["display_name"], callback_data=f"epstart:subject:{subject['id']}")] for subject in subjects[:10]]
    if allow_writes:
        rows.append([InlineKeyboardButton("Create new subject", callback_data="epstart:subject_new")])
    return InlineKeyboardMarkup(rows) if rows else None


def start_location_keyboard(locations: list[dict], *, allow_writes: bool) -> InlineKeyboardMarkup | None:
    rows = [[InlineKeyboardButton(location["display_name"], callback_data=f"epstart:loc:{location['id']}")] for location in locations[:10]]
    if allow_writes:
        rows.append([InlineKeyboardButton("Create new location", callback_data="epstart:loc_new")])
    return InlineKeyboardMarkup(rows) if rows else None


def start_image_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Add/Replace location image", callback_data="epstart:image")],
            [InlineKeyboardButton("Skip image", callback_data="epstart:skip_image")],
        ]
    )


def start_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Create episode", callback_data="epstart:confirm")],
            [InlineKeyboardButton("Cancel", callback_data="epstart:cancel")],
        ]
    )


def episode_select_keyboard(prefix: str, episodes: list[dict]) -> InlineKeyboardMarkup | None:
    rows = [
        [
            InlineKeyboardButton(
                f"Episode {episode['id']} · {episode.get('status', 'unknown')}",
                callback_data=f"{prefix}:select:{episode['id']}",
            )
        ]
        for episode in episodes[:10]
    ]
    rows.append([InlineKeyboardButton("Cancel", callback_data=f"{prefix}:cancel")])
    return InlineKeyboardMarkup(rows)


def confirm_episode_action_keyboard(prefix: str, episode_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm", callback_data=f"{prefix}:confirm:{episode_id}")],
            [InlineKeyboardButton("Cancel", callback_data=f"{prefix}:cancel")],
        ]
    )


def adherence_keyboard(*, allow_rebuild: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("Summary 7 days", callback_data="adh:summary:7"),
            InlineKeyboardButton("Summary 30 days", callback_data="adh:summary:30"),
        ],
        [
            InlineKeyboardButton("Calendar 30 days", callback_data="adh:calendar:30"),
            InlineKeyboardButton("Missed 30 days", callback_data="adh:missed:30"),
        ],
    ]
    if allow_rebuild:
        rows.append([InlineKeyboardButton("Rebuild snapshots", callback_data="adh:rebuild")])
    return InlineKeyboardMarkup(rows)


def adherence_rebuild_range_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("7 days", callback_data="adh:rebuild:range:7"), InlineKeyboardButton("30 days", callback_data="adh:rebuild:range:30")],
            [InlineKeyboardButton("90 days", callback_data="adh:rebuild:range:90"), InlineKeyboardButton("Cancel", callback_data="adh:rebuild:cancel")],
        ]
    )


def adherence_rebuild_confirm_keyboard(days: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Confirm rebuild", callback_data=f"adh:rebuild:confirm:{days}")],
            [InlineKeyboardButton("Cancel", callback_data="adh:rebuild:cancel")],
        ]
    )
