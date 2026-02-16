"""Backfill BaseModel columns for blog tables

Revision ID: 20260216_0007
Revises: 20260216_0006
Create Date: 2026-02-16 23:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260216_0007"
down_revision = "20260216_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_categories",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.add_column(
        "blog_likes",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "blog_likes",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.add_column(
        "blog_subscriptions",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "blog_subscriptions",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("blog_subscriptions", "is_deleted")
    op.drop_column("blog_subscriptions", "updated_at")
    op.drop_column("blog_likes", "is_deleted")
    op.drop_column("blog_likes", "updated_at")
    op.drop_column("blog_categories", "is_deleted")
