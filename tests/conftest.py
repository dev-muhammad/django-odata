"""
Pytest configuration for django-odata tests.

This file ensures proper test database setup for integration tests.
"""

import pytest
from django.core.management import call_command
from django.test.utils import setup_test_environment, teardown_test_environment


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup):
    """
    Ensure Django test database is properly set up with migrations.

    This fixture runs automatically before any database-touching tests
    and ensures that:
    1. Test database is created
    2. All migrations are applied
    3. Required tables exist for integration tests
    """
    # The django_db_setup fixture from pytest-django already handles
    # creating the test database and running migrations automatically
    # This is just documentation of the process
    pass


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Allow all tests to access the database.

    This is needed because some tests might not be explicitly marked
    with @pytest.mark.django_db but still need database access.
    """
    pass
