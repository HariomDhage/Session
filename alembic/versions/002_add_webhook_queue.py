"""Add webhook queue table for retry mechanism.

Revision ID: 002
Revises: 001
Create Date: 2024-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_queue table
    op.create_table(
        'webhook_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=False, default=3),
        sa.Column('last_attempt_at', sa.String(50), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('next_retry_at', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_webhook_queue_status', 'webhook_queue', ['status'])
    op.create_index('idx_webhook_queue_next_retry', 'webhook_queue', ['status', 'next_retry_at'])


def downgrade() -> None:
    op.drop_index('idx_webhook_queue_next_retry', table_name='webhook_queue')
    op.drop_index('idx_webhook_queue_status', table_name='webhook_queue')
    op.drop_table('webhook_queue')
