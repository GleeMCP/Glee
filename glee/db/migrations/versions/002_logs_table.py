"""Add logs table

Revision ID: 002
Revises: 001
Create Date: 2025-01-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'logs',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('level', sa.String(10), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('module', sa.String(255), nullable=True),
        sa.Column('function', sa.String(255), nullable=True),
        sa.Column('line', sa.Integer, nullable=True),
        sa.Column('extra', sa.JSON, nullable=True),
    )

    op.create_index('idx_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('idx_logs_level', 'logs', ['level'])


def downgrade() -> None:
    op.drop_index('idx_logs_level', 'logs')
    op.drop_index('idx_logs_timestamp', 'logs')
    op.drop_table('logs')
