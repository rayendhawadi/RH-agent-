"""ajoute message_log (§4, §5.2, A7)

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("to", sa.String(255), nullable=False),
        sa.Column("channel", sa.String(20), server_default="email"),
        sa.Column("template_id", sa.String(50), nullable=False),
        sa.Column("rendered_body", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="sent"),
        sa.Column("validated_by", sa.String(255), server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("message_log")