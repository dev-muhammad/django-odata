"""
Utility functions for OData query parsing and Django ORM integration.
"""

import logging
from typing import Any, Dict, Union

from django.db.models import QuerySet
from django.http import QueryDict
from odata_query.django import apply_odata_query
from odata_query.exceptions import ODataException

logger = logging.getLogger(__name__)


def parse_odata_query(query_params: Union[QueryDict, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse OData query parameters from request.

    Args:
        query_params: Django QueryDict or dictionary containing query parameters

    Returns:
        Dictionary containing parsed OData query options
    """
    odata_params = {}

    # Standard OData query options
    odata_query_options = [
        "$filter",
        "$orderby",
        "$top",
        "$skip",
        "$select",
        "$expand",
        "$count",
        "$search",
        "$format",
    ]

    for param in odata_query_options:
        if param in query_params:
            odata_params[param] = query_params[param]

    # Handle additional parameters (keeping omit for backward compatibility)
    additional_params = ["omit"]
    for param in additional_params:
        if param in query_params:
            odata_params[param] = query_params[param]

    return odata_params


def apply_odata_query_params(
    queryset: QuerySet, query_params: Dict[str, Any]
) -> QuerySet:
    """
    Apply OData query parameters to a Django QuerySet.

    Args:
        queryset: Django QuerySet to filter
        query_params: Dictionary containing OData query parameters

    Returns:
        Filtered and ordered QuerySet

    Raises:
        ODataQueryError: If the OData query is invalid
    """
    try:
        queryset = _apply_filter(queryset, query_params)
        queryset = _apply_orderby(queryset, query_params)
        queryset = _apply_skip(queryset, query_params)
        queryset = _apply_top(queryset, query_params)
        return queryset

    except ODataException as e:
        logger.error(f"OData query error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error applying OData query: {e}")
        raise


def _apply_filter(queryset: QuerySet, query_params: Dict[str, Any]) -> QuerySet:
    """Apply $filter parameter to queryset."""
    if "$filter" in query_params:
        queryset = apply_odata_query(queryset, query_params["$filter"])
    return queryset


def _apply_orderby(queryset: QuerySet, query_params: Dict[str, Any]) -> QuerySet:
    """Apply $orderby parameter to queryset."""
    if "$orderby" not in query_params:
        return queryset

    order_fields = []
    for field in query_params["$orderby"].split(","):
        field = field.strip()
        if field.endswith(" desc"):
            order_fields.append("-" + field[:-5].strip())
        elif field.endswith(" asc"):
            order_fields.append(field[:-4].strip())
        else:
            order_fields.append(field)
    return queryset.order_by(*order_fields)


def _apply_skip(queryset: QuerySet, query_params: Dict[str, Any]) -> QuerySet:
    """Apply $skip parameter to queryset."""
    if "$skip" not in query_params:
        return queryset

    try:
        skip = int(query_params["$skip"])
        if skip > 0:
            queryset = queryset[skip:]
    except (ValueError, TypeError):
        logger.warning(f"Invalid $skip value: {query_params['$skip']}")
    return queryset


def _apply_top(queryset: QuerySet, query_params: Dict[str, Any]) -> QuerySet:
    """Apply $top parameter to queryset."""
    if "$top" not in query_params:
        return queryset

    try:
        top = int(query_params["$top"])
        if top > 0:
            queryset = queryset[:top]
    except (ValueError, TypeError):
        logger.warning(f"Invalid $top value: {query_params['$top']}")
    return queryset


def get_expandable_fields_from_serializer(serializer_class) -> Dict[str, Any]:
    """
    Extract expandable fields configuration from a FlexFields serializer.

    Args:
        serializer_class: Serializer class to inspect

    Returns:
        Dictionary of expandable fields configuration
    """
    if hasattr(serializer_class, "Meta") and hasattr(
        serializer_class.Meta, "expandable_fields"
    ):
        return serializer_class.Meta.expandable_fields
    return {}


def build_odata_metadata(model_class, serializer_class) -> Dict[str, Any]:
    """
    Build OData-style metadata for a model and its serializer.

    Args:
        model_class: Django model class
        serializer_class: DRF serializer class

    Returns:
        Dictionary containing metadata information
    """
    metadata = {
        "name": model_class.__name__,
        "namespace": model_class._meta.app_label,
        "properties": {},
        "navigation_properties": {},
    }

    # Get serializer fields
    serializer = serializer_class()
    fields = serializer.get_fields()

    for field_name, field in fields.items():
        field_type = type(field).__name__
        metadata["properties"][field_name] = {
            "type": field_type,
            "required": field.required,
            "read_only": field.read_only,
        }

    # Get expandable fields (navigation properties)
    expandable_fields = get_expandable_fields_from_serializer(serializer_class)
    for field_name, config in expandable_fields.items():
        metadata["navigation_properties"][field_name] = {
            "target_type": config[0] if isinstance(config, tuple) else str(config),
            "many": (
                config[1].get("many", False)
                if isinstance(config, tuple) and len(config) > 1
                else False
            ),
        }

    return metadata


class ODataQueryBuilder:
    """
    Helper class for building OData queries programmatically.
    """

    def __init__(self):
        self.filters = []
        self.order_by = []
        self.top = None
        self.skip = None
        self.select_fields = []
        self.expand_fields = []

    def filter(self, expression: str):
        """Add a filter expression."""
        self.filters.append(expression)
        return self

    def order(self, field: str, desc: bool = False):
        """Add an order by clause."""
        order_expr = f"{field} desc" if desc else field
        self.order_by.append(order_expr)
        return self

    def limit(self, count: int):
        """Set the top (limit) value."""
        self.top = count
        return self

    def offset(self, count: int):
        """Set the skip (offset) value."""
        self.skip = count
        return self

    def select(self, *fields):
        """Add fields to select."""
        self.select_fields.extend(fields)
        return self

    def expand(self, *fields):
        """Add fields to expand."""
        self.expand_fields.extend(fields)
        return self

    def build(self) -> Dict[str, str]:
        """Build the query parameters dictionary."""
        params = {}

        if self.filters:
            params["$filter"] = " and ".join(f"({f})" for f in self.filters)

        if self.order_by:
            params["$orderby"] = ", ".join(self.order_by)

        if self.top is not None:
            params["$top"] = str(self.top)

        if self.skip is not None:
            params["$skip"] = str(self.skip)

        if self.select_fields:
            params["$select"] = ",".join(self.select_fields)

        if self.expand_fields:
            params["$expand"] = ",".join(self.expand_fields)

        return params
