"""add pending actions

Revision ID: 04b0d5ecb38f
Revises: 75012e4c4f07
Create Date: 2026-10-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04b0d5ecb38f'
down_revision: Union[str, None] = '75012e4c4f07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pending_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('conversation_id', sa.String(length=36), nullable=False),
        sa.Column('tool_name', sa.String(length=64), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pending_actions_created_at', 'pending_actions', ['created_at'])
    op.create_index('ix_pending_actions_user_id', 'pending_actions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_pending_actions_user_id', table_name='pending_actions')
    op.drop_index('ix_pending_actions_created_at', table_name='pending_actions')
    op.drop_table('pending_actions')
