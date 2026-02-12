PYTHON := .venv/bin/python
ALEMBIC := .venv/bin/alembic
PYTEST := .venv/bin/pytest

.PHONY: bootstrap migrate verify setup test-bootstrap

bootstrap:
	$(PYTHON) scripts/bootstrap_db.py

migrate:
	$(ALEMBIC) upgrade head

verify:
	$(PYTHON) scripts/verify_runtime.py

setup: bootstrap migrate verify
	@echo "Setup complete"

test-bootstrap:
	$(PYTEST) -q tests/test_bootstrap_db.py
