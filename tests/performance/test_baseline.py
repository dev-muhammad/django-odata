"""
Performance baseline tests for SPEC-001: Remove drf-flex-fields.

These tests measure the current performance with drf-flex-fields to establish
a baseline for comparison after implementing native field selection/expansion.

Run with: pytest tests/performance/test_baseline.py -v --benchmark-only
"""

import pytest
from rest_framework.test import APIRequestFactory

# Import test models and serializers
from example.blog.models import Author, BlogPost, Category


@pytest.fixture
def api_factory():
    """Provide DRF API request factory."""
    return APIRequestFactory()


@pytest.fixture
def sample_data(db):
    """Create sample data for performance testing."""
    # Create authors
    from django.contrib.auth.models import User

    users = [
        User.objects.create_user(
            username=f"author{i}",
            email=f"author{i}@example.com",
            first_name="Author",
            last_name=str(i),
        )
        for i in range(10)
    ]
    authors = [
        Author.objects.create(user=users[i], bio=f"Bio for author {i}")
        for i in range(10)
    ]

    # Create categories
    categories = [
        Category.objects.create(
            name=f"Category {i}", description=f"Description for category {i}"
        )
        for i in range(5)
    ]

    # Create blog posts
    posts = []
    for i in range(100):
        post = BlogPost.objects.create(
            title=f"Post {i}",
            slug=f"post-{i}",
            content=f"Content for post {i}" * 10,  # Make content longer
            status="published" if i % 2 == 0 else "draft",
            author=authors[i % len(authors)],
            view_count=i * 10,
        )
        # Add categories
        post.categories.set([categories[i % len(categories)]])
        posts.append(post)

    return {"authors": authors, "categories": categories, "posts": posts}


@pytest.mark.benchmark
class TestFieldSelectionPerformance:
    """Benchmark $select query performance with drf-flex-fields."""

    def test_select_single_field(self, benchmark, api_factory, sample_data):
        """Measure performance of selecting a single field."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get("/posts/", {"$select": "id"})
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200

    def test_select_multiple_fields(self, benchmark, api_factory, sample_data):
        """Measure performance of selecting multiple fields."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get("/posts/", {"$select": "id,title,status"})
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200

    def test_select_all_fields(self, benchmark, api_factory, sample_data):
        """Measure performance with no $select (all fields)."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get("/posts/")
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200


@pytest.mark.benchmark
class TestFieldExpansionPerformance:
    """Benchmark $expand query performance with drf-flex-fields."""

    def test_expand_single_relation(self, benchmark, api_factory, sample_data):
        """Measure performance of expanding a single relation."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get("/posts/", {"$expand": "author"})
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200

    def test_expand_multiple_relations(self, benchmark, api_factory, sample_data):
        """Measure performance of expanding multiple relations."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get("/posts/", {"$expand": "author,categories"})
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200

    def test_expand_with_nested_select(self, benchmark, api_factory, sample_data):
        """Measure performance of expansion with nested field selection."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get(
                "/posts/", {"$expand": "author($select=name,email)"}
            )
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200


@pytest.mark.benchmark
class TestCombinedQueryPerformance:
    """Benchmark combined $select + $expand queries."""

    def test_select_and_expand(self, benchmark, api_factory, sample_data):
        """Measure performance of combined select and expand."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get(
                "/posts/", {"$select": "id,title,status", "$expand": "author"}
            )
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200

    def test_complex_query(self, benchmark, api_factory, sample_data):
        """Measure performance of complex query with multiple operations."""
        from django.urls import resolve

        def run_query():
            request = api_factory.get(
                "/posts/",
                {
                    "$select": "id,title,status",
                    "$expand": "author($select=name,email),categories",
                    "$filter": "status eq 'published'",
                    "$orderby": "created_at desc",
                    "$top": "20",
                },
            )
            view = resolve("/api/posts/").func
            response = view(request)
            return response

        result = benchmark(run_query)
        assert result.status_code == 200


@pytest.mark.benchmark
class TestSerializationPerformance:
    """Benchmark serialization performance."""

    def test_serialize_100_posts_no_expansion(self, benchmark, sample_data):
        """Measure serialization time for 100 posts without expansion."""
        from django_odata.serializers import ODataModelSerializer
        from example.blog.models import BlogPost

        class BlogPostSerializer(ODataModelSerializer):
            class Meta:
                model = BlogPost
                fields = ["id", "title", "content", "status", "created_at"]

        posts = BlogPost.objects.all()[:100]

        def serialize():
            serializer = BlogPostSerializer(posts, many=True)
            return serializer.data

        result = benchmark(serialize)
        assert len(result) == 100

    def test_serialize_100_posts_with_expansion(self, benchmark, sample_data):
        """Measure serialization time for 100 posts with author expansion."""
        from django_odata.serializers import ODataModelSerializer
        from example.blog.models import Author, BlogPost

        class AuthorSerializer(ODataModelSerializer):
            class Meta:
                model = Author
                fields = ["id", "name", "email"]

        class BlogPostSerializer(ODataModelSerializer):
            class Meta:
                model = BlogPost
                fields = ["id", "title", "content", "status", "created_at"]
                expandable_fields = {"author": (AuthorSerializer, {"many": False})}

        posts = BlogPost.objects.select_related("author").all()[:100]

        def serialize():
            context = {
                "odata_params": {"$expand": "author"},
                "request": type("Request", (), {"query_params": {}})(),
            }
            serializer = BlogPostSerializer(posts, many=True, context=context)
            return serializer.data

        result = benchmark(serialize)
        assert len(result) == 100


# Baseline metrics to document
"""
BASELINE PERFORMANCE METRICS (with drf-flex-fields)
====================================================

Run these tests and document the results:

pytest tests/performance/test_baseline.py -v --benchmark-only --benchmark-autosave

Expected metrics to capture:
- test_select_single_field: X ops/sec, Y ms/op
- test_select_multiple_fields: X ops/sec, Y ms/op
- test_expand_single_relation: X ops/sec, Y ms/op
- test_expand_multiple_relations: X ops/sec, Y ms/op
- test_expand_with_nested_select: X ops/sec, Y ms/op
- test_select_and_expand: X ops/sec, Y ms/op
- test_complex_query: X ops/sec, Y ms/op
- test_serialize_100_posts_no_expansion: X ops/sec, Y ms/op
- test_serialize_100_posts_with_expansion: X ops/sec, Y ms/op

After implementing native field selection/expansion, run the same tests
and compare results. Target: No regression, ideally 10-20% improvement.
"""
