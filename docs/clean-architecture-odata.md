# Clean Architecture with OData Queries

This document describes how to implement clean architecture patterns using the decoupled OData functionality in django-odata. The solution allows you to use OData queries anywhere in your codebase without coupling to Django REST Framework.

## Overview

The clean architecture implementation provides:

- **Repository Pattern**: Clean data access interface using `ODataRepository`
- **Use Cases**: Business logic orchestration with dependency injection
- **Service Layer**: High-level operations combining repositories and use cases
- **DTOs**: Data Transfer Objects for clean data boundaries
- **Decoupled OData**: Use OData queries without DRF dependencies

## Architecture Layers

```
┌─────────────────────────────────────┐
│         Delivery Layer              │  ← Views, Commands, APIs
├─────────────────────────────────────┤
│         Service Layer               │  ← Business orchestration
├─────────────────────────────────────┤
│         Use Case Layer              │  ← Business logic
├─────────────────────────────────────┤
│         Repository Layer            │  ← Data access
├─────────────────────────────────────┤
│         Infrastructure Layer        │  ← Django models, OData
└─────────────────────────────────────┘
```

## Core Components

### 1. Repository Layer

The `ODataRepository` provides a clean interface for executing OData queries:

```python
from django_odata.repository import ODataRepository

class BlogPostRepository(ODataRepository):
    def __init__(self):
        super().__init__(BlogPost)

    def get_published_posts(self, query_string=""):
        """Get published posts with optional filtering."""
        base_query = "$filter=status eq 'published'"
        if query_string:
            base_query += f"&{query_string.lstrip('&')}"
        return self.query(base_query)

# Usage
repo = BlogPostRepository()
posts = repo.query("$filter=status eq 'published'&$expand=author")
count = repo.count("$filter=featured eq true")
```

### 2. Use Case Layer

Use cases contain business logic and orchestrate repositories:

```python
from .repositories import BlogPostRepository

class GetBlogPostsUseCase:
    def __init__(self, blog_post_repo=None):
        self.repo = blog_post_repo or BlogPostRepository()

    def execute(self, query_string="", filters=None, include_unpublished=False):
        # Business logic: hide unpublished by default
        base_query = "$filter=status eq 'published'" if not include_unpublished else ""

        # Apply business filters
        if filters.get('featured_only'):
            base_query += " and featured eq true"

        # Combine with OData query
        if query_string:
            combined = f"{base_query}&{query_string.lstrip('&')}" if base_query else query_string
        else:
            combined = base_query

        posts = self.repo.get_list(combined)
        return [BlogPostDTO.from_model(post) for post in posts]
```

### 3. Service Layer

Services orchestrate use cases and provide caching, logging, etc.:

```python
from .use_cases import GetBlogPostsUseCase

class BlogService:
    def __init__(self):
        self.get_posts_use_case = GetBlogPostsUseCase()

    def get_blog_posts(self, query_string="", filters=None, use_cache=True):
        cache_key = f"blog:posts:{query_string}:{filters}"

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached

        result = self.get_posts_use_case.execute(query_string, filters)

        if use_cache:
            cache.set(cache_key, result, timeout=300)

        return result
```

### 4. Data Transfer Objects (DTOs)

DTOs provide clean data boundaries:

```python
@dataclass
class BlogPostDTO:
    id: int
    title: str
    slug: str
    content: str
    author_name: str
    status: str
    created_at: str

    @classmethod
    def from_model(cls, post):
        return cls(
            id=post.id,
            title=post.title,
            slug=post.slug,
            content=post.content,
            author_name=post.author.name,
            status=post.status,
            created_at=post.created_at.isoformat(),
        )
```

## Usage Examples

### In Django Views (without DRF)

```python
from django.http import JsonResponse
from .services import BlogService

def blog_posts_api(request):
    service = BlogService()

    # Get OData query from request
    query_string = request.GET.urlencode()

    # Apply business filters
    filters = {}
    if request.GET.get('featured'):
        filters['featured_only'] = True

    posts = service.get_blog_posts(query_string, filters)
    return JsonResponse({'posts': [post.__dict__ for post in posts]})
```

### In Management Commands

```python
from django.core.management.base import BaseCommand
from .services import BlogService

class Command(BaseCommand):
    def handle(self, *args, **options):
        service = BlogService()

        # Export published posts
        posts = service.get_published_posts("$expand=author&$orderby=created_at desc")

        # Process posts...
        for post in posts:
            self.stdout.write(f"Exporting: {post.title}")
```

### In Background Tasks

```python
from .repositories import BlogPostRepository

def generate_blog_report():
    """Generate blog analytics report."""
    repo = BlogPostRepository()

    # Get statistics using OData
    total_posts = repo.count("")
    published_posts = repo.count("$filter=status eq 'published'")
    featured_posts = repo.count("$filter=featured eq true")

    # Generate report...
    return {
        'total_posts': total_posts,
        'published_posts': published_posts,
        'featured_posts': featured_posts,
    }
```

## Benefits

### 1. **Decoupling from DRF**
- Use OData queries in any context
- No dependency on Django REST Framework
- Works in management commands, background tasks, etc.

### 2. **Clean Architecture**
- Clear separation of concerns
- Dependency injection for testability
- Business logic isolated from infrastructure

### 3. **Performance Optimizations**
- Automatic QuerySet optimizations
- `select_related` and `prefetch_related` applied automatically
- Field selection with `.only()` for reduced memory usage

### 4. **Testability**
- Repositories can be mocked
- Use cases can be tested in isolation
- Services can be tested with dependency injection

### 5. **Caching**
- Built-in caching support in services
- Cache keys based on query parameters
- Configurable cache timeouts

## Migration from ODataMixin

### Before (DRF-coupled)

```python
class BlogPostViewSet(ODataMixin, ModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer

    def get_queryset(self):
        # OData logic mixed with DRF
        return self.apply_odata(self.queryset)
```

### After (Clean Architecture)

```python
# Repository
class BlogPostRepository(ODataRepository):
    def __init__(self):
        super().__init__(BlogPost)

# Use Case
class GetBlogPostsUseCase:
    def execute(self, query_string):
        repo = BlogPostRepository()
        return repo.query(query_string)

# Service
class BlogService:
    def get_posts(self, query_string):
        use_case = GetBlogPostsUseCase()
        return use_case.execute(query_string)

# View
def blog_api(request):
    service = BlogService()
    posts = service.get_posts(request.GET.urlencode())
    return JsonResponse({'posts': posts})
```

## Testing

### Repository Testing

```python
def test_repository_query():
    repo = BlogPostRepository()
    result = repo.query("$filter=status eq 'published'")
    assert isinstance(result, QuerySet)
```

### Use Case Testing

```python
def test_use_case_execute():
    mock_repo = Mock()
    use_case = GetBlogPostsUseCase(mock_repo)
    use_case.execute("$filter=featured eq true")
    mock_repo.query.assert_called_once()
```

### Service Testing

```python
def test_service_caching():
    mock_use_case = Mock()
    service = BlogService()
    service.get_posts_use_case = mock_use_case

    # First call
    service.get_posts("$filter=status eq 'published'")
    # Second call should use cache
    service.get_posts("$filter=status eq 'published'")

    # Use case should only be called once
    mock_use_case.execute.assert_called_once()
```

## Configuration

Add to your Django settings:

```python
# Cache settings for services
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/',
    }
}

# Service cache timeout
BLOG_CACHE_TIMEOUT = 300  # 5 minutes
```

## Best Practices

1. **Repository Methods**: Keep repositories focused on data access
2. **Use Case Granularity**: One use case per business operation
3. **Service Layer**: Use for cross-cutting concerns (caching, logging)
4. **DTOs**: Use for data boundaries between layers
5. **Dependency Injection**: Inject repositories for testability
6. **Caching Strategy**: Cache at service layer with appropriate timeouts
7. **Error Handling**: Handle OData parsing errors gracefully

## Performance Considerations

- **QuerySet Evaluation**: Use `get_list()` only when you need evaluated objects
- **Caching**: Implement caching for frequently accessed data
- **Pagination**: Always use `$top` and `$skip` for large datasets
- **Field Selection**: Use `$select` to reduce memory usage
- **Expand Optimization**: Use `$expand` judiciously to avoid N+1 queries

This clean architecture approach provides maximum flexibility while maintaining performance and testability.