from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, generate_api_key, hash_api_key, hash_password, verify_password
from app.core.time import add_calendar_days, local_date, local_midnight, utc_now
from app.models import (
    Account,
    AccountApiKey,
    BodyLocation,
    EczemaEpisode,
    EpisodeEvent,
    EpisodePhaseHistory,
    Subject,
    TaperProtocolPhase,
    TreatmentApplication,
)


VALID_EPISODE_STATUSES = {"active_flare", "in_taper", "obsolete"}
VALID_TREATMENT_TYPES = {"steroid", "emollient", "other"}
VALID_EVENT_TYPES = {
    "episode_created",
    "healed_marked",
    "phase_entered",
    "relapse_marked",
    "application_logged",
    "application_updated",
    "application_deleted",
    "application_voided",
    "episode_obsoleted",
}


def bootstrap_data(db: Session) -> None:
    if db.execute(select(Account.id)).first() is None:
        db.add(Account(username=settings.initial_username, password_hash=hash_password(settings.initial_password), is_active=True))
        db.commit()
    if db.execute(select(TaperProtocolPhase.phase_number)).first() is None:
        db.add_all(
            [
                TaperProtocolPhase(phase_number=1, duration_days=None, apply_every_n_days=1, applications_per_day=2),
                TaperProtocolPhase(phase_number=2, duration_days=28, apply_every_n_days=2, applications_per_day=1),
                TaperProtocolPhase(phase_number=3, duration_days=14, apply_every_n_days=3, applications_per_day=1),
                TaperProtocolPhase(phase_number=4, duration_days=14, apply_every_n_days=4, applications_per_day=1),
                TaperProtocolPhase(phase_number=5, duration_days=14, apply_every_n_days=5, applications_per_day=1),
                TaperProtocolPhase(phase_number=6, duration_days=14, apply_every_n_days=6, applications_per_day=1),
                TaperProtocolPhase(phase_number=7, duration_days=14, apply_every_n_days=7, applications_per_day=1),
            ]
        )
        db.commit()


def authenticate_user(db: Session, username: str, password: str) -> Account:
    account = db.execute(select(Account).where(Account.username == username)).scalar_one_or_none()
    if account is None or not account.is_active or not verify_password(password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return account


def issue_login_token(account: Account) -> str:
    return create_access_token(subject=str(account.id), account_id=account.id)


def create_api_key(db: Session, account: Account, name: str) -> tuple[AccountApiKey, str]:
    plaintext = generate_api_key()
    key = AccountApiKey(account_id=account.id, name=name, key_hash=hash_api_key(plaintext), is_active=True)
    db.add(key)
    db.commit()
    db.refresh(key)
    return key, plaintext


def list_api_keys(db: Session, account: Account) -> list[AccountApiKey]:
    return list(
        db.execute(select(AccountApiKey).where(AccountApiKey.account_id == account.id).order_by(AccountApiKey.id.asc())).scalars()
    )


def revoke_api_key(db: Session, account: Account, api_key_id: int) -> AccountApiKey:
    api_key = db.get(AccountApiKey, api_key_id)
    if api_key is None or api_key.account_id != account.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api key not found")
    api_key.is_active = False
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def create_subject(db: Session, account: Account, display_name: str) -> Subject:
    subject = Subject(account_id=account.id, display_name=display_name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def list_subjects(db: Session, account: Account) -> list[Subject]:
    return list(db.execute(select(Subject).where(Subject.account_id == account.id).order_by(Subject.id.asc())).scalars())


def get_subject(db: Session, account: Account, subject_id: int) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None or subject.account_id != account.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subject not found")
    return subject


def create_location(db: Session, account: Account, code: str, display_name: str) -> BodyLocation:
    location = BodyLocation(account_id=account.id, code=code, display_name=display_name)
    db.add(location)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="location code already exists") from exc
    db.refresh(location)
    return location


def list_locations(db: Session, account: Account) -> list[BodyLocation]:
    return list(
        db.execute(select(BodyLocation).where(BodyLocation.account_id == account.id).order_by(BodyLocation.id.asc())).scalars()
    )


def get_location(db: Session, account: Account, location_id: int) -> BodyLocation:
    location = db.get(BodyLocation, location_id)
    if location is None or location.account_id != account.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="location not found")
    return location


def get_protocol_phase(db: Session, phase_number: int) -> TaperProtocolPhase:
    phase = db.get(TaperProtocolPhase, phase_number)
    if phase is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="protocol phase missing")
    return phase


def calculate_phase_due_end_at(phase_started_at: datetime, phase_number: int) -> datetime | None:
    phase = {
        1: None,
        2: 28,
        3: 14,
        4: 14,
        5: 14,
        6: 14,
        7: 14,
    }.get(phase_number)
    if phase is None:
        return None
    return add_calendar_days(phase_started_at, phase)


def create_phase_history(db: Session, episode: EczemaEpisode, phase_number: int, started_at: datetime, reason: str) -> EpisodePhaseHistory:
    phase_history = EpisodePhaseHistory(
        episode_id=episode.id,
        phase_number=phase_number,
        started_at=started_at,
        ended_at=None,
        reason=reason,
    )
    db.add(phase_history)
    return phase_history


def close_current_phase_history(db: Session, episode: EczemaEpisode, ended_at: datetime) -> None:
    current_history = (
        db.execute(
            select(EpisodePhaseHistory)
            .where(EpisodePhaseHistory.episode_id == episode.id, EpisodePhaseHistory.ended_at.is_(None))
            .order_by(EpisodePhaseHistory.id.desc())
        )
        .scalars()
        .first()
    )
    if current_history is not None:
        current_history.ended_at = ended_at
        db.add(current_history)


def create_event(
    db: Session,
    *,
    episode_id: int,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    occurred_at: datetime,
    payload: dict,
) -> EpisodeEvent:
    if event_type not in VALID_EVENT_TYPES:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid event type")
    if actor_type not in {"user", "agent", "system"}:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid actor type")
    event = EpisodeEvent(
        event_uuid=str(uuid.uuid4()),
        episode_id=episode_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
        payload=payload,
    )
    db.add(event)
    return event


def create_episode(db: Session, account: Account, subject_id: int, location_id: int, protocol_version: str, now: datetime, actor_type: str, actor_id: str) -> EczemaEpisode:
    if protocol_version != "v1":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid protocol version")
    subject = get_subject(db, account, subject_id)
    location = get_location(db, account, location_id)
    existing = (
        db.execute(
            select(EczemaEpisode).where(
                EczemaEpisode.account_id == account.id,
                EczemaEpisode.subject_id == subject.id,
                EczemaEpisode.location_id == location.id,
                EczemaEpisode.status != "obsolete",
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode already exists for subject location")
    episode = EczemaEpisode(
        account_id=account.id,
        subject_id=subject.id,
        location_id=location.id,
        status="active_flare",
        current_phase_number=1,
        phase_started_at=now,
        phase_due_end_at=None,
        protocol_version=protocol_version,
        healed_at=None,
        obsolete_at=None,
    )
    db.add(episode)
    db.flush()
    create_phase_history(db, episode, 1, now, "episode_created")
    create_event(
        db,
        episode_id=episode.id,
        event_type="episode_created",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=now,
        payload={
            "location_id": location.id,
            "location_code": location.code,
            "initial_phase_number": 1,
            "protocol_version": protocol_version,
        },
    )
    db.commit()
    db.refresh(episode)
    return episode


def get_episode(db: Session, account: Account, episode_id: int) -> EczemaEpisode:
    episode = db.get(EczemaEpisode, episode_id)
    if episode is None or episode.account_id != account.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="episode not found")
    return episode


def list_episodes(db: Session, account: Account, subject_id: int | None = None, status_name: str | None = None) -> list[EczemaEpisode]:
    stmt = select(EczemaEpisode).where(EczemaEpisode.account_id == account.id)
    if subject_id is not None:
        stmt = stmt.where(EczemaEpisode.subject_id == subject_id)
    if status_name is not None:
        stmt = stmt.where(EczemaEpisode.status == status_name)
    return list(db.execute(stmt.order_by(EczemaEpisode.id.asc())).scalars())


def heal_episode(db: Session, account: Account, episode_id: int, healed_at: datetime, actor_type: str, actor_id: str) -> EczemaEpisode:
    episode = get_episode(db, account, episode_id)
    if episode.status == "obsolete":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode is obsolete")
    if episode.current_phase_number != 1 or episode.status != "active_flare":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode not in phase 1")
    close_current_phase_history(db, episode, healed_at)
    episode.status = "in_taper"
    episode.current_phase_number = 2
    episode.healed_at = healed_at
    episode.phase_started_at = healed_at
    episode.phase_due_end_at = calculate_phase_due_end_at(healed_at, 2)
    episode.updated_at = healed_at
    create_phase_history(db, episode, 2, healed_at, "healed_marked")
    create_event(
        db,
        episode_id=episode.id,
        event_type="healed_marked",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=healed_at,
        payload={"from_phase_number": 1, "to_phase_number": 2, "healed_at": healed_at.isoformat()},
    )
    create_event(
        db,
        episode_id=episode.id,
        event_type="phase_entered",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=healed_at,
        payload={
            "from_phase_number": 1,
            "to_phase_number": 2,
            "started_at": healed_at.isoformat(),
            "due_end_at": episode.phase_due_end_at.isoformat() if episode.phase_due_end_at else None,
            "reason": "healed_marked",
        },
    )
    db.commit()
    db.refresh(episode)
    return episode


def relapse_episode(db: Session, account: Account, episode_id: int, reported_at: datetime, reason: str, actor_type: str, actor_id: str) -> EczemaEpisode:
    episode = get_episode(db, account, episode_id)
    if episode.status == "obsolete":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode is obsolete")
    if episode.current_phase_number == 1 or episode.status != "in_taper":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="invalid relapse state")
    previous_phase = episode.current_phase_number
    close_current_phase_history(db, episode, reported_at)
    episode.status = "active_flare"
    episode.current_phase_number = 1
    episode.healed_at = None
    episode.phase_started_at = reported_at
    episode.phase_due_end_at = None
    episode.updated_at = reported_at
    create_phase_history(db, episode, 1, reported_at, "relapse")
    create_event(
        db,
        episode_id=episode.id,
        event_type="relapse_marked",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=reported_at,
        payload={"from_phase_number": previous_phase, "to_phase_number": 1, "reported_at": reported_at.isoformat(), "reason": reason},
    )
    create_event(
        db,
        episode_id=episode.id,
        event_type="phase_entered",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=reported_at,
        payload={
            "from_phase_number": previous_phase,
            "to_phase_number": 1,
            "started_at": reported_at.isoformat(),
            "due_end_at": None,
            "reason": "relapse",
        },
    )
    db.commit()
    db.refresh(episode)
    return episode


def _advance_to_next_phase(db: Session, episode: EczemaEpisode, now: datetime, actor_type: str, actor_id: str) -> EczemaEpisode:
    if episode.status != "in_taper":
        return episode
    if episode.current_phase_number < 2 or episode.current_phase_number > 7:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode not in taper")
    if episode.phase_due_end_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode cannot be advanced")
    if local_date(now) < local_date(episode.phase_due_end_at):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode cannot be advanced")

    previous_phase = episode.current_phase_number
    close_current_phase_history(db, episode, episode.phase_due_end_at)
    if previous_phase == 7:
        episode.status = "obsolete"
        episode.obsolete_at = episode.phase_due_end_at
        episode.updated_at = episode.obsolete_at
        create_event(
            db,
            episode_id=episode.id,
            event_type="episode_obsoleted",
            actor_type=actor_type,
            actor_id=actor_id,
            occurred_at=episode.obsolete_at,
            payload={"final_phase_number": 7, "obsoleted_at": episode.obsolete_at.isoformat(), "reason": "protocol_completed"},
        )
        db.commit()
        db.refresh(episode)
        return episode

    next_phase = previous_phase + 1
    transition_at = episode.phase_due_end_at
    episode.current_phase_number = next_phase
    episode.phase_started_at = transition_at
    episode.phase_due_end_at = calculate_phase_due_end_at(transition_at, next_phase)
    episode.updated_at = transition_at
    create_phase_history(db, episode, next_phase, transition_at, "auto_advance")
    create_event(
        db,
        episode_id=episode.id,
        event_type="phase_entered",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=transition_at,
        payload={
            "from_phase_number": previous_phase,
            "to_phase_number": next_phase,
            "started_at": transition_at.isoformat(),
            "due_end_at": episode.phase_due_end_at.isoformat() if episode.phase_due_end_at else None,
            "reason": "auto_advance",
        },
    )
    db.commit()
    db.refresh(episode)
    return episode


def advance_episode(db: Session, account: Account, episode_id: int, now: datetime, actor_type: str, actor_id: str) -> EczemaEpisode:
    episode = get_episode(db, account, episode_id)
    if episode.status != "in_taper":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode not in taper")
    return _advance_to_next_phase(db, episode, now, actor_type, actor_id)


def auto_advance_due_episodes(db: Session, now: datetime) -> int:
    count = 0
    episodes = list(db.execute(select(EczemaEpisode).where(EczemaEpisode.status == "in_taper").order_by(EczemaEpisode.id.asc())).scalars())
    for episode in episodes:
        while episode.status == "in_taper" and episode.phase_due_end_at is not None and local_date(now) >= local_date(episode.phase_due_end_at):
            _advance_to_next_phase(db, episode, now, "system", "system:phase-advance")
            count += 1
            db.refresh(episode)
    return count


def log_application(
    db: Session,
    account: Account,
    episode_id: int,
    applied_at: datetime,
    treatment_type: str | None,
    treatment_name: str | None,
    quantity_text: str | None,
    notes: str | None,
    actor_type: str,
    actor_id: str,
) -> TreatmentApplication:
    normalized_treatment_type = treatment_type or "other"
    if normalized_treatment_type not in VALID_TREATMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid treatment type")
    episode = get_episode(db, account, episode_id)
    if episode.status == "obsolete":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="episode is obsolete")
    application = TreatmentApplication(
        episode_id=episode.id,
        applied_at=applied_at,
        treatment_type=normalized_treatment_type,
        treatment_name=treatment_name,
        quantity_text=quantity_text,
        phase_number_snapshot=episode.current_phase_number,
        notes=notes,
    )
    db.add(application)
    db.flush()
    create_event(
        db,
        episode_id=episode.id,
        event_type="application_logged",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=applied_at,
        payload={
            "application_id": application.id,
            "applied_at": applied_at.isoformat(),
            "treatment_type": normalized_treatment_type,
            "phase_number_snapshot": episode.current_phase_number,
            "treatment_name": treatment_name,
            "quantity_text": quantity_text,
            "notes": notes,
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application already exists for timestamp") from exc
    db.refresh(application)
    return application


def get_application(db: Session, account: Account, application_id: int) -> TreatmentApplication:
    application = db.get(TreatmentApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    episode = get_episode(db, account, application.episode_id)
    if episode.account_id != account.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    return application


def update_application(
    db: Session,
    account: Account,
    application_id: int,
    *,
    applied_at: datetime | None,
    treatment_type: str | None,
    treatment_name: str | None,
    quantity_text: str | None,
    notes: str | None,
    actor_type: str,
    actor_id: str,
) -> TreatmentApplication:
    application = get_application(db, account, application_id)
    if application.is_deleted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application deleted")
    if applied_at is not None:
        application.applied_at = applied_at
    if treatment_type is not None:
        if treatment_type not in VALID_TREATMENT_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid treatment type")
        application.treatment_type = treatment_type
    if treatment_name is not None:
        application.treatment_name = treatment_name
    if quantity_text is not None:
        application.quantity_text = quantity_text
    if notes is not None:
        application.notes = notes
    application.updated_at = utc_now()
    db.add(application)
    try:
        db.flush()
        create_event(
            db,
            episode_id=application.episode_id,
            event_type="application_updated",
            actor_type=actor_type,
            actor_id=actor_id,
            occurred_at=utc_now(),
            payload={"application_id": application.id},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application already exists for timestamp") from exc
    db.refresh(application)
    return application


def void_application(db: Session, account: Account, application_id: int, voided_at: datetime, reason: str, actor_type: str, actor_id: str) -> TreatmentApplication:
    application = get_application(db, account, application_id)
    if application.is_deleted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application deleted")
    if application.is_voided:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application already voided")
    application.is_voided = True
    application.voided_at = voided_at
    application.updated_at = voided_at
    db.add(application)
    create_event(
        db,
        episode_id=application.episode_id,
        event_type="application_voided",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=voided_at,
        payload={"application_id": application.id, "voided_at": voided_at.isoformat(), "reason": reason},
    )
    db.commit()
    db.refresh(application)
    return application


def delete_application(db: Session, account: Account, application_id: int, deleted_at: datetime, actor_type: str, actor_id: str) -> TreatmentApplication:
    application = get_application(db, account, application_id)
    if application.is_deleted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application already deleted")
    application.is_deleted = True
    application.deleted_at = deleted_at
    application.updated_at = deleted_at
    db.add(application)
    create_event(
        db,
        episode_id=application.episode_id,
        event_type="application_deleted",
        actor_type=actor_type,
        actor_id=actor_id,
        occurred_at=deleted_at,
        payload={"application_id": application.id, "deleted_at": deleted_at.isoformat()},
    )
    db.commit()
    db.refresh(application)
    return application


def list_applications(db: Session, account: Account, episode_id: int, include_voided: bool) -> list[TreatmentApplication]:
    episode = get_episode(db, account, episode_id)
    stmt = select(TreatmentApplication).where(TreatmentApplication.episode_id == episode.id)
    stmt = stmt.where(TreatmentApplication.is_deleted.is_(False))
    if not include_voided:
        stmt = stmt.where(TreatmentApplication.is_voided.is_(False))
    return list(db.execute(stmt.order_by(TreatmentApplication.applied_at.asc(), TreatmentApplication.id.asc())).scalars())


def list_events(db: Session, account: Account, episode_id: int, event_type: str | None = None) -> list[EpisodeEvent]:
    episode = get_episode(db, account, episode_id)
    stmt = select(EpisodeEvent).where(EpisodeEvent.episode_id == episode.id)
    if event_type is not None:
        stmt = stmt.where(EpisodeEvent.event_type == event_type)
    return list(db.execute(stmt.order_by(EpisodeEvent.occurred_at.asc(), EpisodeEvent.id.asc())).scalars())


def due_items(db: Session, account: Account, subject_id: int | None = None) -> list[dict]:
    episodes = list_episodes(db, account, subject_id=subject_id)
    items: list[dict] = []
    for episode in episodes:
        if episode.status == "obsolete":
            continue
        applications = list(
            db.execute(
                select(TreatmentApplication)
                .where(
                    TreatmentApplication.episode_id == episode.id,
                    TreatmentApplication.is_deleted.is_(False),
                    TreatmentApplication.is_voided.is_(False),
                )
                .order_by(TreatmentApplication.applied_at.asc(), TreatmentApplication.id.asc())
            ).scalars()
        )
        last_application_at = applications[-1].applied_at if applications else None
        if episode.current_phase_number == 1:
            phase = get_protocol_phase(db, 1)
            local_today = local_date(utc_now())
            count_today = sum(1 for app in applications if local_date(app.applied_at) == local_today)
            due_today = count_today < phase.applications_per_day
            next_due_date = local_midnight(local_today) if due_today else None
            items.append(
                {
                    "episode_id": episode.id,
                    "subject_id": episode.subject_id,
                    "location_id": episode.location_id,
                    "current_phase_number": episode.current_phase_number,
                    "treatment_due_today": due_today,
                    "next_due_at": next_due_date,
                    "last_application_at": last_application_at,
                }
            )
            continue
        phase = get_protocol_phase(db, episode.current_phase_number)
        anchor = last_application_at or episode.phase_started_at
        anchor_date = local_date(anchor)
        interval = phase.apply_every_n_days
        today = local_date(utc_now())
        days_since_anchor = (today - anchor_date).days
        due_today = days_since_anchor >= interval
        next_due_date = local_midnight(today if due_today else anchor_date + timedelta(days=interval))
        items.append(
            {
                "episode_id": episode.id,
                "subject_id": episode.subject_id,
                "location_id": episode.location_id,
                "current_phase_number": episode.current_phase_number,
                "treatment_due_today": due_today,
                "next_due_at": next_due_date,
                "last_application_at": last_application_at,
            }
        )
    return items
