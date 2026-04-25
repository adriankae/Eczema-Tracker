from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import local_date, utc_now
from app.models import Account, EpisodeDailyAdherence, EpisodePhaseHistory, TaperProtocolPhase, TreatmentApplication
from app.services import get_episode, list_episodes


ADHERENCE_STATUSES = {"completed", "partial", "missed", "not_due", "future"}
ADHERENCE_SOURCES = {"calculated", "backfill", "rebuild", "system"}


@dataclass(frozen=True)
class CalculatedAdherenceDay:
    account_id: int
    episode_id: int
    subject_id: int
    location_id: int
    date: date
    phase_number: int
    expected_applications: int
    completed_applications: int
    credited_applications: int
    status: str
    calculated_at: datetime


@dataclass(frozen=True)
class AdherenceSummary:
    expected_total: int
    completed_total: int
    credited_total: int
    adherence_score: float | None
    completed_day_count: int
    partial_day_count: int
    missed_day_count: int
    not_due_day_count: int
    future_day_count: int


def _validate_date_range(from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid date range")


def _validate_source(source: str) -> None:
    if source not in ADHERENCE_SOURCES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid adherence source")


def _iter_dates(from_date: date, to_date: date) -> Iterable[date]:
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


def _status_for(date_value: date, expected: int, completed: int, today: date) -> str:
    if date_value > today:
        return "future"
    if expected > 0 and completed >= expected:
        return "completed"
    if expected > 0 and 0 < completed < expected:
        return "partial"
    if expected > 0 and completed == 0:
        return "missed"
    return "not_due"


def _applications_by_local_date(db: Session, episode_id: int) -> dict[date, int]:
    applications = db.execute(
        select(TreatmentApplication).where(
            TreatmentApplication.episode_id == episode_id,
            TreatmentApplication.is_deleted.is_(False),
            TreatmentApplication.is_voided.is_(False),
        )
    ).scalars()
    counts: dict[date, int] = {}
    for application in applications:
        applied_date = local_date(application.applied_at)
        counts[applied_date] = counts.get(applied_date, 0) + 1
    return counts


def _protocol_phases_by_number(db: Session) -> dict[int, TaperProtocolPhase]:
    phases = db.execute(select(TaperProtocolPhase)).scalars()
    return {phase.phase_number: phase for phase in phases}


def calculate_episode_adherence(
    db: Session,
    account: Account,
    episode_id: int,
    from_date: date,
    to_date: date,
) -> list[CalculatedAdherenceDay]:
    _validate_date_range(from_date, to_date)
    episode = get_episode(db, account, episode_id)
    histories = list(
        db.execute(
            select(EpisodePhaseHistory)
            .where(EpisodePhaseHistory.episode_id == episode.id)
            .order_by(EpisodePhaseHistory.started_at.asc(), EpisodePhaseHistory.id.asc())
        ).scalars()
    )
    if not histories:
        return []

    protocol_phases = _protocol_phases_by_number(db)
    applications_by_date = _applications_by_local_date(db, episode.id)
    today = local_date(utc_now())
    calculated_at = utc_now()
    rows: list[CalculatedAdherenceDay] = []

    # Persisted adherence is audit-oriented and intentionally uses a fixed
    # protocol schedule anchored to each phase start date. This is separate from
    # the existing rolling /episodes/due reminder behavior.
    for history in histories:
        phase = protocol_phases.get(history.phase_number)
        if phase is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="protocol phase missing")

        phase_start_date = local_date(history.started_at)
        phase_end_date = local_date(history.ended_at) if history.ended_at is not None else to_date + timedelta(days=1)
        range_start = max(from_date, phase_start_date)
        range_end = min(to_date, phase_end_date - timedelta(days=1))
        if range_start > range_end:
            continue

        for date_value in _iter_dates(range_start, range_end):
            days_since_phase_start = (date_value - phase_start_date).days
            is_due = days_since_phase_start % phase.apply_every_n_days == 0
            expected = phase.applications_per_day if is_due else 0
            completed = applications_by_date.get(date_value, 0)
            credited = min(completed, expected)
            rows.append(
                CalculatedAdherenceDay(
                    account_id=episode.account_id,
                    episode_id=episode.id,
                    subject_id=episode.subject_id,
                    location_id=episode.location_id,
                    date=date_value,
                    phase_number=history.phase_number,
                    expected_applications=expected,
                    completed_applications=completed,
                    credited_applications=credited,
                    status=_status_for(date_value, expected, completed, today),
                    calculated_at=calculated_at,
                )
            )
    return rows


def calculate_filtered_adherence(
    db: Session,
    account: Account,
    from_date: date,
    to_date: date,
    *,
    episode_id: int | None = None,
    subject_id: int | None = None,
    location_id: int | None = None,
) -> list[CalculatedAdherenceDay]:
    _validate_date_range(from_date, to_date)
    if episode_id is not None:
        episode = get_episode(db, account, episode_id)
        if subject_id is not None and episode.subject_id != subject_id:
            return []
        if location_id is not None and episode.location_id != location_id:
            return []
        return calculate_episode_adherence(db, account, episode.id, from_date, to_date)

    rows: list[CalculatedAdherenceDay] = []
    for episode in list_episodes(db, account):
        if subject_id is not None and episode.subject_id != subject_id:
            continue
        if location_id is not None and episode.location_id != location_id:
            continue
        rows.extend(calculate_episode_adherence(db, account, episode.id, from_date, to_date))
    return sorted(rows, key=lambda row: (row.date, row.episode_id))


def list_persisted_adherence_rows(
    db: Session,
    account: Account,
    from_date: date,
    to_date: date,
    *,
    episode_id: int | None = None,
    subject_id: int | None = None,
    location_id: int | None = None,
) -> list[EpisodeDailyAdherence]:
    _validate_date_range(from_date, to_date)
    stmt = select(EpisodeDailyAdherence).where(
        EpisodeDailyAdherence.account_id == account.id,
        EpisodeDailyAdherence.date >= from_date,
        EpisodeDailyAdherence.date <= to_date,
    )
    if episode_id is not None:
        get_episode(db, account, episode_id)
        stmt = stmt.where(EpisodeDailyAdherence.episode_id == episode_id)
    if subject_id is not None:
        stmt = stmt.where(EpisodeDailyAdherence.subject_id == subject_id)
    if location_id is not None:
        stmt = stmt.where(EpisodeDailyAdherence.location_id == location_id)
    return list(db.execute(stmt.order_by(EpisodeDailyAdherence.date.asc(), EpisodeDailyAdherence.episode_id.asc())).scalars())


def list_adherence_rows(
    db: Session,
    account: Account,
    from_date: date,
    to_date: date,
    *,
    episode_id: int | None = None,
    subject_id: int | None = None,
    location_id: int | None = None,
    persisted: bool = False,
) -> list[CalculatedAdherenceDay | EpisodeDailyAdherence]:
    if persisted:
        return list_persisted_adherence_rows(
            db,
            account,
            from_date,
            to_date,
            episode_id=episode_id,
            subject_id=subject_id,
            location_id=location_id,
        )
    return calculate_filtered_adherence(
        db,
        account,
        from_date,
        to_date,
        episode_id=episode_id,
        subject_id=subject_id,
        location_id=location_id,
    )


def persist_episode_adherence(
    db: Session,
    account: Account,
    episode_id: int,
    from_date: date,
    to_date: date,
    source: str = "calculated",
) -> list[EpisodeDailyAdherence]:
    _validate_source(source)
    calculated_rows = calculate_episode_adherence(db, account, episode_id, from_date, to_date)
    today = local_date(utc_now())
    rows_to_persist = [row for row in calculated_rows if row.date <= today]
    if not rows_to_persist:
        return []

    existing_rows = list(
        db.execute(
            select(EpisodeDailyAdherence).where(
                EpisodeDailyAdherence.episode_id == episode_id,
                EpisodeDailyAdherence.date >= from_date,
                EpisodeDailyAdherence.date <= to_date,
            )
        ).scalars()
    )
    existing_by_date = {row.date: row for row in existing_rows}
    now = utc_now()
    persisted: list[EpisodeDailyAdherence] = []

    for calculated in rows_to_persist:
        adherence = existing_by_date.get(calculated.date)
        if adherence is None:
            adherence = EpisodeDailyAdherence(
                account_id=calculated.account_id,
                episode_id=calculated.episode_id,
                subject_id=calculated.subject_id,
                location_id=calculated.location_id,
                date=calculated.date,
                phase_number=calculated.phase_number,
                expected_applications=calculated.expected_applications,
                completed_applications=calculated.completed_applications,
                credited_applications=calculated.credited_applications,
                status=calculated.status,
                source=source,
                calculated_at=calculated.calculated_at,
                finalized_at=None,
            )
        else:
            adherence.account_id = calculated.account_id
            adherence.subject_id = calculated.subject_id
            adherence.location_id = calculated.location_id
            adherence.phase_number = calculated.phase_number
            adherence.expected_applications = calculated.expected_applications
            adherence.completed_applications = calculated.completed_applications
            adherence.credited_applications = calculated.credited_applications
            adherence.status = calculated.status
            adherence.source = source
            adherence.calculated_at = calculated.calculated_at
            adherence.updated_at = now
        db.add(adherence)
        persisted.append(adherence)

    db.commit()
    for adherence in persisted:
        db.refresh(adherence)
    return sorted(persisted, key=lambda row: row.date)


def rebuild_episode_adherence(
    db: Session,
    account: Account,
    episode_id: int,
    from_date: date,
    to_date: date,
    source: str = "rebuild",
) -> list[EpisodeDailyAdherence]:
    return persist_episode_adherence(db, account, episode_id, from_date, to_date, source=source)


def rebuild_active_episode_adherence(
    db: Session,
    account: Account,
    from_date: date,
    to_date: date,
    source: str = "rebuild",
) -> list[EpisodeDailyAdherence]:
    _validate_date_range(from_date, to_date)
    persisted: list[EpisodeDailyAdherence] = []
    for episode in list_episodes(db, account):
        if episode.status == "obsolete":
            continue
        persisted.extend(rebuild_episode_adherence(db, account, episode.id, from_date, to_date, source=source))
    return sorted(persisted, key=lambda row: (row.episode_id, row.date))


def summarize_adherence(rows: Iterable[CalculatedAdherenceDay | EpisodeDailyAdherence]) -> AdherenceSummary:
    expected_total = 0
    completed_total = 0
    credited_total = 0
    day_counts = {status_name: 0 for status_name in ADHERENCE_STATUSES}

    for row in rows:
        expected_total += row.expected_applications
        completed_total += row.completed_applications
        credited_total += row.credited_applications
        day_counts[row.status] = day_counts.get(row.status, 0) + 1

    adherence_score = None if expected_total == 0 else credited_total / expected_total
    return AdherenceSummary(
        expected_total=expected_total,
        completed_total=completed_total,
        credited_total=credited_total,
        adherence_score=adherence_score,
        completed_day_count=day_counts["completed"],
        partial_day_count=day_counts["partial"],
        missed_day_count=day_counts["missed"],
        not_due_day_count=day_counts["not_due"],
        future_day_count=day_counts["future"],
    )
