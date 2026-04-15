"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("username", name="uq_accounts_username"),
    )
    op.create_table(
        "taper_protocol_phases",
        sa.Column("phase_number", sa.Integer(), primary_key=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("apply_every_n_days", sa.Integer(), nullable=False),
        sa.Column("applications_per_day", sa.Integer(), nullable=False),
    )
    op.create_table(
        "account_api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_account_api_keys_key_hash", "account_api_keys", ["key_hash"], unique=False)
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "body_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("account_id", "code", name="uq_body_locations_account_code"),
    )
    op.create_table(
        "eczema_episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("body_locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_phase_number", sa.Integer(), nullable=False),
        sa.Column("phase_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phase_due_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("protocol_version", sa.String(length=50), nullable=False),
        sa.Column("healed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("obsolete_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_eczema_episodes_subject_location_active",
        "eczema_episodes",
        ["subject_id", "location_id"],
        unique=True,
        sqlite_where=sa.text("status != 'obsolete'"),
        postgresql_where=sa.text("status != 'obsolete'"),
    )
    op.create_table(
        "episode_phase_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("eczema_episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "treatment_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("eczema_episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("treatment_type", sa.String(length=20), nullable=False),
        sa.Column("treatment_name", sa.String(length=255), nullable=True),
        sa.Column("quantity_text", sa.String(length=255), nullable=True),
        sa.Column("phase_number_snapshot", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_voided", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("episode_id", "applied_at", name="uq_treatment_applications_episode_applied_at"),
    )
    op.create_table(
        "episode_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_uuid", sa.String(length=36), nullable=False, unique=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("eczema_episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_episode_events_episode_id_occurred_at", "episode_events", ["episode_id", "occurred_at", "id"], unique=False)
    op.create_index("ix_episode_events_event_type_occurred_at", "episode_events", ["event_type", "occurred_at", "id"], unique=False)

    op.bulk_insert(
        sa.table(
            "taper_protocol_phases",
            sa.column("phase_number", sa.Integer()),
            sa.column("duration_days", sa.Integer()),
            sa.column("apply_every_n_days", sa.Integer()),
            sa.column("applications_per_day", sa.Integer()),
        ),
        [
            {"phase_number": 1, "duration_days": None, "apply_every_n_days": 1, "applications_per_day": 2},
            {"phase_number": 2, "duration_days": 28, "apply_every_n_days": 2, "applications_per_day": 1},
            {"phase_number": 3, "duration_days": 14, "apply_every_n_days": 3, "applications_per_day": 1},
            {"phase_number": 4, "duration_days": 14, "apply_every_n_days": 4, "applications_per_day": 1},
            {"phase_number": 5, "duration_days": 14, "apply_every_n_days": 5, "applications_per_day": 1},
            {"phase_number": 6, "duration_days": 14, "apply_every_n_days": 6, "applications_per_day": 1},
            {"phase_number": 7, "duration_days": 14, "apply_every_n_days": 7, "applications_per_day": 1},
        ],
    )


def downgrade() -> None:
    op.drop_table("episode_events")
    op.drop_table("treatment_applications")
    op.drop_table("episode_phase_history")
    op.drop_index("uq_eczema_episodes_subject_location_active", table_name="eczema_episodes")
    op.drop_table("eczema_episodes")
    op.drop_table("body_locations")
    op.drop_table("subjects")
    op.drop_index("ix_account_api_keys_key_hash", table_name="account_api_keys")
    op.drop_table("account_api_keys")
    op.drop_table("taper_protocol_phases")
    op.drop_table("accounts")
