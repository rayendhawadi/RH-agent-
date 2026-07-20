"""Archivage des candidatures (soft-delete réversible)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_applications_archived_at", "applications", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_applications_archived_at", table_name="applications")
    op.drop_column("applications", "archived_at")