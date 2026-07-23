"""manual_chunk

Revision ID: b0c3f6482de1
Revises: 0012
Create Date: 2026-07-22 14:24:16.756558
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b0c3f6482de1'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('manual_chunks',
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('manual_chunks')
