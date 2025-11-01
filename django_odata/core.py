"""
OData Core Functions

Main entry point for applying OData queries to Django QuerySets.
Combines odata-query library with optimization functions.
"""

import logging
from typing import Any, Dict

from django.db.models import QuerySet
from odata_query.django import apply_odata_query
from odata_query.exceptions import ODataException

from .optimization import optimize_queryset_for_expand, optimize_queryset_for_select
from .utils import (
    _apply_orderby,
    _apply_skip,
    _apply_top,
    parse_expand_fields_v2,
    parse_odata_query,
)

logger = logging.getLogger(__name__)


def apply_odata_to_queryset(
    queryset: QuerySet, query_string: str = None, query_params: Dict[str, Any] = None
) -> QuerySet:
    """
    Apply OData query to a Django QuerySet with automatic optimizations.

    This is the main entry point for using OData queries anywhere in your code.
    It leverages the existing odata-query library for parsing and filtering,
    combined with custom optimization logic for field selection and eager loading.

    Args:
        queryset: Base Django QuerySet to query
        query_string: Raw query string (e.g., "$filter=status eq 'published'&$expand=author")
        query_params: Parsed query parameters dict (alternative to query_string)

    Returns:
        Optimized Django QuerySet with all OData parameters applied

    Raises:
        ODataException: If the OData query is invalid

    Examples:
        >>> # In a repository
        >>> posts = apply_odata_to_queryset(
        ...     BlogPost.objects.filter(is_active=True),
        ...     "$filter=status eq 'published'&$expand=author($select=name)"
        ... )

        >>> # In a management command
        >>> posts = apply_odata_to_queryset(
        ...     BlogPost.objects.all(),
        ...     "$filter=created_at ge 2024-01-01&$orderby=created_at desc&$top=100"
        ... )

        >>> # With programmatic queries
        >>> posts = apply_odata_to_queryset(
        ...     BlogPost.objects.all(),
        ...     {"$filter": "status eq 'published'", "$expand": "author"}
        ... )
    """
    # Parse query string into dict if provided
    if query_string:
        query_params = parse_odata_query(query_string)

    if not query_params:
        return queryset

    try:
        # Apply optimizations BEFORE filtering (order matters for performance)
        queryset = _apply_optimizations(queryset, query_params)

        # Apply filtering using odata-query library
        if "$filter" in query_params:
            queryset = apply_odata_query(queryset, query_params["$filter"])

        # Apply ordering
        if "$orderby" in query_params:
            queryset = _apply_orderby(queryset, query_params)

        # Apply pagination
        if "$skip" in query_params:
            queryset = _apply_skip(queryset, query_params)

        if "$top" in query_params:
            queryset = _apply_top(queryset, query_params)

        return queryset

    except ODataException as e:
        logger.error(f"OData query error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error applying OData query: {e}")
        raise


def _apply_optimizations(queryset: QuerySet, query_params: Dict[str, Any]) -> QuerySet:
    """
    Apply QuerySet optimizations based on OData parameters.

    Args:
        queryset: Base queryset
        query_params: Parsed OData parameters

    Returns:
        Optimized queryset
    """
    # Parse expand fields for optimization
    expand_fields = {}
    if "$expand" in query_params:
        expand_value = query_params["$expand"]
        if isinstance(expand_value, list):
            expand_value = expand_value[0] if expand_value else ""
        if expand_value:
            expand_fields = parse_expand_fields_v2(expand_value)

    # Apply field selection optimization
    if "$select" in query_params:
        select_fields = query_params["$select"]
        if isinstance(select_fields, str):
            select_fields = [f.strip() for f in select_fields.split(",")]
        queryset = optimize_queryset_for_select(queryset, select_fields, expand_fields)

    # Apply expansion optimization
    if expand_fields:
        queryset = optimize_queryset_for_expand(queryset, expand_fields)

    return queryset
