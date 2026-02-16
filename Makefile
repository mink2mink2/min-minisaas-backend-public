PYTHON := .venv/bin/python
ALEMBIC := .venv/bin/alembic
PYTEST := .venv/bin/pytest

.PHONY: bootstrap migrate seed-categories verify setup test-bootstrap test-seed

bootstrap:
	$(PYTHON) scripts/bootstrap_db.py

migrate:
	$(ALEMBIC) upgrade head

seed-categories:
	$(PYTHON) scripts/seed_board_categories.py

verify:
	$(PYTHON) scripts/verify_runtime.py

setup: bootstrap migrate seed-categories verify
	@echo "Setup complete"

test-bootstrap:
	$(PYTEST) -q tests/test_bootstrap_db.py

test-seed:
	$(PYTEST) -q tests/test_seed_board_categories.py
