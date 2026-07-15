"""A6 : table interviews — planification d'entretiens (§6-A6, §4)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="PROPOSED"),
        sa.Column("proposed_slots", postgresql.JSONB, server_default="[]"),
        sa.Column("slot_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slot_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candidate_tz", sa.String(64), server_default="Africa/Tunis"),
        sa.Column("recruiter_tz", sa.String(64), server_default="Africa/Tunis"),
        sa.Column("calendar_ref", sa.String(255), nullable=True),
        sa.Column("cancel_reason", sa.Text, server_default=""),
        sa.Column("reschedule_count", sa.Integer, server_default="0"),
        sa.Column("candidate_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recruiter_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"])
    op.create_index("ix_interviews_status", "interviews", ["status"])


def downgrade() -> None:
    op.drop_index("ix_interviews_status", table_name="interviews")
    op.drop_index("ix_interviews_application_id", table_name="interviews")
    op.drop_table("interviews")