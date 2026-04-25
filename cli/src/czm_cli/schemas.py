from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiErrorPayload(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    error: ApiErrorPayload


class SubjectOut(BaseModel):
    id: int
    account_id: int | None = None
    display_name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class SubjectListResponse(BaseModel):
    subjects: list[SubjectOut]


class LocationOut(BaseModel):
    id: int
    code: str
    display_name: str
    created_at: datetime | None = None
    image: dict | None = None

    model_config = ConfigDict(extra="ignore")


class LocationCreateResponse(BaseModel):
    location: LocationOut


class LocationListResponse(BaseModel):
    locations: list[LocationOut]


class EpisodeOut(BaseModel):
    id: int
    subject_id: int
    location_id: int
    status: str
    current_phase_number: int
    phase_started_at: datetime
    phase_due_end_at: datetime | None = None
    protocol_version: str
    healed_at: datetime | None = None
    obsolete_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class EpisodeResponse(BaseModel):
    episode: EpisodeOut


class EpisodeListResponse(BaseModel):
    episodes: list[EpisodeOut]


class ApplicationOut(BaseModel):
    id: int
    episode_id: int
    applied_at: datetime
    treatment_type: str
    treatment_name: str | None = None
    quantity_text: str | None = None
    phase_number_snapshot: int
    is_voided: bool
    voided_at: datetime | None = None
    is_deleted: bool | None = None
    deleted_at: datetime | None = None
    notes: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class ApplicationResponse(BaseModel):
    application: ApplicationOut


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationOut]


class EventOut(BaseModel):
    id: int
    event_uuid: str
    episode_id: int
    event_type: str
    actor_type: str
    actor_id: str | None = None
    occurred_at: datetime
    payload: dict
    created_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class EventListResponse(BaseModel):
    events: list[EventOut]


class TimelineResponse(BaseModel):
    timeline: list[EventOut]


class DueItem(BaseModel):
    episode_id: int
    subject_id: int
    location_id: int
    current_phase_number: int
    treatment_due_today: bool
    next_due_at: datetime | None = None
    last_application_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class DueListResponse(BaseModel):
    due: list[DueItem]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    account: dict

    model_config = ConfigDict(extra="ignore")


class AdherenceDayOut(BaseModel):
    date: date
    episode_id: int
    subject_id: int
    location_id: int
    phase_number: int
    expected_applications: int
    completed_applications: int
    credited_applications: int
    status: str
    source: str
    calculated_at: datetime
    finalized_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class AdherenceCalendarResponse(BaseModel):
    days: list[AdherenceDayOut]

    model_config = ConfigDict(extra="ignore")


class AdherenceSummaryResponse(BaseModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    expected_applications: int
    completed_applications: int
    credited_applications: int
    adherence_score: float | None = None
    completed_days: int
    partial_days: int
    missed_days: int
    not_due_days: int
    future_days: int

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class EpisodeAdherenceResponse(BaseModel):
    episode_id: int
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    summary: AdherenceSummaryResponse
    days: list[AdherenceDayOut]

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class AdherenceRebuildResponse(BaseModel):
    episodes_processed: int
    rows_persisted: int

    model_config = ConfigDict(extra="ignore")
