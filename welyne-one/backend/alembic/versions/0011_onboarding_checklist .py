"""Ajoute role_templates et onboarding_tasks (§4/§6-A8 — jamais créées avant).

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "role_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("role_category", sa.String(50), nullable=False, unique=True),
        sa.Column("required_documents", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("equipment", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("accounts_to_create", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("week_one_agenda", postgresql.JSONB, nullable=False, server_default="[]"),
    )

    op.create_table(
        "onboarding_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("task", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("owner", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("reject_reason", sa.String(500), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_onboarding_tasks_application_id", "onboarding_tasks", ["application_id"])


def downgrade():
    op.drop_index("ix_onboarding_tasks_application_id", table_name="onboarding_tasks")
    op.drop_table("onboarding_tasks")
    op.drop_table("role_templates")