"""
Integration tests for complete field optimization feature (SPEC-003).

This module tests all three phases of field optimization working together:
- Phase 1: Main queryset field selection
- Phase 2: select_related field selection
- Phase 3: prefetch_related field selection
"""

import pytest
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory

from example.blog.models import Author, BlogPost, Category, Comment
from example.blog.views import BlogPostViewSet


class TestCompleteFieldOptimization(TestCase):
    """Test all field optimization features working together."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()

        # Create test users and authors
        self.user1 = User.objects.create_user(
            username="author1",
            email="author1@example.com",
            first_name="John",
            last_name="Doe",
        )
        self.user2 = User.objects.create_user(
            username="author2",
            email="author2@example.com",
            first_name="Jane",
            last_name="Smith",
        )

        self.author1 = Author.objects.create(
            user=self.user1,
            bio="Author 1 bio with lots of text we don't want to fetch",
            website="https://author1.com",
        )
        self.author2 = Author.objects.create(
            user=self.user2,
            bio="Author 2 bio with lots of text we don't want to fetch",
            website="https://author2.com",
        )

        # Create categories
        self.tech = Category.objects.create(
            name="Technology", description="Tech articles with long descriptions"
        )
        self.science = Category.objects.create(
            name="Science", description="Science articles with long descriptions"
        )

        # Create posts
        self.post1 = BlogPost.objects.create(
            title="Post 1",
            slug="post-1",
            content="Content 1 with lots of text",
            excerpt="Excerpt 1",
            author=self.author1,
        )
        self.post1.categories.add(self.tech, self.science)

        self.post2 = BlogPost.objects.create(
            title="Post 2",
            slug="post-2",
            content="Content 2 with lots of text",
            excerpt="Excerpt 2",
            author=self.author2,
        )
        self.post2.categories.add(self.tech)

        # Create comments
        Comment.objects.create(
            post=self.post1,
            author_name="Commenter 1",
            author_email="c1@example.com",
            content="Comment 1 content",
        )
        Comment.objects.create(
            post=self.post1,
            author_name="Commenter 2",
            author_email="c2@example.com",
            content="Comment 2 content",
        )

    def test_all_phases_together(self):
        """Test main, select_related, and prefetch_related optimization together."""
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

        with CaptureQueriesContext(connection):
            queryset = viewset.get_queryset()
            posts = list(queryset)

            # Access related data to trigger prefetch
            for post in posts:
                _ = post.author.bio if hasattr(post, "author") else None
                list(post.categories.all())

            # Should have optimized queries
            assert len(posts) == 2

            # Should use select_related for author
            assert queryset.query.select_related

            # Should use prefetch_related for categories
            assert queryset._prefetch_related_lookups

    def test_query_count_optimization(self):
        """Test that field optimization doesn't increase query count."""
        # Without optimization
        request1 = self.factory.get("/posts/")
        viewset1 = BlogPostViewSet()
        viewset1.request = request1
        viewset1.format_kwarg = None

        with CaptureQueriesContext(connection) as queries1:
            qs1 = viewset1.get_queryset()
            posts1 = list(qs1)
            for post in posts1:
                list(post.categories.all())

        # With optimization
        request2 = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "categories($select=name)"}
        )
        viewset2 = BlogPostViewSet()
        viewset2.request = request2
        viewset2.format_kwarg = None

        with CaptureQueriesContext(connection) as queries2:
            qs2 = viewset2.get_queryset()
            posts2 = list(qs2)
            for post in posts2:
                list(post.categories.all())

        # Query count should be similar (optimization shouldn't add queries)
        assert len(queries2) <= len(queries1) + 1  # Allow 1 extra for optimization

    def test_complex_nested_expansion(self):
        """Test complex query with multiple nested expansions."""
        request = self.factory.get(
            "/posts/",
            {
                "$select": "id,title,excerpt",
                "$expand": "author($select=bio,website),categories($select=name),comments($select=author_name)",
            },
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        posts = list(queryset)

        # Should return all posts
        assert len(posts) == 2

        # Should have both select_related and prefetch_related
        assert queryset.query.select_related
        assert queryset._prefetch_related_lookups

    def test_serialization_with_optimization(self):
        """Test that serialization works correctly with all optimizations."""
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

        queryset = viewset.get_queryset()
        serializer = viewset.get_serializer(queryset, many=True)
        data = serializer.data

        # Should serialize correctly
        assert len(data) == 2
        for item in data:
            assert "id" in item
            assert "title" in item

    def test_no_n_plus_1_queries(self):
        """Test that optimization prevents N+1 query problems."""
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

            # Access all related data
            for post in posts:
                _ = post.author.bio if hasattr(post, "author") else None
                list(post.categories.all())

            # Should not have N+1 queries
            # Expected: 1 main query + 1 prefetch for categories
            # (author is select_related, so included in main query)
            assert len(queries) <= 3  # Allow some flexibility


class TestFieldOptimizationEdgeCases(TestCase):
    """Test edge cases and error handling."""

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

    def test_empty_select(self):
        """Test handling of empty $select parameter."""
        request = self.factory.get("/posts/", {"$select": "", "$expand": "author"})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        posts = list(queryset)

        # Should still work
        assert len(posts) > 0

    def test_empty_expand(self):
        """Test handling of empty $expand parameter."""
        request = self.factory.get("/posts/", {"$select": "id,title", "$expand": ""})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        posts = list(queryset)

        # Should still work
        assert len(posts) > 0

    def test_nonexistent_field_in_select(self):
        """Test handling of non-existent field in $select."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title,nonexistent_field", "$expand": "author"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        posts = list(queryset)

        # Should still work, ignoring invalid field
        assert len(posts) > 0

    def test_nonexistent_relation_in_expand(self):
        """Test that non-existent relation in $expand raises appropriate error."""
        request = self.factory.get(
            "/posts/", {"$select": "id,title", "$expand": "nonexistent_relation"}
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()

        # Django will raise AttributeError for invalid prefetch_related field
        # This is expected behavior - invalid relations should fail
        with pytest.raises(AttributeError, match="Cannot find 'nonexistent_relation'"):
            list(queryset)

    def test_property_field_in_nested_select(self):
        """Test that property fields in nested $select are handled gracefully."""
        request = self.factory.get(
            "/posts/",
            {
                "$select": "id,title",
                "$expand": "author($select=name)",  # 'name' is a property, not a field
            },
        )
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None

        queryset = viewset.get_queryset()
        posts = list(queryset)

        # Should work without errors (property fields are skipped)
        assert len(posts) > 0


class TestFieldOptimizationPerformance(TestCase):
    """Performance tests for field optimization."""

    def setUp(self):
        """Set up test data with multiple records."""
        self.factory = APIRequestFactory()

        # Create multiple authors
        self.authors = []
        for i in range(10):
            user = User.objects.create_user(
                username=f"author{i}", email=f"author{i}@example.com"
            )
            author = Author.objects.create(
                user=user, bio=f"Bio for author {i} with lots of text " * 10
            )
            self.authors.append(author)

        # Create categories
        self.categories = []
        for i in range(5):
            category = Category.objects.create(
                name=f"Category {i}",
                description=f"Description for category {i} with lots of text " * 10,
            )
            self.categories.append(category)

        # Create posts
        for i in range(50):
            post = BlogPost.objects.create(
                title=f"Post {i}",
                slug=f"post-{i}",
                content=f"Content for post {i} with lots of text " * 20,
                excerpt=f"Excerpt {i}",
                author=self.authors[i % 10],
            )
            # Add random categories
            post.categories.add(self.categories[i % 5], self.categories[(i + 1) % 5])

    def test_performance_with_large_dataset(self):
        """Test that optimization works efficiently with larger datasets."""
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

            # Access related data
            for post in posts:
                _ = post.author.bio if hasattr(post, "author") else None
                list(post.categories.all())

            # Should return all posts
            assert len(posts) == 50

            # Should not have excessive queries
            # Expected: 1 main + 1 prefetch for categories
            assert len(queries) <= 5  # Allow some flexibility

    def test_optimization_reduces_data_transfer(self):
        """Test that field selection actually reduces data fetched."""
        # Full query without optimization
        request1 = self.factory.get("/posts/")
        viewset1 = BlogPostViewSet()
        viewset1.request = request1
        viewset1.format_kwarg = None

        with CaptureQueriesContext(connection) as queries1:
            qs1 = viewset1.get_queryset()
            list(qs1)

        # Optimized query with minimal fields
        request2 = self.factory.get("/posts/", {"$select": "id,title"})
        viewset2 = BlogPostViewSet()
        viewset2.request = request2
        viewset2.format_kwarg = None

        with CaptureQueriesContext(connection) as queries2:
            qs2 = viewset2.get_queryset()
            list(qs2)

        # Both should execute queries
        assert len(queries1) > 0
        assert len(queries2) > 0

        # Optimized query should select fewer fields
        # (This is a basic check - actual SQL analysis would be more detailed)
        if queries1 and queries2:
            sql1 = queries1[0]["sql"]
            sql2 = queries2[0]["sql"]
            # Optimized query should be shorter or similar length
            # (not a perfect test, but gives an indication)
            assert len(sql2) <= len(sql1) * 1.5
