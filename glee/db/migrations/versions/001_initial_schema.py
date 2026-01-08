"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'review_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_path', sa.String(512), nullable=False),
        sa.Column('claude_session_id', sa.String(36), nullable=True),
        sa.Column('files', sa.JSON, nullable=False),
        sa.Column('iteration', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_iterations', sa.Integer, nullable=False, server_default='10'),
        sa.Column('status', sa.Enum('in_progress', 'approved', 'max_iterations', 'aborted', 'needs_human', name='review_status'), nullable=False, server_default='in_progress'),
        sa.Column('pending_questions', sa.JSON, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'review_iterations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('review_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('iteration', sa.Integer, nullable=False),
        sa.Column('codex_feedback', sa.Text, nullable=True),
        sa.Column('claude_changes', sa.Text, nullable=True),
        sa.Column('human_answers', sa.JSON, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Indexes
    op.create_index('idx_sessions_project', 'review_sessions', ['project_path'])
    op.create_index('idx_sessions_status', 'review_sessions', ['status'])
    op.create_index('idx_sessions_created', 'review_sessions', ['created_at'])
    op.create_index('idx_iterations_session', 'review_iterations', ['session_id'])


def downgrade() -> None:
    op.drop_index('idx_iterations_session', 'review_iterations')
    op.drop_index('idx_sessions_created', 'review_sessions')
    op.drop_index('idx_sessions_status', 'review_sessions')
    op.drop_index('idx_sessions_project', 'review_sessions')
    op.drop_table('review_iterations')
    op.drop_table('review_sessions')
