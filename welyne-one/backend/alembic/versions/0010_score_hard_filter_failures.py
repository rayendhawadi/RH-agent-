"""Ajoute scores.hard_filter_failures — calculé mais jamais persisté jusqu'ici.

Revision ID: 0009_score_hard_filter_failures
Revises: 0008_llm_usage
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "scores",
        sa.Column("hard_filter_failures", postgresql.JSONB, nullable=False, server_default="[]"),
    )


def downgrade():
    op.drop_column("scores", "hard_filter_failures")