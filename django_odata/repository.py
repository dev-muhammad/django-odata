"""
OData Repository

Repository layer for executing OData queries on Django models.
Provides a clean interface for using OData queries in repositories,
use cases, and any code that needs QuerySets.
"""

from typing import TYPE_CHECKING, List

from django.db.models import QuerySet

from .core import apply_odata_to_queryset

if TYPE_CHECKING:
    pass


class ODataRepository:
    """
    Repository for executing OData queries on Django models.

    Provides a clean interface for using OData queries in repositories,
    use cases, and any code that needs QuerySets. This class leverages
    the existing odata-query library for parsing and filtering, combined
    with custom optimization logic for field selection and eager loading.

    Examples:
        >>> # Basic usage
        >>> repo = ODataRepository(BlogPost)
        >>> posts = repo.query("$filter=status eq 'published'&$expand=author")

        >>> # With business logic
        >>> base_qs = BlogPost.objects.filter(featured=True)
        >>> posts = repo.query("$filter=rating gt 4.0", base_queryset=base_qs)

        >>> # Helper methods
        >>> count = repo.count("$filter=status eq 'published'")
        >>> exists = repo.exists("$filter=title eq 'My Post'")
        >>> first_post = repo.first("$orderby=created_at desc")
    """

    def __init__(self, model_class=None):
        """
        Initialize repository.

        Args:
            model_class: Optional Django model. Can be set per-query if not provided.
        """
        self.model = model_class

    def query(
        self, query_string: str = None, model_class=None, base_queryset: QuerySet = None
    ) -> QuerySet:
        """
        Execute OData query and return QuerySet.

        Args:
            query_string: OData query string (e.g., "$filter=status eq 'published'&$expand=author")
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter (default: Model.objects.all())

        Returns:
            Optimized Django QuerySet

        Examples:
            >>> repo = ODataRepository(BlogPost)
            >>> posts = repo.query("$filter=status eq 'published'&$expand=author")

            >>> # With custom base queryset
            >>> posts = repo.query(
            ...     "$filter=rating gt 4.0",
            ...     base_queryset=BlogPost.objects.filter(featured=True)
            ... )
        """
        model = model_class or self.model
        if not model:
            raise ValueError("model_class required")

        # Get base queryset
        if base_queryset is None:
            base_queryset = model.objects.all()

        # Apply OData query using the core wrapper
        return apply_odata_to_queryset(base_queryset, query_string)

    def query_from_request(
        self, request, model_class=None, base_queryset: QuerySet = None
    ) -> QuerySet:
        """
        Query from Django/DRF request.

        Args:
            request: Django/DRF request object
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter

        Returns:
            Optimized Django QuerySet
        """
        query_string = request.META.get("QUERY_STRING", "")
        return self.query(query_string, model_class, base_queryset)

    def count(self, query_string: str, model_class=None) -> int:
        """
        Get count of matching records.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)

        Returns:
            Count of matching records

        Example:
            >>> repo = ODataRepository(BlogPost)
            >>> published_count = repo.count("$filter=status eq 'published'")
        """
        qs = self.query(query_string, model_class)
        return qs.count()

    def exists(self, query_string: str, model_class=None) -> bool:
        """
        Check if any records match.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)

        Returns:
            True if any records match, False otherwise

        Example:
            >>> repo = ODataRepository(BlogPost)
            >>> has_drafts = repo.exists("$filter=status eq 'draft'")
        """
        qs = self.query(query_string, model_class)
        return qs.exists()

    def first(self, query_string: str, model_class=None):
        """
        Get first matching record.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)

        Returns:
            First matching record or None

        Example:
            >>> repo = ODataRepository(BlogPost)
            >>> latest_post = repo.first("$orderby=created_at desc")
        """
        qs = self.query(query_string, model_class)
        return qs.first()

    def get_list(
        self, query_string: str = None, model_class=None, base_queryset: QuerySet = None
    ) -> List:
        """
        Get evaluated list of objects.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter

        Returns:
            List of model instances

        Example:
            >>> repo = ODataRepository(BlogPost)
            >>> posts_list = repo.get_list("$filter=status eq 'published'&$top=10")
        """
        return list(self.query(query_string, model_class, base_queryset))
