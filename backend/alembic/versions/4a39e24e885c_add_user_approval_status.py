"""add user approval status

Revision ID: 4a39e24e885c
Revises: 5407f58b0e20
Create Date: 2026-10-03 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a39e24e885c'
down_revision: Union[str, None] = '5407f58b0e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default='approved' both backfills every existing row (so no one already using the
    # app gets locked out by this migration) and is a safety net for any insert that somehow
    # bypasses the ORM-level default of "pending" (app/db/models.py).
    op.add_column('users', sa.Column('approval_status', sa.String(length=16), nullable=False, server_default='approved'))


def downgrade() -> None:
    op.drop_column('users', 'approval_status')
