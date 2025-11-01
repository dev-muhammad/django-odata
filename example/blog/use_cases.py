"""
Blog use cases for clean architecture implementation.

This module demonstrates how to implement use cases that orchestrate
business logic using repositories, maintaining clean architecture
principles and separation of concerns.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from django.db.models import QuerySet

from .repositories import BlogPostRepository, AuthorRepository, CategoryRepository
from .models import BlogPost, Author, Category


@dataclass
class BlogPostDTO:
    """Data Transfer Object for BlogPost data."""
    id: int
    title: str
    slug: str
    content: str
    excerpt: str
    author_name: str
    author_email: str
    categories: List[str]
    status: str
    featured: bool
    view_count: int
    rating: Optional[float]
    created_at: str
    updated_at: str
    published_at: Optional[str]
    tags: List[str]
    word_count: int

    @classmethod
    def from_model(cls, post: BlogPost) -> 'BlogPostDTO':
        """Create DTO from BlogPost model instance."""
        return cls(
            id=post.id,
            title=post.title,
            slug=post.slug,
            content=post.content,
            excerpt=post.excerpt,
            author_name=post.author.name,
            author_email=post.author.email,
            categories=[cat.name for cat in post.categories.all()],
            status=post.status,
            featured=post.featured,
            view_count=post.view_count,
            rating=float(post.rating) if post.rating else None,
            created_at=post.created_at.isoformat(),
            updated_at=post.updated_at.isoformat(),
            published_at=post.published_at.isoformat() if post.published_at else None,
            tags=post.tags,
            word_count=post.word_count,
        )


class GetBlogPostsUseCase:
    """
    Use case for retrieving blog posts with various filtering options.

    This use case demonstrates clean architecture principles by:
    - Depending only on abstractions (repositories)
    - Containing business logic separate from infrastructure
    - Returning DTOs instead of raw model instances
    - Being easily testable with mocked repositories
    """

    def __init__(
        self,
        blog_post_repo: Optional[BlogPostRepository] = None,
        author_repo: Optional[AuthorRepository] = None,
        category_repo: Optional[CategoryRepository] = None,
    ):
        """
        Initialize use case with repositories.

        Args:
            blog_post_repo: BlogPost repository (injected for testability)
            author_repo: Author repository (injected for testability)
            category_repo: Category repository (injected for testability)
        """
        self.blog_post_repo = blog_post_repo or BlogPostRepository()
        self.author_repo = author_repo or AuthorRepository()
        self.category_repo = category_repo or CategoryRepository()

    def execute(
        self,
        query_string: str = "",
        filters: Optional[Dict[str, Any]] = None,
        include_unpublished: bool = False,
    ) -> List[BlogPostDTO]:
        """
        Execute the use case to get blog posts.

        Args:
            query_string: OData query string for filtering/sorting/pagination
            filters: Additional business logic filters
            include_unpublished: Whether to include unpublished posts

        Returns:
            List of BlogPostDTO objects
        """
        # Apply business logic filters
        base_query = self._build_base_query(filters or {}, include_unpublished)

        # Combine with OData query
        if query_string:
            if base_query:
                combined_query = f"{base_query}&{query_string.lstrip('&')}"
            else:
                combined_query = query_string
        else:
            combined_query = base_query

        # Get posts using repository
        posts = self.blog_post_repo.get_list(combined_query)

        # Convert to DTOs
        return [BlogPostDTO.from_model(post) for post in posts]

    def _build_base_query(self, filters: Dict[str, Any], include_unpublished: bool) -> str:
        """Build base OData query from business filters."""
        conditions = []

        # Business rule: hide unpublished posts by default
        if not include_unpublished:
            conditions.append("status eq 'published'")

        # Apply additional filters
        if filters.get('featured_only'):
            conditions.append("featured eq true")

        if filters.get('author_id'):
            conditions.append(f"author/id eq {filters['author_id']}")

        if filters.get('category_id'):
            conditions.append(f"categories/any(c:c/id eq {filters['category_id']})")

        if filters.get('min_rating'):
            conditions.append(f"rating ge {filters['min_rating']}")

        if filters.get('search_term'):
            search = filters['search_term']
            conditions.append(f"contains(title,'{search}') or contains(content,'{search}')")

        if filters.get('tags'):
            # Filter posts that have any of the specified tags
            tag_conditions = [f"tags/any(t:t eq '{tag}')" for tag in filters['tags']]
            conditions.append(f"({' or '.join(tag_conditions)})")

        # Combine conditions
        if conditions:
            return "$filter=" + " and ".join(conditions)

        return ""


class GetPublishedBlogPostsUseCase:
    """
    Specialized use case for getting published blog posts.

    Demonstrates how to create focused use cases for common operations.
    """

    def __init__(self, blog_post_repo: Optional[BlogPostRepository] = None):
        self.blog_post_repo = blog_post_repo or BlogPostRepository()

    def execute(self, query_string: str = "") -> List[BlogPostDTO]:
        """
        Get published blog posts with optional additional filtering.

        Args:
            query_string: Additional OData query parameters

        Returns:
            List of published BlogPostDTO objects
        """
        posts = self.blog_post_repo.get_published_posts(query_string)
        return [BlogPostDTO.from_model(post) for post in posts]


class GetFeaturedBlogPostsUseCase:
    """
    Specialized use case for getting featured blog posts.
    """

    def __init__(self, blog_post_repo: Optional[BlogPostRepository] = None):
        self.blog_post_repo = blog_post_repo or BlogPostRepository()

    def execute(self, query_string: str = "") -> List[BlogPostDTO]:
        """
        Get featured blog posts with optional additional filtering.

        Args:
            query_string: Additional OData query parameters

        Returns:
            List of featured BlogPostDTO objects
        """
        posts = self.blog_post_repo.get_featured_posts(query_string)
        return [BlogPostDTO.from_model(post) for post in posts]


class SearchBlogPostsUseCase:
    """
    Use case for searching blog posts by content.
    """

    def __init__(self, blog_post_repo: Optional[BlogPostRepository] = None):
        self.blog_post_repo = blog_post_repo or BlogPostRepository()

    def execute(self, search_term: str, query_string: str = "") -> List[BlogPostDTO]:
        """
        Search blog posts by title or content.

        Args:
            search_term: Term to search for
            query_string: Additional OData query parameters

        Returns:
            List of matching BlogPostDTO objects
        """
        posts = self.blog_post_repo.search_posts(search_term, query_string)
        return [BlogPostDTO.from_model(post) for post in posts]