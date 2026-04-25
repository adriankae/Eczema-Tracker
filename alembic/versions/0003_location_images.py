"""add location image metadata

Revision ID: 0003_location_images
Revises: 0002_episode_daily_adherence
Create Date: 2026-04-25 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_location_images"
down_revision = "0002_episode_daily_adherence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("body_locations", sa.Column("image_storage_key", sa.String(length=255), nullable=True))
    op.add_column("body_locations", sa.Column("image_mime_type", sa.String(length=100), nullable=True))
    op.add_column("body_locations", sa.Column("image_size_bytes", sa.Integer(), nullable=True))
    op.add_column("body_locations", sa.Column("image_sha256", sa.String(length=64), nullable=True))
    op.add_column("body_locations", sa.Column("image_original_filename", sa.String(length=255), nullable=True))
    op.add_column("body_locations", sa.Column("image_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("uq_body_locations_image_storage_key", "body_locations", ["image_storage_key"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_body_locations_image_storage_key", table_name="body_locations")
    op.drop_column("body_locations", "image_uploaded_at")
    op.drop_column("body_locations", "image_original_filename")
    op.drop_column("body_locations", "image_sha256")
    op.drop_column("body_locations", "image_size_bytes")
    op.drop_column("body_locations", "image_mime_type")
    op.drop_column("body_locations", "image_storage_key")
