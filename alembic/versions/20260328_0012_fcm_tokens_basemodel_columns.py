"""Backfill BaseModel columns for fcm_tokens

Revision ID: 20260328_0012
Revises: 20260318_0011
Create Date: 2026-03-28 18:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260328_0012"
down_revision = "20260318_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fcm_tokens
        ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false
        """
    )
    op.execute(
        """
        UPDATE fcm_tokens
        SET is_deleted = COALESCE(is_deleted, false)
        WHERE is_deleted IS NULL
        """
    )
    op.execute(
        """
        ALTER TABLE fcm_tokens
        ALTER COLUMN is_deleted SET NOT NULL
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE fcm_tokens
        DROP COLUMN IF EXISTS is_deleted
        """
    )
