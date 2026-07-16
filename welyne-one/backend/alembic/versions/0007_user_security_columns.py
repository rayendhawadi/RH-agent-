"""ajoute email_verified, verification_token, password_reset_required à users (§7 sécurité comptes)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.false()))
    op.add_column("users", sa.Column("verification_token", sa.String(64), nullable=True))
    op.add_column(
        "users",
        sa.Column("password_reset_required", sa.Boolean(), server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "password_reset_required")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "email_verified")