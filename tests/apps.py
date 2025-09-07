"""
Django app configuration for unit tests.
"""

from django.apps import AppConfig


class TestsConfig(AppConfig):
    """Configuration for unit tests app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tests'
    label = 'tests'
    verbose_name = 'Unit Tests'
