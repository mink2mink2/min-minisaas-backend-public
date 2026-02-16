"""Push notification domain tables

Revision ID: 20260216_0006
Revises: 20260216_0005
Create Date: 2026-02-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260216_0006'
down_revision = '20260216_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create fcm_tokens table
    op.create_table(
        'fcm_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(500), nullable=False, unique=True),
        sa.Column('platform', sa.String(20), nullable=False),  # android, ios, web
        sa.Column('device_name', sa.String(200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fcm_tokens_user_id', 'fcm_tokens', ['user_id'], unique=False)
    op.create_index('ix_fcm_tokens_token', 'fcm_tokens', ['token'], unique=False)
    op.create_index('ix_fcm_tokens_platform', 'fcm_tokens', ['platform'], unique=False)

    # Create push_notifications table
    op.create_table(
        'push_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=True),  # blog.post.created, chat.message, etc
        sa.Column('related_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_push_notifications_user_id', 'push_notifications', ['user_id'], unique=False)
    op.create_index('ix_push_notifications_event_type', 'push_notifications', ['event_type'], unique=False)
    op.create_index('ix_push_notifications_created_at', 'push_notifications', ['created_at'], unique=False)
    op.create_index('ix_push_notifications_is_read', 'push_notifications', ['is_read'], unique=False)


def downgrade() -> None:
    op.drop_table('push_notifications')
    op.drop_table('fcm_tokens')
