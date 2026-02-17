"""Seed default board categories in an idempotent way.

Usage:
  .venv/bin/python scripts/seed_board_categories.py
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


DEFAULT_BOARD_CATEGORIES: list[dict[str, Any]] = [
    {"name": "자유", "slug": "free", "color": "#3B82F6", "order_index": 10},
    {"name": "질문", "slug": "qna", "color": "#10B981", "order_index": 20},
    {"name": "정보", "slug": "tips", "color": "#8B5CF6", "order_index": 30},
    {"name": "공지", "slug": "notice", "color": "#EF4444", "order_index": 40},
]


@dataclass(frozen=True)
class SeedPlan:
    to_insert: list[dict[str, Any]]
    to_update: list[dict[str, Any]]
    unchanged: int


def build_seed_plan(
    existing_by_slug: dict[str, dict[str, Any]],
    defaults: list[dict[str, Any]] | None = None,
) -> SeedPlan:
    """Build insert/update plan from current DB rows and defaults."""
    default_rows = defaults or DEFAULT_BOARD_CATEGORIES
    to_insert: list[dict[str, Any]] = []
    to_update: list[dict[str, Any]] = []
    unchanged = 0

    for row in default_rows:
        slug = row["slug"]
        existing = existing_by_slug.get(slug)
        if not existing:
            to_insert.append(row)
            continue

        changed = (
            existing.get("name") != row["name"]
            or existing.get("color") != row["color"]
            or existing.get("order_index") != row["order_index"]
            or existing.get("is_active") is not True
        )
        if changed:
            to_update.append(row)
        else:
            unchanged += 1

    return SeedPlan(to_insert=to_insert, to_update=to_update, unchanged=unchanged)


async def ensure_board_categories_seeded() -> SeedPlan:
    """Apply seed data to board_categories table and return applied plan."""
    engine = create_async_engine(settings.DATABASE_URL)

    try:
        async with engine.begin() as conn:
            rows_result = await conn.execute(
                text(
                    """
                    SELECT slug, name, color, order_index, is_active
                    FROM board_categories
                    """
                )
            )
            existing_by_slug: dict[str, dict[str, Any]] = {
                row.slug: {
                    "name": row.name,
                    "color": row.color,
                    "order_index": row.order_index,
                    "is_active": row.is_active,
                }
                for row in rows_result.fetchall()
            }

            plan = build_seed_plan(existing_by_slug)

            for row in plan.to_insert:
                await conn.execute(
                    text(
                        """
                        INSERT INTO board_categories
                            (name, slug, color, order_index, is_active)
                        VALUES
                            (:name, :slug, :color, :order_index, true)
                        """
                    ),
                    row,
                )

            for row in plan.to_update:
                await conn.execute(
                    text(
                        """
                        UPDATE board_categories
                        SET name = :name,
                            color = :color,
                            order_index = :order_index,
                            is_active = true,
                            updated_at = now()
                        WHERE slug = :slug
                        """
                    ),
                    row,
                )

            return plan
    finally:
        await engine.dispose()


async def main() -> int:
    plan = await ensure_board_categories_seeded()
    print(
        "Board categories seed: "
        f"inserted={len(plan.to_insert)}, "
        f"updated={len(plan.to_update)}, "
        f"unchanged={plan.unchanged}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
