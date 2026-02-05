"""Initial migration - Create all tables

Revision ID: 001
Revises:
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create manuals table
    op.create_table(
        'manuals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('manual_id', sa.String(100), unique=True, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('total_steps', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
    )
    op.create_index('idx_manuals_manual_id', 'manuals', ['manual_id'])

    # Create manual_steps table
    op.create_table(
        'manual_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('manual_uuid', postgresql.UUID(as_uuid=True), sa.ForeignKey('manuals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.UniqueConstraint('manual_uuid', 'step_number', name='uq_manual_step_number'),
    )
    op.create_index('idx_manual_steps_manual_id', 'manual_steps', ['manual_uuid'])
    op.create_index('idx_manual_steps_step_number', 'manual_steps', ['manual_uuid', 'step_number'])

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.String(100), unique=True, nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('manual_uuid', postgresql.UUID(as_uuid=True), sa.ForeignKey('manuals.id'), nullable=False),
        sa.Column('current_step', sa.Integer(), nullable=False, default=1),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('started_at', sa.String(50), nullable=False),
        sa.Column('ended_at', sa.String(50), nullable=True),
        sa.Column('last_activity_at', sa.String(50), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=False),
        sa.CheckConstraint('current_step >= 0', name='check_current_step_positive'),
        sa.CheckConstraint("status IN ('active', 'completed', 'abandoned')", name='check_valid_status'),
    )
    op.create_index('idx_sessions_session_id', 'sessions', ['session_id'])
    op.create_index('idx_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('idx_sessions_status', 'sessions', ['status'])
    op.create_index('idx_sessions_manual_id', 'sessions', ['manual_uuid'])

    # Create conversation_messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_uuid', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('sender', sa.String(20), nullable=False),
        sa.Column('step_at_time', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.CheckConstraint("sender IN ('user', 'agent', 'system')", name='check_valid_sender'),
    )
    op.create_index('idx_messages_session_id', 'conversation_messages', ['session_uuid'])
    op.create_index('idx_messages_created_at', 'conversation_messages', ['session_uuid', 'created_at'])

    # Create progress_events table
    op.create_table(
        'progress_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_uuid', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_status', sa.String(20), nullable=False),
        sa.Column('previous_step', sa.Integer(), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.UniqueConstraint('session_uuid', 'idempotency_key', name='uq_session_idempotency_key'),
        sa.CheckConstraint("step_status IN ('DONE', 'ONGOING')", name='check_valid_step_status'),
    )
    op.create_index('idx_progress_events_session_id', 'progress_events', ['session_uuid'])
    op.create_index('idx_progress_events_idempotency', 'progress_events', ['idempotency_key'])


def downgrade() -> None:
    op.drop_table('progress_events')
    op.drop_table('conversation_messages')
    op.drop_table('sessions')
    op.drop_table('manual_steps')
    op.drop_table('manuals')
