from scripts.verify_schema import detect_schema_issues


def test_detect_schema_issues_when_schema_matches() -> None:
    required = {
        "blog_categories": {"id", "is_deleted"},
        "blog_posts": {"id", "is_deleted"},
    }
    existing = {
        "blog_categories": {"id", "is_deleted", "name"},
        "blog_posts": {"id", "is_deleted", "title"},
    }

    issues = detect_schema_issues(existing, required)

    assert issues == []


def test_detect_schema_issues_when_table_and_column_missing() -> None:
    required = {
        "blog_categories": {"id", "is_deleted", "name"},
        "blog_posts": {"id", "is_deleted"},
    }
    existing = {
        "blog_categories": {"id", "name"},
    }

    issues = detect_schema_issues(existing, required)

    assert "missing column: blog_categories.is_deleted" in issues
    assert "missing table: blog_posts" in issues
