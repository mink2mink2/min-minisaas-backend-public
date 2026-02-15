"""Add board system tables

Revision ID: 20260215_0002
Revises: 20260211_0001
Create Date: 2026-02-15 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260215_0002"
down_revision = "20260211_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create board system tables with search and reaction support"""

    # Create board_categories table
    op.create_table(
        "board_categories",
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
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), nullable=True, server_default="#000000"),
        sa.Column("order_index", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_board_categories_name"),
        sa.UniqueConstraint("slug", name="uq_board_categories_slug"),
    )
    op.create_index("ix_board_categories_slug", "board_categories", ["slug"])

    # Create board_posts table
    op.create_table(
        "board_posts",
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
        sa.Column("title", sa.String(200), nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=True, server_default="published"),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True, server_default="{}"),
        sa.Column("view_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("like_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("bookmark_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_board_posts_author_id"),
        sa.ForeignKeyConstraint(["category_id"], ["board_categories.id"], name="fk_board_posts_category_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_posts_author_id", "board_posts", ["author_id"])
    op.create_index("ix_board_posts_category_id", "board_posts", ["category_id"])
    op.create_index("ix_board_posts_status", "board_posts", ["status"])
    op.create_index("ix_board_posts_created_at", "board_posts", ["created_at"])
    op.create_index(
        "ix_board_posts_search_vector",
        "board_posts",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create comments table
    op.create_table(
        "comments",
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
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("like_count", sa.Integer(), nullable=True, server_default="0"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_comments_author_id"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], name="fk_comments_parent_comment_id"),
        sa.ForeignKeyConstraint(["post_id"], ["board_posts.id"], name="fk_comments_post_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_author_id", "comments", ["author_id"])
    op.create_index("ix_comments_created_at", "comments", ["created_at"])
    op.create_index("ix_comments_parent_comment_id", "comments", ["parent_comment_id"])
    op.create_index("ix_comments_post_id", "comments", ["post_id"])

    # Create post_likes table
    op.create_table(
        "post_likes",
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
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["board_posts.id"], name="fk_post_likes_post_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_post_likes_user_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_post_like"),
    )
    op.create_index("ix_post_likes_post_id", "post_likes", ["post_id"])
    op.create_index("ix_post_likes_user_id", "post_likes", ["user_id"])

    # Create post_bookmarks table
    op.create_table(
        "post_bookmarks",
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
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["board_posts.id"], name="fk_post_bookmarks_post_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_post_bookmarks_user_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_post_bookmark"),
    )
    op.create_index("ix_post_bookmarks_post_id", "post_bookmarks", ["post_id"])
    op.create_index("ix_post_bookmarks_user_id", "post_bookmarks", ["user_id"])

    # Create comment_likes table
    op.create_table(
        "comment_likes",
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
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], name="fk_comment_likes_comment_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_comment_likes_user_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", "user_id", name="uq_comment_like"),
    )
    op.create_index("ix_comment_likes_comment_id", "comment_likes", ["comment_id"])
    op.create_index("ix_comment_likes_user_id", "comment_likes", ["user_id"])

    # Enable pg_trgm extension for similarity matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Create trigger for updating search_vector on board_posts
    op.execute(
        """
        CREATE TRIGGER update_search_vector
        BEFORE INSERT OR UPDATE ON board_posts
        FOR EACH ROW
        EXECUTE FUNCTION tsvector_update_trigger(
            search_vector,
            'pg_catalog.simple',
            title,
            content
        )
        """
    )


def downgrade() -> None:
    """Drop board system tables and triggers"""

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_search_vector ON board_posts")

    # Drop tables in reverse order of creation
    op.drop_table("comment_likes")
    op.drop_table("post_bookmarks")
    op.drop_table("post_likes")
    op.drop_table("comments")
    op.drop_table("board_posts")
    op.drop_table("board_categories")

    # Optionally drop extension (only if not used elsewhere)
    # op.execute("DROP EXTENSION IF EXISTS pg_trgm")
