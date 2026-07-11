# Six Degree Bacon — task runner (Unix / CI).
# On Windows without `make`, run the underlying `uv` commands directly (see README).

.DEFAULT_GOAL := check
TOPIC ?= Roman Empire

.PHONY: install lint format typecheck test check validate discover clean

install:  ## Create the venv and install dev dependencies (writes uv.lock).
	uv sync --extra dev

lint:  ## Lint with ruff.
	uv run ruff check .

format:  ## Auto-format with ruff.
	uv run ruff format .

typecheck:  ## Static type check the package with mypy.
	uv run mypy sdb

test:  ## Run the test suite.
	uv run pytest

check: lint typecheck test  ## Lint + typecheck + test (the offline CI gate).

validate:  ## Network guard (ADR 0008): check every seed QID resolves. Run after editing seed.json.
	uv run sdb validate-qids

discover:  ## Discover a surprising path for TOPIC (e.g. `make discover TOPIC="Roman Empire"`).
	uv run sdb discover "$(TOPIC)"

clean:  ## Remove caches and build artifacts.
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info
