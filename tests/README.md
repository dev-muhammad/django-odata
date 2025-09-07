# Django OData Test Suite

This directory contains the test suite for the django-odata package, organized into unit tests and integration tests with their support files properly separated.

## Test Structure

### Unit Tests (tests/)
These tests focus on testing individual components, but they still require Django setup:

- `test_utils.py` - Tests utility functions and query parsing
- `test_serializers.py` - Tests OData serializer classes
- `test_mixins.py` - Tests OData mixin functionality
- `test_viewsets.py` - Tests OData viewset classes

### Integration Tests (tests/integration/)
These tests verify that multiple components work together correctly and require full database setup:

- `test_odata_integration.py` - Integration tests using existing infrastructure
- `test_odata_expressions.py` - Tests OData expressions with database models
- `test_odata_performance.py` - Performance tests with large datasets
- `test_odata_comprehensive.py` - End-to-end comprehensive tests

### Integration Support (tests/integration/support/)
Support files specifically for integration tests:

- `models.py` - Test models for integration tests
- `settings.py` - Django settings for integration tests
- `urls.py` - URL configuration for API tests
- `apps.py` - Django app configuration
- `migrations/` - Database migrations for test models

## Running Tests

**Important**: All tests require the Django settings module to be specified explicitly.

### Run All Tests
```bash
DJANGO_SETTINGS_MODULE=tests.integration.support.settings pytest tests/
```

### Run Only Unit Tests (Faster)
```bash
DJANGO_SETTINGS_MODULE=tests.integration.support.settings pytest tests/test_utils.py tests/test_serializers.py tests/test_mixins.py tests/test_viewsets.py
```

### Run Only Integration Tests
```bash
DJANGO_SETTINGS_MODULE=tests.integration.support.settings pytest tests/integration/
```

### Run Specific Test Categories
```bash
# Run unit tests only
DJANGO_SETTINGS_MODULE=tests.integration.support.settings pytest tests/ --ignore=tests/integration/

# Run integration tests only  
DJANGO_SETTINGS_MODULE=tests.integration.support.settings pytest tests/integration/

# Run with coverage
DJANGO_SETTINGS_MODULE=tests.integration.support.settings pytest tests/ --cov=django_odata --cov-report=term-missing
```

### Alternative: Set Environment Variable
```bash
# Set once in your shell session
export DJANGO_SETTINGS_MODULE=tests.integration.support.settings

# Then run tests normally
pytest tests/
pytest tests/integration/
pytest tests/test_utils.py
```

## Test Configuration

- **Django Settings**: Tests use `tests.integration.support.settings` module
- **Test Database**: In-memory SQLite database for integration tests
- **Test Models**: Defined in `tests/integration/support/models.py`
- **URL Configuration**: `tests/integration/support/urls.py` for API endpoint tests
- **Django App**: `tests.integration.support` (configured via apps.py)

## Database Migrations in Tests

### How Test Database Setup Works

1. **pytest-django** automatically creates a test database for each test run
2. **Migrations are applied automatically** during test database creation
3. **Tables are created** from the migration files in `tests/integration/support/migrations/`
4. **Database is destroyed** after tests complete

### In CI Pipeline

The CI workflow ensures proper database setup:

```yaml
- name: Check Django setup and run migrations
  env:
    DJANGO_SETTINGS_MODULE: tests.integration.support.settings
  run: |
    # Verify Django can detect our test apps and migrations
    python -m django check --settings=tests.integration.support.settings
    python -m django showmigrations --settings=tests.integration.support.settings

- name: Run tests
  env:
    DJANGO_SETTINGS_MODULE: tests.integration.support.settings
  run: |
    pytest --cov=django_odata --cov-report=xml --cov-report=term-missing
```

### Migration Files

Integration test migrations are stored in:
- `tests/integration/support/migrations/0001_initial.py`

These migrations create all necessary tables:
- `integration_support_odatatestmodel`
- `integration_support_performancetestmodel`
- `integration_support_performancerelatedmodel`
- And other test model tables

## Test Models

The test suite includes several models for comprehensive testing:

- `ODataTestModel` - Main model with various field types
- `ODataRelatedModel` - Related model for testing navigation properties
- `PerformanceTestModel` - Model for performance testing with indexes
- `SerializerTestModel` - Model for serializer-specific tests
- `ViewSetTestModel` - Model for viewset-specific tests
- `UtilsTestModel` - Model for utility function tests
- `MixinTestModel` - Model for mixin tests

## Adding New Tests

### Unit Tests
Add new unit tests to the appropriate existing file or create a new `test_*.py` file in the main `tests/` directory.

### Integration Tests
Add new integration tests to the `tests/integration/` directory. Make sure to:
1. Import models from `..models` (note the double dots)
2. Use `TestCase` or `TransactionTestCase` for database tests
3. Use `APITestCase` for API endpoint tests

## Migration Management

Test models are managed through Django migrations in the `tests/migrations/` directory. To create new migrations:

```bash
python -m django makemigrations tests --settings=tests.settings
python -m django migrate --settings=tests.settings
```
