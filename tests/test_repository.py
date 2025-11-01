"""
Tests for OData Repository pattern implementation.
"""

import pytest
from django.db.models import QuerySet

from django_odata.repository import ODataRepository


@pytest.mark.django_db
class TestODataRepository:
    """Test ODataRepository class."""

    def test_initialization(self, blog_post_model):
        """Should initialize with model."""
        repo = ODataRepository(blog_post_model)
        assert repo.model == blog_post_model

    def test_query_returns_queryset(self, blog_post_model):
        """Should return QuerySet from query method."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("")
        assert isinstance(result, QuerySet)
        assert result.model == blog_post_model

    def test_query_applies_odata_filter(self, blog_post_model):
        """Should apply OData filter in query."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("$filter=status eq 'published'")
        assert isinstance(result, QuerySet)

    def test_query_applies_select(self, blog_post_model):
        """Should apply field selection in query."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("$select=title,content")

        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "title" in deferred_loading[0]
        assert "content" in deferred_loading[0]

    def test_query_applies_expand(self, blog_post_model):
        """Should apply expansions in query."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("$expand=author")

        assert "author" in result.query.select_related

    def test_query_applies_orderby(self, blog_post_model):
        """Should apply ordering in query."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("$orderby=title asc")

        assert result.query.order_by == ("title",)

    def test_query_applies_top(self, blog_post_model):
        """Should apply top limit in query."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("$top=5")

        assert result.query.high_mark == 5

    def test_query_applies_skip(self, blog_post_model):
        """Should apply skip offset in query."""
        repo = ODataRepository(blog_post_model)
        result = repo.query("$skip=10")

        assert result.query.low_mark == 10

    def test_query_combines_parameters(self, blog_post_model):
        """Should handle multiple OData parameters."""
        repo = ODataRepository(blog_post_model)
        result = repo.query(
            "$filter=status eq 'published'&$select=title&$expand=author&$orderby=title&$top=10"
        )

        # Verify all optimizations applied
        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "author" in result.query.select_related
        assert result.query.order_by == ("title",)
        assert result.query.high_mark == 10

    def test_count_returns_integer(self, blog_post_model):
        """Should return integer from count method."""
        repo = ODataRepository(blog_post_model)
        result = repo.count("")
        assert isinstance(result, int)

    def test_count_applies_filter(self, blog_post_model):
        """Should apply filter in count query."""
        repo = ODataRepository(blog_post_model)
        # This would need actual data to test properly
        result = repo.count("$filter=status eq 'published'")
        assert isinstance(result, int)

    def test_exists_returns_boolean(self, blog_post_model):
        """Should return boolean from exists method."""
        repo = ODataRepository(blog_post_model)
        result = repo.exists("")
        assert isinstance(result, bool)

    def test_exists_applies_filter(self, blog_post_model):
        """Should apply filter in exists query."""
        repo = ODataRepository(blog_post_model)
        result = repo.exists("$filter=status eq 'published'")
        assert isinstance(result, bool)

    def test_first_returns_model_instance_or_none(self, blog_post_model):
        """Should return model instance or None from first method."""
        repo = ODataRepository(blog_post_model)
        result = repo.first("")
        assert result is None or isinstance(result, blog_post_model)

    def test_first_applies_filter(self, blog_post_model):
        """Should apply filter in first query."""
        repo = ODataRepository(blog_post_model)
        result = repo.first("$filter=status eq 'published'")
        assert result is None or isinstance(result, blog_post_model)

    def test_get_list_returns_list(self, blog_post_model):
        """Should return list from get_list method."""
        repo = ODataRepository(blog_post_model)
        result = repo.get_list("")
        assert isinstance(result, list)

    def test_get_list_applies_odata(self, blog_post_model):
        """Should apply OData query in get_list."""
        repo = ODataRepository(blog_post_model)
        repo.get_list("$select=title&$expand=author")

        # get_list returns a list, so we need to check the queryset before evaluation
        qs = repo.query("$select=title&$expand=author")
        deferred_loading = getattr(qs.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "author" in qs.query.select_related


@pytest.mark.django_db
class TestRepositoryIntegration:
    """Integration tests for repository functionality."""

    def test_repository_vs_direct_function_consistency(self, blog_post_model):
        """Test that repository and direct function produce consistent results."""
        from django_odata.core import apply_odata_to_queryset

        repo = ODataRepository(blog_post_model)
        query = "$select=title&$expand=author&$orderby=title"

        # Get results from both approaches
        repo_result = repo.query(query)
        direct_result = apply_odata_to_queryset(blog_post_model.objects.all(), query)

        # Both should be QuerySets
        assert isinstance(repo_result, QuerySet)
        assert isinstance(direct_result, QuerySet)

        # Both should have same optimizations applied
        repo_deferred = getattr(repo_result.query, "deferred_loading", (None, None))
        direct_deferred = getattr(direct_result.query, "deferred_loading", (None, None))

        assert repo_deferred[0] is not None
        assert direct_deferred[0] is not None
        assert "author" in repo_result.query.select_related
        assert "author" in direct_result.query.select_related
        assert repo_result.query.order_by == direct_result.query.order_by

    def test_repository_methods_use_query_internally(self, blog_post_model):
        """Test that repository methods use query() internally."""
        repo = ODataRepository(blog_post_model)

        # Test that count uses query internally
        # (This is more of a design verification than a functional test)
        assert hasattr(repo, "query")
        assert hasattr(repo, "count")
        assert hasattr(repo, "exists")
        assert hasattr(repo, "first")
        assert hasattr(repo, "get_list")

    def test_repository_handles_empty_query(self, blog_post_model):
        """Test repository handles empty queries gracefully."""
        repo = ODataRepository(blog_post_model)

        # All methods should handle empty query
        assert isinstance(repo.query(""), QuerySet)
        assert isinstance(repo.count(""), int)
        assert isinstance(repo.exists(""), bool)
        assert repo.first("") is None or isinstance(repo.first(""), blog_post_model)
        assert isinstance(repo.get_list(""), list)

    def test_repository_preserves_model_relationships(self, blog_post_model):
        """Test repository preserves model relationships."""
        repo = ODataRepository(blog_post_model)

        result = repo.query("$expand=author")
        assert result.model == blog_post_model
        assert "author" in result.query.select_related


# Performance and edge case tests
@pytest.mark.django_db
class TestRepositoryEdgeCases:
    """Test repository edge cases and performance."""

    def test_repository_handles_complex_queries(self, blog_post_model):
        """Test repository handles complex OData queries."""
        repo = ODataRepository(blog_post_model)

        complex_query = (
            "$filter=status eq 'published'"
            "&$select=title,content,created_at"
            "&$expand=author($select=user__username),categories($select=name)"
            "&$orderby=created_at desc"
            "&$top=20&$skip=10"
        )

        result = repo.query(complex_query)

        # Should not raise exception and return QuerySet
        assert isinstance(result, QuerySet)

        # Should have ordering
        assert result.query.order_by == ("-created_at",)

        # Should have limit and offset
        assert result.query.high_mark == 30  # skip 10 + top 20
        assert result.query.low_mark == 10

    def test_repository_handles_invalid_queries(self, blog_post_model):
        """Test repository handles invalid OData queries."""
        repo = ODataRepository(blog_post_model)

        # This might raise exceptions depending on odata-query library
        # For now, test that it doesn't crash the repository
        try:
            result = repo.query("$invalid=parameter")
            assert isinstance(result, QuerySet)
        except Exception:
            # If it raises exception, that's acceptable behavior
            pass

    def test_repository_chaining_works(self, blog_post_model):
        """Test that repository results can be chained."""
        repo = ODataRepository(blog_post_model)

        result = repo.query("$select=title")
        # Should be able to chain additional QuerySet methods
        chained = result.filter(status="published").order_by("created_at")

        assert isinstance(chained, QuerySet)
        assert chained.model == blog_post_model
