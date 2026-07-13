"""A5 : langue candidat + suivi des relances par slot (§6-A5)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("language", sa.String(5), server_default="fr"))
    op.add_column("conversations", sa.Column("retry_counts", postgresql.JSONB, server_default="{}"))


def downgrade() -> None:
    op.drop_column("conversations", "retry_counts")
    op.drop_column("conversations", "language")