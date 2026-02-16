"""Seed default blog categories in an idempotent way.

Usage:
  .venv/bin/python scripts/seed_blog_categories.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


DEFAULT_BLOG_CATEGORIES: list[dict[str, Any]] = [
    {"name": "일상", "slug": "daily", "description": "일상 기록"},
    {"name": "개발", "slug": "dev", "description": "개발 메모"},
    {"name": "회고", "slug": "retrospective", "description": "회고/정리"},
    {"name": "공지", "slug": "notice", "description": "안내 및 공지"},
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
    rows = defaults or DEFAULT_BLOG_CATEGORIES
    to_insert: list[dict[str, Any]] = []
    to_update: list[dict[str, Any]] = []
    unchanged = 0

    for row in rows:
        existing = existing_by_slug.get(row["slug"])
        if not existing:
            to_insert.append(row)
            continue

        changed = (
            existing.get("name") != row["name"]
            or existing.get("description") != row["description"]
            or existing.get("is_active") is not True
        )
        if changed:
            to_update.append(row)
        else:
            unchanged += 1

    return SeedPlan(to_insert=to_insert, to_update=to_update, unchanged=unchanged)


async def ensure_blog_categories_seeded() -> SeedPlan:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.begin() as conn:
            rows_result = await conn.execute(
                text(
                    """
                    SELECT slug, name, description, is_active
                    FROM blog_categories
                    """
                )
            )
            existing_by_slug: dict[str, dict[str, Any]] = {
                row.slug: {
                    "name": row.name,
                    "description": row.description,
                    "is_active": row.is_active,
                }
                for row in rows_result.fetchall()
            }

            plan = build_seed_plan(existing_by_slug)

            for row in plan.to_insert:
                insert_row = {"id": str(uuid.uuid4()), **row}
                await conn.execute(
                    text(
                        """
                        INSERT INTO blog_categories
                            (id, name, slug, description, is_active)
                        VALUES
                            (:id, :name, :slug, :description, true)
                        """
                    ),
                    insert_row,
                )

            for row in plan.to_update:
                await conn.execute(
                    text(
                        """
                        UPDATE blog_categories
                        SET name = :name,
                            description = :description,
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
    plan = await ensure_blog_categories_seeded()
    print(
        "Blog categories seed: "
        f"inserted={len(plan.to_insert)}, "
        f"updated={len(plan.to_update)}, "
        f"unchanged={plan.unchanged}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
