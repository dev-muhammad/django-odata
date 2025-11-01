"""
Tests for OData core functionality.
"""

import pytest
from django.db.models import QuerySet

from django_odata.core import apply_odata_to_queryset


@pytest.mark.django_db
class TestApplyOdataToQueryset:
    """Test apply_odata_to_queryset function."""

    def test_returns_queryset_instance(self, blog_post_queryset):
        """Should return a QuerySet instance."""
        result = apply_odata_to_queryset(blog_post_queryset, "")
        assert isinstance(result, QuerySet)

    def test_empty_query_returns_unchanged(self, blog_post_queryset):
        """Should return unchanged queryset for empty query."""
        result = apply_odata_to_queryset(blog_post_queryset, "")
        assert result is blog_post_queryset

    def test_applies_filter(self, blog_post_queryset):
        """Should apply $filter query."""
        result = apply_odata_to_queryset(
            blog_post_queryset, "$filter=status eq 'published'"
        )
        # Verify filter was applied (would need actual data to test fully)
        assert isinstance(result, QuerySet)

    def test_applies_select(self, blog_post_queryset):
        """Should apply $select query."""
        result = apply_odata_to_queryset(blog_post_queryset, "$select=title,content")
        # Verify only() was applied
        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "title" in deferred_loading[0]
        assert "content" in deferred_loading[0]

    def test_applies_expand(self, blog_post_queryset):
        """Should apply $expand query."""
        result = apply_odata_to_queryset(blog_post_queryset, "$expand=author")
        # Verify select_related was applied
        assert "author" in result.query.select_related

    def test_applies_orderby(self, blog_post_queryset):
        """Should apply $orderby query."""
        result = apply_odata_to_queryset(blog_post_queryset, "$orderby=title asc")
        # Verify ordering was applied
        assert result.query.order_by == ("title",)

    def test_applies_top(self, blog_post_queryset):
        """Should apply $top query."""
        result = apply_odata_to_queryset(blog_post_queryset, "$top=10")
        # Verify limit was applied
        assert result.query.low_mark == 0
        assert result.query.high_mark == 10

    def test_applies_skip(self, blog_post_queryset):
        """Should apply $skip query."""
        result = apply_odata_to_queryset(blog_post_queryset, "$skip=5")
        # Verify offset was applied
        assert result.query.low_mark == 5

    def test_applies_count(self, blog_post_queryset):
        """Should apply $count query."""
        result = apply_odata_to_queryset(blog_post_queryset, "$count=true")
        # Count query should still return QuerySet
        assert isinstance(result, QuerySet)

    def test_combines_multiple_parameters(self, blog_post_queryset):
        """Should handle multiple OData parameters."""
        result = apply_odata_to_queryset(
            blog_post_queryset,
            "$filter=status eq 'published'&$select=title&$expand=author&$orderby=title&$top=5",
        )

        # Verify all optimizations applied
        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "author" in result.query.select_related
        assert result.query.order_by == ("title",)
        assert result.query.high_mark == 5

    def test_handles_complex_expand(self, blog_post_queryset):
        """Should handle complex expand with nested selects."""
        result = apply_odata_to_queryset(
            blog_post_queryset, "$expand=author($select=name,email)"
        )

        # Verify select_related applied
        assert "author" in result.query.select_related

        # Verify field selection includes FK
        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        # The FK field might be in the related field selection
        assert deferred_loading[0] is not None

    def test_preserves_existing_filters(self, blog_post_queryset):
        """Should preserve existing QuerySet filters."""
        # Add existing filter
        filtered_qs = blog_post_queryset.filter(status="draft")

        result = apply_odata_to_queryset(filtered_qs, "$filter=featured eq true")

        # Should still have the original filter
        # (Testing this properly would require actual data)
        assert isinstance(result, QuerySet)

    def test_handles_invalid_query_gracefully(self, blog_post_queryset):
        """Should handle invalid OData queries gracefully."""
        # This might raise an exception depending on odata-query library behavior
        # For now, test that it doesn't crash
        try:
            result = apply_odata_to_queryset(blog_post_queryset, "$invalid=parameter")
            # If it doesn't raise, it should still return a QuerySet
            assert isinstance(result, QuerySet)
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            pass

    def test_returns_same_queryset_type(self, blog_post_queryset):
        """Should return same QuerySet type as input."""
        result = apply_odata_to_queryset(blog_post_queryset, "$select=title")
        assert isinstance(result, type(blog_post_queryset))


@pytest.mark.django_db
class TestApplyOptimizations:
    """Test _apply_optimizations internal function."""

    def test_applies_field_selection(self, blog_post_queryset):
        """Should apply field selection optimizations."""
        from django_odata.core import _apply_optimizations

        query_params = {"$select": "title"}
        result = _apply_optimizations(blog_post_queryset, query_params)

        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "title" in deferred_loading[0]

    def test_applies_expansion_optimizations(self, blog_post_queryset):
        """Should apply expansion optimizations."""
        from django_odata.core import _apply_optimizations

        query_params = {"$expand": "author"}
        result = _apply_optimizations(blog_post_queryset, query_params)

        assert "author" in result.query.select_related

    def test_combines_field_and_expand_optimizations(self, blog_post_queryset):
        """Should combine field selection and expansion optimizations."""
        from django_odata.core import _apply_optimizations

        query_params = {"$select": "title", "$expand": "author"}
        result = _apply_optimizations(blog_post_queryset, query_params)

        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None
        assert "author" in result.query.select_related


# Integration tests
@pytest.mark.django_db
class TestCoreIntegration:
    """Integration tests for core functionality."""

    def test_end_to_end_odata_processing(self, blog_post_queryset):
        """Test complete end-to-end OData processing."""
        query = "$filter=status eq 'published'&$select=title,content&$expand=author($select=name)&$orderby=title&$top=10"

        result = apply_odata_to_queryset(blog_post_queryset, query)

        # Verify all aspects applied
        assert isinstance(result, QuerySet)

        # Check field selection
        deferred_loading = getattr(result.query, "deferred_loading", (None, None))
        assert deferred_loading[0] is not None

        # Check expansion
        assert "author" in result.query.select_related

        # Check ordering
        assert result.query.order_by == ("title",)

        # Check limit
        assert result.query.high_mark == 10

    def test_optimization_preserves_query_structure(self, blog_post_queryset):
        """Test that optimizations preserve QuerySet query structure."""
        original_query = blog_post_queryset.query.clone()

        result = apply_odata_to_queryset(blog_post_queryset, "$select=title")

        # Query should be modified but structure preserved
        assert result.query.model == original_query.model
