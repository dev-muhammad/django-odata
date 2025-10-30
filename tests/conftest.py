"""
Pytest configuration for django-odata tests.

This file ensures proper test database setup for integration tests.
"""

import pytest
from django.core.management import call_command
from django.test.utils import setup_test_environment, teardown_test_environment
