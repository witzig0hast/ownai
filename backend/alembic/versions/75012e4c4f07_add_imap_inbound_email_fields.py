"""add imap inbound email fields

Revision ID: 75012e4c4f07
Revises: 4a39e24e885c
Create Date: 2026-10-03 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75012e4c4f07'
down_revision: Union[str, None] = '4a39e24e885c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('email_accounts', sa.Column('imap_host', sa.String(length=255), nullable=True))
    op.add_column('email_accounts', sa.Column('imap_port', sa.Integer(), nullable=True))
    op.add_column('email_accounts', sa.Column('imap_username', sa.String(length=255), nullable=True))
    op.add_column('email_accounts', sa.Column('encrypted_imap_password', sa.Text(), nullable=True))
    op.add_column(
        'email_accounts',
        sa.Column('inbound_agent_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('email_accounts', 'inbound_agent_enabled')
    op.drop_column('email_accounts', 'encrypted_imap_password')
    op.drop_column('email_accounts', 'imap_username')
    op.drop_column('email_accounts', 'imap_port')
    op.drop_column('email_accounts', 'imap_host')
