"""Unit tests for DB bootstrap helpers."""

from scripts.bootstrap_db import build_db_urls


def test_build_db_urls_with_asyncpg_scheme() -> None:
    parts = build_db_urls(
        "postgresql+asyncpg://myuser:mypass@localhost:55432/minisaas_db"
    )

    assert parts.driverless_url == "postgresql://myuser:mypass@localhost:55432/minisaas_db"
    assert parts.database_name == "minisaas_db"
    assert parts.admin_url == "postgresql://myuser:mypass@localhost:55432/postgres"


def test_build_db_urls_requires_database_name() -> None:
    try:
        build_db_urls("postgresql+asyncpg://myuser:mypass@localhost:55432")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "database name" in str(exc)
