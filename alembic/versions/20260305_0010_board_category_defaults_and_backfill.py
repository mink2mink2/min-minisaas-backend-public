"""Harden board_categories defaults and backfill nullable system columns

Revision ID: 20260305_0010
Revises: 20260304_0009
Create Date: 2026-03-05 19:40:00
"""

from __future__ import annotations

from alembic import op


revision = "20260305_0010"
down_revision = "20260304_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Backfill nullable system fields created by earlier seed/manual inserts.
    op.execute("UPDATE board_categories SET id = gen_random_uuid() WHERE id IS NULL")
    op.execute("UPDATE board_categories SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE board_categories SET updated_at = COALESCE(updated_at, created_at, now()) WHERE updated_at IS NULL")
    op.execute("UPDATE board_categories SET is_deleted = false WHERE is_deleted IS NULL")
    op.execute("UPDATE board_categories SET is_active = true WHERE is_active IS NULL")

    # Enforce safe defaults for future writes.
    op.execute("ALTER TABLE board_categories ALTER COLUMN id SET DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE board_categories ALTER COLUMN created_at SET DEFAULT now()")
    op.execute("ALTER TABLE board_categories ALTER COLUMN updated_at SET DEFAULT now()")
    op.execute("ALTER TABLE board_categories ALTER COLUMN is_deleted SET DEFAULT false")
    op.execute("ALTER TABLE board_categories ALTER COLUMN is_active SET DEFAULT true")

    # Lock down nullability now that rows are backfilled.
    op.execute("ALTER TABLE board_categories ALTER COLUMN id SET NOT NULL")
    op.execute("ALTER TABLE board_categories ALTER COLUMN created_at SET NOT NULL")
    op.execute("ALTER TABLE board_categories ALTER COLUMN updated_at SET NOT NULL")
    op.execute("ALTER TABLE board_categories ALTER COLUMN is_deleted SET NOT NULL")
    op.execute("ALTER TABLE board_categories ALTER COLUMN is_active SET NOT NULL")

    # Keep updated_at coherent for raw SQL updates too.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_board_categories_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_board_categories_updated_at ON board_categories")
    op.execute(
        """
        CREATE TRIGGER trg_board_categories_updated_at
        BEFORE UPDATE ON board_categories
        FOR EACH ROW
        EXECUTE FUNCTION set_board_categories_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_board_categories_updated_at ON board_categories")
    op.execute("DROP FUNCTION IF EXISTS set_board_categories_updated_at()")

