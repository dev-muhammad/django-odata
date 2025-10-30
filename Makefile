.PHONY: help venv venv-activate install install-dev test test-unit test-integration test-coverage clean lint format example-setup example-run example-clean docs

# Default target
help:
	@echo "Django OData - Development Commands"
	@echo ""
	@echo "Environment Setup:"
	@echo "  make venv             Create Python virtual environment"
	@echo "  make venv-activate    Show command to activate venv"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install package in production mode"
	@echo "  make install-dev      Install package with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests (unit + integration)"
	@echo "  make test-unit        Run only unit tests (fast)"
	@echo "  make test-integration Run only integration tests"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run code linters (flake8, mypy)"
	@echo "  make format           Format code with black and isort"
	@echo ""
	@echo "Example Application:"
	@echo "  make example-setup    Set up example application database"
	@echo "  make example-run      Run example application server"
	@echo "  make example-clean    Clean example application database"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove build artifacts and cache files"
	@echo "  make docs             Build documentation"
	@echo ""
	@echo "Quick Start:"
	@echo "  1. make venv          # Create virtual environment"
	@echo "  2. source venv/bin/activate  # Activate it"
	@echo "  3. make dev-setup     # Install deps and setup example"
	@echo "  4. make example-run   # Run the server"

# Virtual Environment
venv:
	@echo "Creating Python virtual environment..."
	python3 -m venv venv
	@echo ""
	@echo "✅ Virtual environment created!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. source venv/bin/activate"
	@echo "  2. make dev-setup"

venv-activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source venv/bin/activate"
	@echo ""
	@echo "To deactivate it later, run:"
	@echo "  deactivate"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	DJANGO_SETTINGS_MODULE=tests.settings pytest tests/ --ignore=tests/performance/ -v

test-unit:
	DJANGO_SETTINGS_MODULE=tests.settings pytest tests/ --ignore=tests/performance/ --ignore=tests/integration/ -v

test-integration:
	DJANGO_SETTINGS_MODULE=tests.settings pytest tests/integration/ -v

test-coverage:
	DJANGO_SETTINGS_MODULE=tests.settings pytest tests/ --ignore=tests/performance/ --cov=django_odata --cov-report=html --cov-report=term

# Code Quality
lint:
	@echo "Running flake8..."
	-flake8 django_odata tests
	@echo "Running mypy..."
	-mypy django_odata

format:
	@echo "Running black..."
	black django_odata tests
	@echo "Running isort..."
	isort django_odata tests

# Example Application
example-setup:
	@echo "Setting up example application..."
	cd example && python manage.py migrate --run-syncdb
	@echo ""
	@echo "Creating test user (test@test.com / test)..."
	cd example && python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(email='test@test.com').exists() or User.objects.create_superuser('test', 'test@test.com', 'test')"
	@echo ""
	@echo "Example application ready!"
	@echo "  - Test user: test@test.com / test"
	@echo "  - Admin: http://localhost:8000/admin/"
	@echo "  - OData: http://localhost:8000/odata/posts/"

example-run:
	@echo "Starting example application server..."
	@echo ""
	@echo "Available endpoints:"
	@echo "  - OData Posts: http://localhost:8000/odata/posts/"
	@echo "  - Django Admin: http://localhost:8000/admin/"
	@echo ""
	@echo "Test credentials: test@test.com / test"
	@echo ""
	cd example && python manage.py runserver

example-clean:
	@echo "Cleaning example application database..."
	rm -f example/db.sqlite3
	@echo "Database removed. Run 'make example-setup' to recreate."

# Maintenance
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Clean complete!"

docs:
	@echo "Building documentation..."
	@echo "Documentation build not yet configured"

# Development workflow shortcuts
dev-setup: install-dev example-setup
	@echo ""
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  make example-run    # Start the example server"
	@echo "  make test-unit      # Run unit tests"
	@echo ""
	@echo "Credentials: test@test.com / test"

quick-test: test-unit
	@echo ""
	@echo "Quick unit tests complete!"

full-test: test-coverage
	@echo ""
	@echo "Full test suite with coverage complete!"
	@echo "Open htmlcov/index.html to view coverage report"