"""Populate nicknames for existing users without nicknames

Revision ID: 20260304_0009
Revises: 20260304_0008
Create Date: 2026-03-04 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260304_0009"
down_revision = "20260304_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # transaction-safe, idempotent backfill
    op.execute(
        sa.text(
            """
            UPDATE users
            SET nickname = 'User_' || SUBSTRING(MD5(id::text), 1, 8)
            WHERE nickname IS NULL OR nickname = ''
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE users SET nickname = NULL WHERE nickname LIKE 'User_%'"))
