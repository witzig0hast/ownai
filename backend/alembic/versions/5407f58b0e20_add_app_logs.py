"""add app logs

Revision ID: 5407f58b0e20
Revises: f7695397b862
Create Date: 2026-10-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5407f58b0e20'
down_revision: Union[str, None] = 'f7695397b862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('app_logs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=True),
    sa.Column('category', sa.String(length=32), nullable=False),
    sa.Column('level', sa.String(length=16), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('detail', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_app_logs_user_id'), 'app_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_app_logs_category'), 'app_logs', ['category'], unique=False)
    op.create_index(op.f('ix_app_logs_created_at'), 'app_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_app_logs_created_at'), table_name='app_logs')
    op.drop_index(op.f('ix_app_logs_category'), table_name='app_logs')
    op.drop_index(op.f('ix_app_logs_user_id'), table_name='app_logs')
    op.drop_table('app_logs')
