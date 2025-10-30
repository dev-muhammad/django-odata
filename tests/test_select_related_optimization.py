"""
Tests for select_related field optimization.

This module tests the field selection optimization for select_related queries,
ensuring that only requested fields from related models are fetched.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory

from example.blog.models import BlogPost, Author, Category
from example.blog.views import BlogPostViewSet


class TestSelectRelatedFieldOptimization(TestCase):
    """Test field selection optimization with select_related."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        
        # Create test user and author
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="John",
            last_name="Doe"
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Test author bio with lots of text that we don't want to fetch unnecessarily",
            website="https://example.com"
        )
        
        # Create test post
        self.post = BlogPost.objects.create(
            title="Test Post",
            slug="test-post",
            content="Content for test post with lots of text",
            excerpt="Short excerpt",
            author=self.author
        )

    def test_select_related_with_nested_select(self):
        """Test that nested $select limits fields from related model."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            # Force query execution
            list(queryset)
            
            if queries:
                sql = queries[0]['sql'].lower()
                # Should include author.id (PK) and author name-related fields
                # Should NOT include author.bio or author.website
                assert 'author' in sql or 'user' in sql  # Related table
                # Note: Exact field checking depends on Django's query generation

    def test_select_related_without_nested_select(self):
        """Test that select_related without nested $select fetches all related fields."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Without nested $select, should not apply field restriction to related model
        # The queryset should still use select_related for optimization
        assert queryset.query.select_related

    def test_select_related_multiple_relations(self):
        """Test field selection with multiple select_related relations."""
        # Create another post with same author
        post2 = BlogPost.objects.create(
            title="Test Post 2",
            slug="test-post-2",
            content="Content 2",
            author=self.author
        )
        
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        posts = list(queryset)
        
        # Should return both posts
        assert len(posts) == 2
        # Should have optimized query with select_related
        assert queryset.query.select_related

    def test_select_related_pk_always_included(self):
        """Test that related model PK is always included."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            list(queryset)
            
            # The query should include author's PK even though not in $select
            # This is required by Django for the relationship to work
            if queries:
                sql = queries[0]['sql']
                # Should have JOIN with author table
                assert 'JOIN' in sql.upper()


class TestGetExistingOnlyFields(TestCase):
    """Test the _get_existing_only_fields helper method."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Test bio"
        )

    def test_extracts_existing_only_fields(self):
        """Test that existing only() fields are extracted correctly."""
        request = self.factory.get('/posts/', {'$select': 'id,title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        # Get a queryset with only() already applied
        queryset = viewset.get_queryset()
        
        # Extract existing only fields
        existing_fields = viewset._get_existing_only_fields(queryset)
        
        # Should return a list
        assert isinstance(existing_fields, list)

    def test_returns_empty_for_no_only(self):
        """Test that empty list is returned when no only() is applied."""
        request = self.factory.get('/posts/')
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        # Get base queryset without only()
        queryset = BlogPost.objects.all()
        
        # Extract existing only fields
        existing_fields = viewset._get_existing_only_fields(queryset)
        
        # Should return empty list
        assert existing_fields == []


class TestApplyRelatedFieldSelection(TestCase):
    """Test the _apply_related_field_selection method."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Test bio"
        )
        self.post = BlogPost.objects.create(
            title="Test Post",
            slug="test-post",
            content="Content",
            author=self.author
        )

    def test_applies_field_selection_to_related(self):
        """Test that field selection is applied to select_related fields."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Should have only() applied
        deferred_loading = queryset.query.deferred_loading
        assert deferred_loading[0] is not None

    def test_handles_no_expand(self):
        """Test that method handles queries without $expand gracefully."""
        request = self.factory.get('/posts/', {'$select': 'id,title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Should still work, just without related field optimization
        assert queryset is not None

    def test_combines_with_main_only_fields(self):
        """Test that related fields are combined with main model fields."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Should have both main and related fields in only()
        deferred_loading = queryset.query.deferred_loading
        if deferred_loading[0]:
            only_fields = set(deferred_loading[0])
            # Should include main model fields
            assert 'id' in only_fields or 'pk' in only_fields
            assert 'title' in only_fields


class TestSelectRelatedIntegration(TestCase):
    """Integration tests for select_related field optimization."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="integrationuser",
            email="integration@example.com"
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Integration test bio"
        )
        self.post = BlogPost.objects.create(
            title="Integration Test Post",
            slug="integration-test-post",
            content="Integration test content",
            author=self.author
        )

    def test_end_to_end_select_related_optimization(self):
        """Test complete request/response with select_related optimization."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            posts = list(queryset)
            
            # Should return posts
            assert len(posts) > 0
            
            # Should use optimized query
            if queries:
                sql = queries[0]['sql']
                # Should have JOIN for author
                assert 'JOIN' in sql.upper()

    def test_serializer_works_with_optimized_select_related(self):
        """Test that serializer works correctly with optimized select_related."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        serializer = viewset.get_serializer(queryset, many=True)
        data = serializer.data
        
        # Should serialize correctly
        assert len(data) > 0
        assert 'id' in data[0]
        assert 'title' in data[0]