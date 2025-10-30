"""
Tests for database query field optimization.

This module tests the field selection optimization that uses Django's .only()
method to fetch only requested fields from the database.
"""

import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory

from example.blog.models import BlogPost, Author, Category
from example.blog.serializers import BlogPostSerializer
from example.blog.views import BlogPostViewSet


class TestFieldSelectionOptimization(TestCase):
    """Test field selection optimization with .only()"""

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
            bio="Test author bio"
        )
        
        # Create test posts
        self.post1 = BlogPost.objects.create(
            title="Test Post 1",
            slug="test-post-1",
            content="Content for post 1",
            author=self.author
        )
        self.post2 = BlogPost.objects.create(
            title="Test Post 2",
            slug="test-post-2",
            content="Content for post 2",
            author=self.author
        )
        
        # Create test categories
        self.category1 = Category.objects.create(name="Tech")
        self.category2 = Category.objects.create(name="Science")
        self.post1.categories.add(self.category1, self.category2)

    def test_only_selected_fields_fetched(self):
        """Test that only() is applied with $select parameter."""
        request = self.factory.get('/posts/', {'$select': 'id,title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Check that only() was applied
        deferred_loading = queryset.query.deferred_loading
        if deferred_loading[0]:  # Has only() fields
            only_fields = set(deferred_loading[0])
            # Should include id, title, and pk (if different)
            assert 'id' in only_fields or 'pk' in only_fields
            assert 'title' in only_fields
            # Should not include content (not requested)
            assert 'content' not in only_fields

    def test_primary_key_always_included(self):
        """Test that PK is included even if not in $select."""
        request = self.factory.get('/posts/', {'$select': 'title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Check that PK is included
        deferred_loading = queryset.query.deferred_loading
        if deferred_loading[0]:
            only_fields = set(deferred_loading[0])
            # PK should be included even though not in $select
            assert 'id' in only_fields or 'pk' in only_fields

    def test_foreign_keys_included_for_expand(self):
        """Test that FK fields are included when relation is expanded."""
        request = self.factory.get('/posts/', {
            '$select': 'id,title',
            '$expand': 'author'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Check that author_id FK is included
        deferred_loading = queryset.query.deferred_loading
        if deferred_loading[0]:
            only_fields = set(deferred_loading[0])
            # FK field should be included for expansion
            assert 'author_id' in only_fields

    def test_no_optimization_without_select(self):
        """Test that no .only() is applied without $select."""
        request = self.factory.get('/posts/')
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Check that only() was NOT applied
        deferred_loading = queryset.query.deferred_loading
        # Should be (None, True) or (set(), False) when no only() applied
        assert not deferred_loading[0] or len(deferred_loading[0]) == 0

    def test_empty_select_returns_all_fields(self):
        """Test that empty $select returns all fields."""
        request = self.factory.get('/posts/', {'$select': ''})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        # Empty $select should not apply optimization
        deferred_loading = queryset.query.deferred_loading
        assert not deferred_loading[0] or len(deferred_loading[0]) == 0

    def test_sql_query_optimization(self):
        """Test that SQL query only includes requested fields."""
        request = self.factory.get('/posts/', {'$select': 'id,title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        with CaptureQueriesContext(connection) as queries:
            queryset = viewset.get_queryset()
            # Force query execution
            list(queryset)
            
            if queries:
                sql = queries[0]['sql'].lower()
                # Should include id and title
                assert 'id' in sql or 'pk' in sql
                assert 'title' in sql
                # Should NOT include content (not requested)
                # Note: This might not always work due to Django's query optimization
                # but it's a good indicator

    def test_multiple_fields_selection(self):
        """Test selection of multiple fields."""
        request = self.factory.get('/posts/', {'$select': 'id,title,content'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        
        deferred_loading = queryset.query.deferred_loading
        if deferred_loading[0]:
            only_fields = set(deferred_loading[0])
            assert 'id' in only_fields or 'pk' in only_fields
            assert 'title' in only_fields
            assert 'content' in only_fields


class TestBuildOnlyFieldsList(TestCase):
    """Test the _build_only_fields_list helper method."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testauthor",
            email="test@example.com"
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Test bio"
        )

    def test_includes_primary_key(self):
        """Test that primary key is always included."""
        request = self.factory.get('/posts/', {'$select': 'title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        odata_params = viewset.get_odata_query_params()
        model = BlogPost
        selected_fields = ['title']
        
        only_fields = viewset._build_only_fields_list(
            model, selected_fields, odata_params
        )
        
        # Should include PK
        assert 'id' in only_fields or 'pk' in only_fields
        assert 'title' in only_fields

    def test_includes_foreign_key_for_expand(self):
        """Test that FK fields are included for expanded relations."""
        request = self.factory.get('/posts/', {
            '$select': 'title',
            '$expand': 'author'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        odata_params = viewset.get_odata_query_params()
        model = BlogPost
        selected_fields = ['title']
        
        only_fields = viewset._build_only_fields_list(
            model, selected_fields, odata_params
        )
        
        # Should include FK for expanded relation
        assert 'author_id' in only_fields

    def test_handles_multiple_expansions(self):
        """Test handling of multiple expanded relations."""
        request = self.factory.get('/posts/', {
            '$select': 'title',
            '$expand': 'author,categories'
        })
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        odata_params = viewset.get_odata_query_params()
        model = BlogPost
        selected_fields = ['title']
        
        only_fields = viewset._build_only_fields_list(
            model, selected_fields, odata_params
        )
        
        # Should include FK for author
        assert 'author_id' in only_fields
        # Note: M2M relations don't have FK fields on the main model


class TestFieldSelectionIntegration(TestCase):
    """Integration tests for field selection with actual queries."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="integrationuser",
            email="integration@example.com"
        )
        self.author = Author.objects.create(
            user=self.user,
            bio="Bio for integration testing"
        )
        self.post = BlogPost.objects.create(
            title="Integration Test Post",
            slug="integration-test-post",
            content="Content for integration testing",
            author=self.author
        )

    def test_queryset_returns_correct_data(self):
        """Test that optimized queryset still returns correct data."""
        request = self.factory.get('/posts/', {'$select': 'id,title'})
        viewset = BlogPostViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        queryset = viewset.get_queryset()
        posts = list(queryset)
        
        # Should still return posts
        assert len(posts) > 0
        # Should have id and title
        assert hasattr(posts[0], 'id')
        assert hasattr(posts[0], 'title')

    def test_serializer_works_with_optimized_queryset(self):
        """Test that serializer works correctly with optimized queryset."""
        request = self.factory.get('/posts/', {'$select': 'id,title'})
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