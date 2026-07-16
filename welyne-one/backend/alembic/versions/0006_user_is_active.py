"""ajoute is_active à users (gestion des comptes — admin only)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("users", "is_active")