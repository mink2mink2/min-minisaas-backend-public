"""Add chat domain tables

Revision ID: 20260215_0004
Revises: 20260215_0003
Create Date: 2026-02-15 19:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260215_0004"
down_revision = "20260215_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create chat domain tables"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("chat_rooms"):
        return

    op.create_table(
        "chat_rooms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_group", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_chat_rooms_created_by"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_rooms_created_by", "chat_rooms", ["created_by"])
    op.create_index("ix_chat_rooms_created_at", "chat_rooms", ["created_at"])

    op.create_table(
        "chat_room_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], name="fk_chat_room_members_room_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_room_members_user_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "user_id", name="uq_chat_room_members_room_user"),
    )
    op.create_index("ix_chat_room_members_room_id", "chat_room_members", ["room_id"])
    op.create_index("ix_chat_room_members_user_id", "chat_room_members", ["user_id"])
    op.create_index(
        "ix_chat_room_members_room_user",
        "chat_room_members",
        ["room_id", "user_id"],
    )

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.ForeignKeyConstraint(["room_id"], ["chat_rooms.id"], name="fk_chat_messages_room_id"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name="fk_chat_messages_sender_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_room_id", "chat_messages", ["room_id"])
    op.create_index("ix_chat_messages_sender_id", "chat_messages", ["sender_id"])
    op.create_index(
        "ix_chat_messages_room_created_at",
        "chat_messages",
        ["room_id", "created_at"],
    )


def downgrade() -> None:
    """Drop chat domain tables"""
    op.drop_index("ix_chat_messages_room_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_room_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_room_members_room_user", table_name="chat_room_members")
    op.drop_index("ix_chat_room_members_user_id", table_name="chat_room_members")
    op.drop_index("ix_chat_room_members_room_id", table_name="chat_room_members")
    op.drop_table("chat_room_members")

    op.drop_index("ix_chat_rooms_created_at", table_name="chat_rooms")
    op.drop_index("ix_chat_rooms_created_by", table_name="chat_rooms")
    op.drop_table("chat_rooms")
