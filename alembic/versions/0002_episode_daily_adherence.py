"""add episode daily adherence

Revision ID: 0002_episode_daily_adherence
Revises: 0001_initial
Create Date: 2026-04-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_episode_daily_adherence"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "episode_daily_adherence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("eczema_episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("body_locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("phase_number", sa.Integer(), nullable=False),
        sa.Column("expected_applications", sa.Integer(), nullable=False),
        sa.Column("completed_applications", sa.Integer(), nullable=False),
        sa.Column("credited_applications", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("episode_id", "date", name="uq_episode_daily_adherence_episode_date"),
        sa.CheckConstraint("expected_applications >= 0", name="ck_episode_daily_adherence_expected_nonnegative"),
        sa.CheckConstraint("completed_applications >= 0", name="ck_episode_daily_adherence_completed_nonnegative"),
        sa.CheckConstraint("credited_applications >= 0", name="ck_episode_daily_adherence_credited_nonnegative"),
        sa.CheckConstraint("credited_applications <= expected_applications", name="ck_episode_daily_adherence_credited_lte_expected"),
        sa.CheckConstraint(
            "status in ('completed', 'partial', 'missed', 'not_due', 'future')",
            name="ck_episode_daily_adherence_status",
        ),
        sa.CheckConstraint(
            "source in ('calculated', 'backfill', 'rebuild', 'system')",
            name="ck_episode_daily_adherence_source",
        ),
    )
    op.create_index("ix_episode_daily_adherence_account_date", "episode_daily_adherence", ["account_id", "date"], unique=False)
    op.create_index("ix_episode_daily_adherence_episode_date", "episode_daily_adherence", ["episode_id", "date"], unique=False)
    op.create_index("ix_episode_daily_adherence_subject_date", "episode_daily_adherence", ["subject_id", "date"], unique=False)
    op.create_index("ix_episode_daily_adherence_location_date", "episode_daily_adherence", ["location_id", "date"], unique=False)
    op.create_index("ix_episode_daily_adherence_status_date", "episode_daily_adherence", ["status", "date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_episode_daily_adherence_status_date", table_name="episode_daily_adherence")
    op.drop_index("ix_episode_daily_adherence_location_date", table_name="episode_daily_adherence")
    op.drop_index("ix_episode_daily_adherence_subject_date", table_name="episode_daily_adherence")
    op.drop_index("ix_episode_daily_adherence_episode_date", table_name="episode_daily_adherence")
    op.drop_index("ix_episode_daily_adherence_account_date", table_name="episode_daily_adherence")
    op.drop_table("episode_daily_adherence")
