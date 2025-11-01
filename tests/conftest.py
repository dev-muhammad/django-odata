"""
Pytest configuration for django-odata tests.

This file ensures proper test database setup for integration tests.
"""

import pytest
from django.conf import settings

# Configure Django settings for tests
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "tests.integration.support",
            "example.blog",
        ],
        SECRET_KEY="test-secret-key",
        USE_TZ=True,
    )

    import django

    django.setup()


@pytest.fixture
def blog_post_model():
    """Fixture providing the BlogPost model."""
    from example.blog.models import BlogPost

    return BlogPost


@pytest.fixture
def blog_post_queryset(blog_post_model):
    """Fixture providing a BlogPost QuerySet."""
    return blog_post_model.objects.all()


@pytest.fixture
def author_model():
    """Fixture providing the Author model."""
    from example.blog.models import Author

    return Author


@pytest.fixture
def category_model():
    """Fixture providing the Category model."""
    from example.blog.models import Category

    return Category
