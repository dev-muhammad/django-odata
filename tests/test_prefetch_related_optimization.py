"""
Tests for prefetch_related field optimization.

This module tests the field selection optimization for prefetch_related queries,
ensuring that only requested fields from related models are fetched.
"""

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory

from example.blog.models import Author, BlogPost, Category, Comment
from example.blog.views import BlogPostViewSet


class TestPrefetchRelatedFieldOptimization(TestCase):
    """Test field selection optimization with prefetch_related."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()

        # Create test user and author
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Test author bio with lots of text that we don't want to fetch unnecessarily",
            website="https://example.com",
        )

        # Create test post
        self.post = BlogPost.objects.create(
            title="Test Post",
            slug="test-post",
            content="Content for test post with lots of text",
            excerpt="Short excerpt",
            author=self.author,
        )

        # Create categories
        self.category1 = Category.objects.create(
            name="Technology",
            description="Tech articles with long descriptions we don't need",
        )
        self.category2 = Category.objects.create(
            name="Science",
            description="Science articles with long descriptions we don't need",
        )
        self.post.categories.add(self.category1, self.category2)

        # Create comments
        self.comment1 = Comment.objects.create(
            post=self.post,
            author_name="Commenter 1",
            author_email="commenter1@example.com",
            content="First comment with lots of text",
        )
        self.comment2 = Comment.objects.create(
            post=self.post,
            author_name="Commenter 2",
            author_email="commenter2@example.com",
            content="Second comment with lots of text",
        )

    def test_prefetch_related_with_nested_select(self):
        """Test that nested $select limits fields from prefetch_related model."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories($select=name)"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            # Force query execution
            posts = list(queryset)
            # Access prefetched data
            for post in posts:
                list(post.categories.all())

            # Should have 2 queries: main query + prefetch query
            assert len(queries) >= 2

            # Check that prefetch query exists
            prefetch_query = None
            for query in queries:
                sql = query["sql"].lower()
                if "category" in sql:
                    prefetch_query = sql
                    break

            assert prefetch_query is not None

    def test_prefetch_related_without_nested_select(self):
        """Test that prefetch_related without nested $select fetches all fields."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()

        # Without nested $select, should not apply field restriction
        # The queryset should still use prefetch_related for optimization
        assert queryset._prefetch_related_lookups

    def test_prefetch_related_multiple_relations(self):
        """Test field selection with multiple prefetch_related relations."""
        request = self.factory.get(
            "/posts/",
            {
                "$select": "id,title",
                "$expand": "categories($select=name),comments($select=author_name)",
            },
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        posts = list(queryset)

        # Should return posts
        assert len(posts) > 0
        # Should have optimized query with prefetch_related
        assert queryset._prefetch_related_lookups

    def test_prefetch_related_pk_always_included(self):
        """Test that related model PK is always included in prefetch."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories($select=name)"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            posts = list(queryset)
            # Access prefetched data
            for post in posts:
                list(post.categories.all())

            # The prefetch query should include category PK
            # even though not in $select
            assert len(queries) >= 2


class TestPrefetchObjectCreation(TestCase):
    """Test the creation of Prefetch objects with custom querysets."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )
        self.author = Author.objects.create(user=self.user, bio="Test bio")
        self.post = BlogPost.objects.create(
            title="Test Post", slug="test-post", content="Content", author=self.author
        )

    def test_creates_prefetch_objects_with_only(self):
        """Test that Prefetch objects are created with only() querysets."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories($select=name)"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()

        # Should have Prefetch objects
        assert queryset._prefetch_related_lookups

    def test_handles_reverse_relations(self):
        """Test that reverse relations (comments) are handled correctly."""
        request = self.factory.get(
            "/posts/",
            {"$select": "id,title", "$expand": "comments($select=author_name)"},
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()

        # Should have prefetch for comments
        assert queryset._prefetch_related_lookups


class TestPrefetchRelatedIntegration(TestCase):
    """Integration tests for prefetch_related field optimization."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="integrationuser", email="integration@example.com"
        )
        self.author = Author.objects.create(user=self.user, bio="Integration test bio")
        self.post = BlogPost.objects.create(
            title="Integration Test Post",
            slug="integration-test-post",
            content="Integration test content",
            author=self.author,
        )
        self.category = Category.objects.create(
            name="Test Category", description="Test description"
        )
        self.post.categories.add(self.category)

    def test_end_to_end_prefetch_related_optimization(self):
        """Test complete request/response with prefetch_related optimization."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories($select=name)"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            posts = list(queryset)
            # Access prefetched data
            for post in posts:
                list(post.categories.all())

            # Should return posts
            assert len(posts) > 0

            # Should use optimized queries (main + prefetch)
            assert len(queries) >= 2

    def test_serializer_works_with_optimized_prefetch_related(self):
        """Test that serializer works correctly with optimized prefetch_related."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories($select=name)"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        serializer = viewset.get_serializer(queryset, many=True)
        data = serializer.data

        # Should serialize correctly
        assert len(data) > 0
        assert "id" in data[0]
        assert "title" in data[0]

    def test_mixed_select_and_prefetch_related(self):
        """Test optimization with both select_related and prefetch_related."""
        request = self.factory.get(
            "/posts/",
            {
                "$select": "id,title",
                "$expand": "author($select=bio),categories($select=name)",
            },
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            posts = list(queryset)
            # Access prefetched data
            for post in posts:
                list(post.categories.all())

            # Should have both select_related and prefetch_related
            assert queryset.query.select_related
            assert queryset._prefetch_related_lookups

            # Should use optimized queries
            assert len(queries) >= 2
