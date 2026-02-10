.PHONY: install install-dev test test-one lint format clean run sync

# Install uv if not already installed
uv-check:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

# Install production dependencies
install: uv-check
	uv sync --no-dev

# Install development dependencies
install-dev: uv-check
	uv sync

# Sync dependencies (update lock file)
sync: uv-check
	uv sync --upgrade

# Run tests (ensures dev deps are installed)
test: uv-check install-dev
	uv run --extra dev python -m pytest tests/ -v --cov=. --cov-report=html

# Run a single test file or specific test
# Usage: make test-one TEST=tests/test_policy_registry.py::TestPolicyRegistry::test_register_policy
test-one: uv-check install-dev
	uv run --extra dev python -m pytest $(TEST) -v

# Lint code
lint: uv-check
	uv run --extra dev python -m ruff check .
	uv run --extra dev python -m mypy .

# Format code
format: uv-check
	uv run --extra dev python -m black .
	uv run --extra dev python -m ruff check --fix .

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/

# Run the application
run: uv-check
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Setup database migrations
migrate: uv-check
	uv run alembic upgrade head

# Create new migration
migrate-create: uv-check
	uv run alembic revision --autogenerate -m "$(msg)"

