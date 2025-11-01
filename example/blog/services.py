"""
Blog services demonstrating how to use the clean architecture components.

This module shows how to orchestrate repositories and use cases
in service layer components, which can be used by views, management
commands, or background tasks.
"""

from typing import List, Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings

from .repositories import BlogPostRepository, AuthorRepository, CategoryRepository
from .use_cases import (
    GetBlogPostsUseCase,
    GetPublishedBlogPostsUseCase,
    GetFeaturedBlogPostsUseCase,
    SearchBlogPostsUseCase,
    BlogPostDTO,
)


class BlogService:
    """
    Service layer for blog operations using clean architecture.

    This service demonstrates how to compose repositories and use cases
    to provide high-level business operations that can be used across
    different delivery mechanisms (views, APIs, commands, etc.).
    """

    def __init__(
        self,
        blog_post_repo: Optional[BlogPostRepository] = None,
        author_repo: Optional[AuthorRepository] = None,
        category_repo: Optional[CategoryRepository] = None,
    ):
        """Initialize service with repositories."""
        self.blog_post_repo = blog_post_repo or BlogPostRepository()
        self.author_repo = author_repo or AuthorRepository()
        self.category_repo = category_repo or CategoryRepository()

        # Initialize use cases
        self.get_posts_use_case = GetBlogPostsUseCase(
            self.blog_post_repo, self.author_repo, self.category_repo
        )
        self.get_published_use_case = GetPublishedBlogPostsUseCase(self.blog_post_repo)
        self.get_featured_use_case = GetFeaturedBlogPostsUseCase(self.blog_post_repo)
        self.search_use_case = SearchBlogPostsUseCase(self.blog_post_repo)

    def get_blog_posts(
        self,
        query_string: str = "",
        filters: Optional[Dict[str, Any]] = None,
        include_unpublished: bool = False,
        use_cache: bool = True,
    ) -> List[BlogPostDTO]:
        """
        Get blog posts with caching support.

        Args:
            query_string: OData query string
            filters: Business logic filters
            include_unpublished: Include unpublished posts
            use_cache: Whether to use caching

        Returns:
            List of BlogPostDTO objects
        """
        # Create cache key
        cache_key = self._build_cache_key("posts", query_string, filters, include_unpublished)

        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Execute use case
        result = self.get_posts_use_case.execute(query_string, filters, include_unpublished)

        # Cache result
        if use_cache:
            cache.set(cache_key, result, timeout=getattr(settings, 'BLOG_CACHE_TIMEOUT', 300))

        return result

    def get_published_posts(self, query_string: str = "", use_cache: bool = True) -> List[BlogPostDTO]:
        """
        Get published blog posts.

        Args:
            query_string: Additional OData query parameters
            use_cache: Whether to use caching

        Returns:
            List of published BlogPostDTO objects
        """
        cache_key = self._build_cache_key("published", query_string)

        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = self.get_published_use_case.execute(query_string)

        if use_cache:
            cache.set(cache_key, result, timeout=getattr(settings, 'BLOG_CACHE_TIMEOUT', 300))

        return result

    def get_featured_posts(self, query_string: str = "", use_cache: bool = True) -> List[BlogPostDTO]:
        """
        Get featured blog posts.

        Args:
            query_string: Additional OData query parameters
            use_cache: Whether to use caching

        Returns:
            List of featured BlogPostDTO objects
        """
        cache_key = self._build_cache_key("featured", query_string)

        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = self.get_featured_use_case.execute(query_string)

        if use_cache:
            cache.set(cache_key, result, timeout=getattr(settings, 'BLOG_CACHE_TIMEOUT', 300))

        return result

    def search_posts(self, search_term: str, query_string: str = "", use_cache: bool = True) -> List[BlogPostDTO]:
        """
        Search blog posts.

        Args:
            search_term: Search term
            query_string: Additional OData query parameters
            use_cache: Whether to use caching

        Returns:
            List of matching BlogPostDTO objects
        """
        cache_key = self._build_cache_key("search", query_string, {"search_term": search_term})

        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        result = self.search_use_case.execute(search_term, query_string)

        if use_cache:
            cache.set(cache_key, result, timeout=getattr(settings, 'BLOG_CACHE_TIMEOUT', 60))  # Shorter cache for search

        return result

    def get_blog_stats(self) -> Dict[str, Any]:
        """
        Get blog statistics using repository methods.

        Returns:
            Dictionary with blog statistics
        """
        return {
            'total_posts': self.blog_post_repo.count(""),
            'published_posts': self.blog_post_repo.count("$filter=status eq 'published'"),
            'featured_posts': self.blog_post_repo.count("$filter=featured eq true"),
            'total_authors': self.author_repo.count(""),
            'total_categories': self.category_repo.count(""),
        }

    def invalidate_cache(self):
        """Invalidate all blog-related cache entries."""
        # This is a simplified implementation - in production you'd want more granular cache invalidation
        cache.delete_pattern("blog:*")

    def _build_cache_key(self, operation: str, query_string: str = "", filters: Optional[Dict] = None, *args) -> str:
        """Build cache key for the operation."""
        key_parts = ["blog", operation]

        if query_string:
            key_parts.append(query_string.replace("&", "_").replace("=", "_"))

        if filters:
            # Sort filters for consistent cache keys
            sorted_filters = sorted(filters.items())
            key_parts.extend([f"{k}_{v}" for k, v in sorted_filters])

        for arg in args:
            key_parts.append(str(arg))

        return ":".join(key_parts)


# Example usage in a management command
class BlogDataExporter:
    """
    Example service for exporting blog data using OData queries.

    This demonstrates how the clean architecture can be used in
    background tasks or management commands.
    """

    def __init__(self, service: Optional[BlogService] = None):
        self.service = service or BlogService()

    def export_published_posts(self, format_type: str = "json") -> Dict[str, Any]:
        """
        Export published posts for backup/analytics.

        Args:
            format_type: Export format (json, csv, etc.)

        Returns:
            Export data structure
        """
        # Get all published posts with full details
        posts = self.service.get_published_posts(
            "$expand=author,categories&$orderby=created_at desc",
            use_cache=False  # Don't use cache for exports
        )

        if format_type == "json":
            return {
                "posts": [post.__dict__ for post in posts],
                "exported_at": "2024-01-01T00:00:00Z",  # Would use datetime.now()
                "total_count": len(posts),
            }
        elif format_type == "csv":
            # Would implement CSV export logic here
            return {"error": "CSV export not implemented"}

        return {"error": f"Unsupported format: {format_type}"}

    def export_author_stats(self) -> Dict[str, Any]:
        """
        Export author statistics.

        Returns:
            Author statistics
        """
        # Get all authors with their post counts
        authors = self.author_repo.query("$expand=user,posts&$orderby=user/username")

        stats = []
        for author in authors:
            post_count = author.posts.count()
            published_count = author.posts.filter(status='published').count()

            stats.append({
                "author_id": author.id,
                "name": author.name,
                "email": author.email,
                "total_posts": post_count,
                "published_posts": published_count,
            })

        return {
            "author_stats": stats,
            "total_authors": len(stats),
        }