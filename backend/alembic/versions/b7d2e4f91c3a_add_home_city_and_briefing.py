"""add home_city and morning briefing settings to users

Revision ID: b7d2e4f91c3a
Revises: a3c91f7e2b10
Create Date: 2026-10-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2e4f91c3a'
down_revision: Union[str, None] = 'a3c91f7e2b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('home_city', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('briefing_enabled', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('briefing_hour', sa.Integer(), nullable=False, server_default='7'))
    op.add_column('users', sa.Column('briefing_minute', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('briefing_last_sent_date', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'briefing_last_sent_date')
    op.drop_column('users', 'briefing_minute')
    op.drop_column('users', 'briefing_hour')
    op.drop_column('users', 'briefing_enabled')
    op.drop_column('users', 'home_city')
