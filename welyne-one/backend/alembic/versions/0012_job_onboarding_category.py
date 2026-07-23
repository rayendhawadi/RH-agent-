"""Ajoute jobs.onboarding_category — choix explicite du recruteur (§6-A8),
sinon A8 retombe sur la détection auto par mot-clé du titre.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "jobs",
        sa.Column("onboarding_category", sa.String(length=50), nullable=True),
    )


def downgrade():
    op.drop_column("jobs", "onboarding_category")