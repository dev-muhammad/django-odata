import pytest
from django.db import connection
from django.test import RequestFactory

from django_odata.repository import ODataRepository
from django_odata.viewsets import ODataModelViewSet


class TestODataPerformanceComparison:
    """Performance benchmarks comparing repository pattern vs ODataMixin."""

    @pytest.fixture
    def request_factory(self):
        """Fixture providing a RequestFactory instance."""
        return RequestFactory()

    def _count_queries(self, queryset_func):
        """Count database queries executed by a function."""
        initial_queries = len(connection.queries)
        result = queryset_func()
        final_queries = len(connection.queries)
        return result, final_queries - initial_queries

    def _benchmark_repository_vs_mixin(
        self, request_factory, query_string, model_class
    ):
        """Benchmark repository vs mixin for a given query."""
        factory = request_factory

        # Repository approach
        def repository_query():
            repo = ODataRepository(model_class)
            return repo.query(query_string)

        # Mixin approach
        def mixin_query():
            class TestViewSet(ODataModelViewSet):
                queryset = model_class.objects.all()

            viewset = TestViewSet()
            request = factory.get(f"/test/?{query_string}")
            viewset.request = request
            return viewset.get_queryset()

        # Execute and count queries
        repo_result, repo_queries = self._count_queries(repository_query)
        mixin_result, mixin_queries = self._count_queries(mixin_query)

        return {
            "repository": {"result": repo_result, "queries": repo_queries},
            "mixin": {"result": mixin_result, "queries": mixin_queries},
        }

    @pytest.mark.django_db
    @pytest.mark.benchmark
    def test_simple_select_performance(self, request_factory, blog_post_model):
        """Benchmark simple $select query performance."""
        query = "$select=title,content"
        results = self._benchmark_repository_vs_mixin(
            request_factory, query, blog_post_model
        )

        # Both should return same results
        assert len(results["repository"]["result"]) == len(results["mixin"]["result"])

        # Repository should be at least as efficient as mixin
        # Allow for slight variations due to implementation differences
        assert results["repository"]["queries"] <= results["mixin"]["queries"] + 1

    @pytest.mark.django_db
    @pytest.mark.benchmark
    def test_expand_performance(self, request_factory, blog_post_model):
        """Benchmark $expand query performance."""
        query = "$expand=author($select=name,email),category($select=name)"
        results = self._benchmark_repository_vs_mixin(
            request_factory, query, blog_post_model
        )

        # Both should return same results
        assert len(results["repository"]["result"]) == len(results["mixin"]["result"])

        # Repository should be at least as efficient as mixin
        assert results["repository"]["queries"] <= results["mixin"]["queries"] + 1

    @pytest.mark.django_db
    @pytest.mark.benchmark
    def test_filter_performance(self, request_factory, blog_post_model):
        """Benchmark $filter query performance."""
        query = "$filter=status eq 'published' and created_at gt 2023-01-01T00:00:00Z"
        results = self._benchmark_repository_vs_mixin(
            request_factory, query, blog_post_model
        )

        # Both should return same results
        assert len(results["repository"]["result"]) == len(results["mixin"]["result"])

        # Repository should be at least as efficient as mixin
        assert results["repository"]["queries"] <= results["mixin"]["queries"] + 1

    @pytest.mark.django_db
    @pytest.mark.benchmark
    def test_complex_query_performance(self, request_factory, blog_post_model):
        """Benchmark complex combined query performance."""
        query = "$select=title,content&$expand=author($select=name)&$filter=status eq 'published'&$orderby=created_at desc&$top=10"
        results = self._benchmark_repository_vs_mixin(
            request_factory, query, blog_post_model
        )

        # Both should return same results
        assert len(results["repository"]["result"]) == len(results["mixin"]["result"])

        # Repository should be at least as efficient as mixin
        assert results["repository"]["queries"] <= results["mixin"]["queries"] + 1

    @pytest.mark.django_db
    @pytest.mark.benchmark
    def test_pagination_performance(self, request_factory, blog_post_model):
        """Benchmark pagination query performance."""
        query = "$top=5&$skip=10&$orderby=id"
        results = self._benchmark_repository_vs_mixin(
            request_factory, query, blog_post_model
        )

        # Both should return same results
        assert len(results["repository"]["result"]) == len(results["mixin"]["result"])

        # Repository should be at least as efficient as mixin
        assert results["repository"]["queries"] <= results["mixin"]["queries"] + 1

    @pytest.mark.django_db
    def test_optimization_effectiveness(self, request_factory, blog_post_model):
        """Test that both approaches apply the same optimizations."""
        query = "$select=title,author/name&$expand=author($select=name,email)"

        # Repository approach
        repo = ODataRepository(blog_post_model)
        repo_qs = repo.query(query)

        # Mixin approach
        class TestViewSet(ODataModelViewSet):
            queryset = blog_post_model.objects.all()

        viewset = TestViewSet()
        request = request_factory.get(f"/test/?{query}")
        viewset.request = request
        mixin_qs = viewset.get_queryset()

        # Both should have select_related for author
        assert "author" in str(repo_qs.query.select_related)
        assert "author" in str(mixin_qs.query.select_related)

        # Both should have only() applied to limit fields
        # Note: This is harder to test directly, but we can check the query structure
        repo_sql = str(repo_qs.query)
        mixin_sql = str(mixin_qs.query)

        # Both queries should be structurally similar
        assert "title" in repo_sql
        assert "title" in mixin_sql

    @pytest.mark.django_db
    def test_memory_usage_comparison(self, request_factory, blog_post_model):
        """Compare memory usage between approaches."""
        import os

        import psutil

        def get_memory_usage():
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB

        query = "$expand=author,category&$top=50"

        # Repository approach
        initial_memory = get_memory_usage()
        repo = ODataRepository(blog_post_model)
        repo_result = repo.query(query)
        list(repo_result)  # Force evaluation
        repo_memory = get_memory_usage() - initial_memory

        # Mixin approach
        initial_memory = get_memory_usage()

        class TestViewSet(ODataModelViewSet):
            queryset = blog_post_model.objects.all()

        viewset = TestViewSet()
        request = request_factory.get(f"/test/?{query}")
        viewset.request = request
        mixin_result = viewset.get_queryset()
        list(mixin_result)  # Force evaluation
        mixin_memory = get_memory_usage() - initial_memory

        # Repository should not use significantly more memory
        # Allow 10% tolerance for measurement variations
        assert repo_memory <= mixin_memory * 1.1
