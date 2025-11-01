"""
Blog repositories for clean architecture implementation.

This module demonstrates how to use the ODataRepository pattern
in a clean architecture context, providing a clean interface
for data access without coupling to Django REST Framework.
"""

from django.db.models import QuerySet
from typing import List, Optional

from django_odata.repository import ODataRepository

from .models import BlogPost, Author, Category


class BlogPostRepository(ODataRepository):
    """
    Repository for BlogPost model with OData query support.

    This repository provides a clean interface for querying blog posts
    using OData syntax, while maintaining separation of concerns and
    enabling clean architecture patterns.

    Examples:
        >>> repo = BlogPostRepository()
        >>> published_posts = repo.query("$filter=status eq 'published'&$expand=author")
        >>> featured_posts = repo.query("$filter=featured eq true&$orderby=created_at desc")
        >>> recent_posts = repo.get_list("$filter=created_at ge 2024-01-01&$top=10")
    """

    def __init__(self):
        """Initialize repository with BlogPost model."""
        super().__init__(BlogPost)

    def get_published_posts(self, query_string: str = "") -> QuerySet:
        """
        Get published posts with optional additional filtering.

        Args:
            query_string: Additional OData query parameters

        Returns:
            QuerySet of published posts
        """
        base_query = "$filter=status eq 'published'"
        if query_string:
            base_query += f"&{query_string.lstrip('&')}"

        return self.query(base_query)

    def get_featured_posts(self, query_string: str = "") -> QuerySet:
        """
        Get featured posts with optional additional filtering.

        Args:
            query_string: Additional OData query parameters

        Returns:
            QuerySet of featured posts
        """
        base_query = "$filter=featured eq true"
        if query_string:
            base_query += f"&{query_string.lstrip('&')}"

        return self.query(base_query)

    def get_posts_by_author(self, author_id: int, query_string: str = "") -> QuerySet:
        """
        Get posts by specific author with optional additional filtering.

        Args:
            author_id: Author ID
            query_string: Additional OData query parameters

        Returns:
            QuerySet of posts by the author
        """
        base_query = f"$filter=author/id eq {author_id}"
        if query_string:
            base_query += f"&{query_string.lstrip('&')}"

        return self.query(base_query)

    def get_posts_by_category(self, category_id: int, query_string: str = "") -> QuerySet:
        """
        Get posts by specific category with optional additional filtering.

        Args:
            category_id: Category ID
            query_string: Additional OData query parameters

        Returns:
            QuerySet of posts in the category
        """
        base_query = f"$filter=categories/any(c:c/id eq {category_id})"
        if query_string:
            base_query += f"&{query_string.lstrip('&')}"

        return self.query(base_query)

    def search_posts(self, search_term: str, query_string: str = "") -> QuerySet:
        """
        Search posts by title or content with optional additional filtering.

        Args:
            search_term: Search term for title/content
            query_string: Additional OData query parameters

        Returns:
            QuerySet of matching posts
        """
        base_query = f"$filter=contains(title,'{search_term}') or contains(content,'{search_term}')"
        if query_string:
            base_query += f"&{query_string.lstrip('&')}"

        return self.query(base_query)


class AuthorRepository(ODataRepository):
    """
    Repository for Author model with OData query support.

    Examples:
        >>> repo = AuthorRepository()
        >>> authors = repo.query("$expand=user&$orderby=user/username")
    """

    def __init__(self):
        """Initialize repository with Author model."""
        super().__init__(Author)


class CategoryRepository(ODataRepository):
    """
    Repository for Category model with OData query support.

    Examples:
        >>> repo = CategoryRepository()
        >>> categories = repo.query("$orderby=name&$expand=posts($top=5)")
    """

    def __init__(self):
        """Initialize repository with Category model."""
        super().__init__(Category)