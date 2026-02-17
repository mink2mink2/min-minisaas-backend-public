"""Unit tests for board category seed planning."""

from scripts.seed_board_categories import DEFAULT_BOARD_CATEGORIES, build_seed_plan


def test_build_seed_plan_with_empty_existing() -> None:
    plan = build_seed_plan(existing_by_slug={})
    assert len(plan.to_insert) == len(DEFAULT_BOARD_CATEGORIES)
    assert len(plan.to_update) == 0
    assert plan.unchanged == 0


def test_build_seed_plan_updates_inactive_or_changed_rows() -> None:
    existing = {
        "free": {
            "name": "자유",
            "color": "#000000",
            "order_index": 1,
            "is_active": False,
        }
    }
    defaults = [
        {"name": "자유", "slug": "free", "color": "#3B82F6", "order_index": 10}
    ]
    plan = build_seed_plan(existing_by_slug=existing, defaults=defaults)
    assert len(plan.to_insert) == 0
    assert len(plan.to_update) == 1
    assert plan.unchanged == 0


def test_build_seed_plan_marks_unchanged_rows() -> None:
    existing = {
        "notice": {
            "name": "공지",
            "color": "#EF4444",
            "order_index": 40,
            "is_active": True,
        }
    }
    defaults = [
        {"name": "공지", "slug": "notice", "color": "#EF4444", "order_index": 40}
    ]
    plan = build_seed_plan(existing_by_slug=existing, defaults=defaults)
    assert len(plan.to_insert) == 0
    assert len(plan.to_update) == 0
    assert plan.unchanged == 1
