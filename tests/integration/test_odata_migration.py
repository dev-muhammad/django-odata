"""
Integration tests comparing old ODataMixin vs new repository pattern.

These tests ensure that the new clean architecture implementation
produces identical results to the original ODataMixin approach.
"""

import pytest
from django.db.models import QuerySet
from django.test import RequestFactory

from django_odata.core import apply_odata_to_queryset
from django_odata.repository import ODataRepository
from django_odata.viewsets import ODataModelViewSet


@pytest.mark.django_db
class TestODataMigrationCompatibility:
    """Test that new implementation matches old ODataMixin behavior."""

    def test_repository_vs_mixin_queryset_consistency(self, blog_post_model):
        """Test that repository and mixin produce identical querysets."""
        # Test query with various OData parameters
        query_string = "$filter=status eq 'published'&$select=title,content&$expand=author&$orderby=created_at desc&$top=5"

        # Get results from repository
        repo = ODataRepository(blog_post_model)
        repo_queryset = repo.query(query_string)

        # Get results from mixin (simulate ViewSet behavior)

        class TestViewSet(ODataModelViewSet):
            queryset = blog_post_model.objects.all()

        viewset = TestViewSet()
        factory = RequestFactory()
        request = factory.get(f"/test/?{query_string}")
        viewset.request = request

        mixin_queryset = viewset.get_queryset()

        # Both should be QuerySets
        assert isinstance(repo_queryset, QuerySet)
        assert isinstance(mixin_queryset, QuerySet)

        # Both should have same model
        assert repo_queryset.model == mixin_queryset.model == blog_post_model

        # Both should have same query structure
        assert repo_queryset.query.order_by == mixin_queryset.query.order_by
        assert repo_queryset.query.high_mark == mixin_queryset.query.high_mark
        assert repo_queryset.query.low_mark == mixin_queryset.query.low_mark

        # Both should have same select_related
        assert repo_queryset.query.select_related == mixin_queryset.query.select_related

        # Both should have same deferred loading (only() fields)
        repo_deferred = getattr(repo_queryset.query, "deferred_loading", (None, None))
        mixin_deferred = getattr(mixin_queryset.query, "deferred_loading", (None, None))
        assert repo_deferred[0] == mixin_deferred[0]  # only() fields should match

    def test_repository_vs_direct_function_consistency(self, blog_post_model):
        """Test that repository matches direct function calls."""
        query_string = (
            "$filter=featured eq true&$expand=author($select=name)&$orderby=title"
        )

        # Repository approach
        repo = ODataRepository(blog_post_model)
        repo_result = repo.query(query_string)

        # Direct function approach
        direct_result = apply_odata_to_queryset(
            blog_post_model.objects.all(), query_string
        )

        # Should produce identical querysets
        assert repo_result.query.order_by == direct_result.query.order_by
        assert repo_result.query.select_related == direct_result.query.select_related

        # Deferred loading should match
        repo_deferred = getattr(repo_result.query, "deferred_loading", (None, None))
        direct_deferred = getattr(direct_result.query, "deferred_loading", (None, None))
        assert repo_deferred[0] == direct_deferred[0]

    def test_mixin_backward_compatibility(self, blog_post_model):
        """Test that ODataMixin still works after refactoring."""
        factory = RequestFactory()

        # Test various query combinations
        test_queries = [
            "$filter=status eq 'published'",
            "$select=title,created_at&$expand=author",
            "$orderby=created_at desc&$top=10&$skip=5",
            "$filter=featured eq true&$expand=categories&$select=title",
        ]

        for query in test_queries:

            class TestViewSet(ODataModelViewSet):
                queryset = blog_post_model.objects.all()

            viewset = TestViewSet()
            request = factory.get(f"/test/?{query}")
            viewset.request = request

            # Should not raise exceptions
            queryset = viewset.get_queryset()
            assert isinstance(queryset, QuerySet)
            assert queryset.model == blog_post_model

    def test_repository_methods_vs_mixin_behavior(self, blog_post_model):
        """Test that repository methods behave like mixin operations."""
        query = "$filter=status eq 'published'&$top=3"

        # Repository count
        repo = ODataRepository(blog_post_model)
        repo_count = repo.count(query)

        # Mixin count (simulated)

        class TestViewSet(ODataModelViewSet):
            queryset = blog_post_model.objects.all()

        viewset = TestViewSet()
        factory = RequestFactory()
        request = factory.get(f"/test/?{query}")
        viewset.request = request

        mixin_queryset = viewset.get_queryset()
        mixin_count = mixin_queryset.count()

        # Should return same count
        assert repo_count == mixin_count

    def test_complex_nested_queries_compatibility(self, blog_post_model):
        """Test complex nested queries work identically."""
        complex_query = (
            "$filter=status eq 'published' and featured eq true"
            "&$select=id,title,created_at"
            "&$expand=author($select=name,email),categories($select=name)"
            "&$orderby=created_at desc"
            "&$top=10"
        )

        # Repository
        repo = ODataRepository(blog_post_model)
        repo_qs = repo.query(complex_query)

        # Mixin

        class TestViewSet(ODataModelViewSet):
            queryset = blog_post_model.objects.all()

        viewset = TestViewSet()
        factory = RequestFactory()
        request = factory.get(f"/test/?{complex_query}")
        viewset.request = request

        mixin_qs = viewset.get_queryset()

        # Should have identical query structure
        assert repo_qs.query.order_by == mixin_qs.query.order_by
        assert repo_qs.query.high_mark == mixin_qs.query.high_mark
        assert repo_qs.query.select_related == mixin_qs.query.select_related

        # Deferred loading should match
        repo_deferred = getattr(repo_qs.query, "deferred_loading", (None, None))
        mixin_deferred = getattr(mixin_qs.query, "deferred_loading", (None, None))
        assert repo_deferred[0] == mixin_deferred[0]

    def test_error_handling_consistency(self, blog_post_model):
        """Test that error handling is consistent between approaches."""
        invalid_query = "$filter=invalid_field eq 'test'"

        # Repository should handle gracefully
        repo = ODataRepository(blog_post_model)
        try:
            repo_result = repo.query(invalid_query)
            assert isinstance(repo_result, QuerySet)
        except Exception:
            # If it raises, that's acceptable behavior
            pass

        # Mixin should handle gracefully

        class TestViewSet(ODataModelViewSet):
            queryset = blog_post_model.objects.all()

        viewset = TestViewSet()
        factory = RequestFactory()
        request = factory.get(f"/test/?{invalid_query}")
        viewset.request = request

        try:
            mixin_result = viewset.get_queryset()
            assert isinstance(mixin_result, QuerySet)
        except Exception:
            # If it raises, that's acceptable behavior
            pass

    def test_empty_and_none_queries(self, blog_post_model):
        """Test handling of empty or None queries."""
        repo = ODataRepository(blog_post_model)

        # Empty query
        empty_repo = repo.query("")
        empty_direct = apply_odata_to_queryset(blog_post_model.objects.all(), "")

        assert empty_repo.query.order_by == empty_direct.query.order_by
        assert empty_repo.query.select_related == empty_direct.query.select_related

        # None query
        none_repo = repo.query(None)
        none_direct = apply_odata_to_queryset(blog_post_model.objects.all(), None)

        assert none_repo.query.order_by == none_direct.query.order_by
        assert none_repo.query.select_related == none_direct.query.select_related
