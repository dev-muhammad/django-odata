"""
Django app configuration for integration test support.
"""

from django.apps import AppConfig


class IntegrationSupportConfig(AppConfig):
    """Configuration for integration test support app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.integration.support"
    label = "integration_support"
    verbose_name = "Integration Test Support"
