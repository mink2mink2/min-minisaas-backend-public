"""Schema guard for runtime-critical tables.

Usage:
  .venv/bin/python scripts/verify_schema.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings


REQUIRED_COLUMNS: dict[str, set[str]] = {
    "board_categories": {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "name",
        "slug",
        "color",
        "order_index",
        "is_active",
    },
    "blog_categories": {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "name",
        "slug",
        "description",
        "is_active",
    },
    "blog_posts": {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "author_id",
        "title",
        "slug",
        "content",
        "excerpt",
        "featured_image_url",
        "category_id",
        "tags",
        "is_published",
        "published_at",
        "view_count",
        "like_count",
        "comment_count",
    },
    "blog_likes": {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "post_id",
        "user_id",
    },
    "blog_subscriptions": {
        "id",
        "created_at",
        "updated_at",
        "is_deleted",
        "subscriber_id",
        "author_id",
    },
}

REQUIRED_MIN_ROWS: dict[str, int] = {
    "board_categories": 1,
    "blog_categories": 1,
}


def normalized_pg_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


def detect_schema_issues(
    existing_columns: dict[str, set[str]],
    required_columns: dict[str, set[str]],
) -> list[str]:
    issues: list[str] = []
    for table_name in sorted(required_columns):
        if table_name not in existing_columns:
            issues.append(f"missing table: {table_name}")
            continue
        missing = sorted(required_columns[table_name] - existing_columns[table_name])
        for column_name in missing:
            issues.append(f"missing column: {table_name}.{column_name}")
    return issues


def detect_seed_issues(
    row_counts: dict[str, int],
    required_min_rows: dict[str, int],
) -> list[str]:
    issues: list[str] = []
    for table_name, min_rows in sorted(required_min_rows.items()):
        current = row_counts.get(table_name, 0)
        if current < min_rows:
            issues.append(
                f"seed data missing: {table_name} has {current} row(s), requires >= {min_rows}"
            )
    return issues


async def load_existing_columns(database_url: str) -> dict[str, set[str]]:
    conn = await asyncpg.connect(normalized_pg_url(database_url))
    try:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            """
        )
    finally:
        await conn.close()

    columns: dict[str, set[str]] = {}
    for row in rows:
        table_name = row["table_name"]
        column_name = row["column_name"]
        columns.setdefault(table_name, set()).add(column_name)
    return columns


async def load_row_counts(database_url: str, table_names: set[str]) -> dict[str, int]:
    conn = await asyncpg.connect(normalized_pg_url(database_url))
    counts: dict[str, int] = {}
    try:
        for table_name in sorted(table_names):
            value = await conn.fetchval(f"SELECT COUNT(*)::int FROM {table_name}")
            counts[table_name] = int(value or 0)
    finally:
        await conn.close()
    return counts


async def main() -> int:
    existing_columns = await load_existing_columns(settings.DATABASE_URL)
    issues = detect_schema_issues(existing_columns, REQUIRED_COLUMNS)
    if issues:
        print("SCHEMA VERIFY FAIL")
        for issue in issues:
            print(f"- {issue}")
        print(
            "Action: run '.venv/bin/alembic upgrade head' and re-run verify_schema.py"
        )
        return 1

    row_counts = await load_row_counts(
        settings.DATABASE_URL,
        set(REQUIRED_MIN_ROWS.keys()),
    )
    seed_issues = detect_seed_issues(row_counts, REQUIRED_MIN_ROWS)

    if seed_issues:
        print("SCHEMA VERIFY FAIL")
        for issue in seed_issues:
            print(f"- {issue}")
        print(
            "Action: run '.venv/bin/python scripts/seed_board_categories.py' and "
            "'.venv/bin/python scripts/seed_blog_categories.py', then re-run verify_schema.py"
        )
        return 1

    print("SCHEMA VERIFY PASS: required tables/columns are present")
    print(
        "SEED VERIFY PASS: "
        f"board_categories={row_counts['board_categories']}, "
        f"blog_categories={row_counts['blog_categories']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
