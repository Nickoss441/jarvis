PYTHON ?= python3
PYTEST ?= pytest
VENV ?= venv

.PHONY: setup run lint format test audit-verify verify-audit orb-audit todos-automate verify

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

run:
	$(PYTHON) -m jarvis

lint:
	@if $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
		echo "Running ruff lint checks..."; \
		$(PYTHON) -m ruff check jarvis tests; \
	else \
		echo "ruff not installed; running syntax checks via compileall"; \
		$(PYTHON) -m compileall -q jarvis tests; \
	fi

format:
	@if $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
		echo "Running ruff formatter..."; \
		$(PYTHON) -m ruff format jarvis tests; \
	elif $(PYTHON) -m black --version >/dev/null 2>&1; then \
		echo "Running black formatter..."; \
		$(PYTHON) -m black jarvis tests; \
	else \
		echo "No formatter installed (ruff/black). Skipping format target."; \
	fi

test:
	$(PYTEST) -q

audit-verify:
	$(PYTHON) -m jarvis audit-verify

verify-audit: audit-verify

orb-audit:
	$(PYTHON) scripts/orb_task_automation.py

todos-automate:
	$(PYTHON) scripts/automate_todos.py

verify: lint test verify-audit orb-audit
