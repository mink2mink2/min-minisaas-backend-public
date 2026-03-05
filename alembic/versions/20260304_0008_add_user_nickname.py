"""Add nickname column to users table

Revision ID: 20260304_0008
Revises: 20260216_0007
Create Date: 2026-03-04 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260304_0008"
down_revision = "20260216_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(50)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nickname")
