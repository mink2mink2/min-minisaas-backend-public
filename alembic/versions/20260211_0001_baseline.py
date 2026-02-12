"""baseline schema from SQLAlchemy metadata

Revision ID: 20260211_0001
Revises:
Create Date: 2026-02-11 21:20:00
"""

from __future__ import annotations

from alembic import op

from app.core.database import Base
import app.db.model_registry  # noqa: F401


revision = "20260211_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
