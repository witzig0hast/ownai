"""add oidc subject for sso login

Revision ID: e0be0579df2c
Revises: 04b0d5ecb38f
Create Date: 2026-10-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0be0579df2c'
down_revision: Union[str, None] = '04b0d5ecb38f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('oidc_subject', sa.String(length=255), nullable=True))
    op.create_index('ix_users_oidc_subject', 'users', ['oidc_subject'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_oidc_subject', table_name='users')
    op.drop_column('users', 'oidc_subject')
