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


def parse_expand_fields_v2(expand_string: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse OData $expand with full query options support.

    Supports:
    - Simple expansion: "author" -> {'author': {}}
    - Nested $select: "author($select=name,email)" -> {'author': {'$select': 'name,email'}}
    - Multiple query options: "author($select=name;$filter=active eq true;$orderby=name desc;$top=5)"
    - Multiple expansions: "author,categories" -> {'author': {}, 'categories': {}}
    - Nested expansions: "author($expand=posts($top=3))"
    - Complex combinations: "author($select=name;$expand=posts($top=3)),categories($filter=active eq true)"

    Args:
        expand_string: The raw $expand query string.

    Returns:
        Dictionary where keys are field names and values are dictionaries
        of their respective OData query options.

    Examples:
        >>> parse_expand_fields_v2("author")
        {'author': {}}

        >>> parse_expand_fields_v2("author($select=name,email)")
        {'author': {'$select': 'name,email'}}

        >>> parse_expand_fields_v2("author($select=name;$filter=active eq true;$top=5)")
        {'author': {'$select': 'name', '$filter': 'active eq true', '$top': '5'}}

        >>> parse_expand_fields_v2("author,categories($orderby=name)")
        {'author': {}, 'categories': {'$orderby': 'name'}}
    """
    if not expand_string or not expand_string.strip():
        return {}

    result = {}
    current_field = ""
    paren_depth = 0

    # Add comma at end to process last field
    for char in expand_string + ",":
        if char == "(":
            paren_depth += 1
            current_field += char
        elif char == ")":
            paren_depth -= 1
            current_field += char
        elif char == "," and paren_depth == 0:
            # End of field at top level
            if current_field.strip():
                field_name, options = _parse_single_expand_field_v2(
                    current_field.strip()
                )
                result[field_name] = options
            current_field = ""
        else:
            current_field += char

    return result


def _parse_single_expand_field_v2(field: str) -> tuple[str, Dict[str, Any]]:
    """
    Parse a single expand field expression with all query options.

    Args:
        field: Single expand expression, e.g., "author" or "author($select=name;$filter=active eq true)"

    Returns:
        Tuple of (field_name, options_dict)

    Examples:
        >>> _parse_single_expand_field_v2("author")
        ('author', {})

        >>> _parse_single_expand_field_v2("author($select=name,email)")
        ('author', {'$select': 'name,email'})

        >>> _parse_single_expand_field_v2("author($select=name;$filter=active eq true;$top=5)")
        ('author', {'$select': 'name', '$filter': 'active eq true', '$top': '5'})
    """
    field = field.strip()

    if "(" not in field:
        # Simple field without options
        return field, {}

    # Parse field_name(options)
    field_name = field.split("(")[0].strip()

    # Extract content inside parentheses
    start_paren = field.find("(")
    end_paren = field.rfind(")")

    if start_paren == -1 or end_paren == -1:
        # Malformed, return as simple field
        logger.warning(f"Malformed expand expression: {field}")
        return field, {}

    inner_content = field[start_paren + 1 : end_paren]

    # Parse query options separated by semicolons
    options = _parse_query_options(inner_content)

    return field_name, options


def _parse_query_options(options_string: str) -> Dict[str, Any]:
    """
    Parse query options from the content inside parentheses.

    Handles:
    - $select=field1,field2
    - $filter=expression
    - $orderby=field desc
    - $top=10
    - $skip=5
    - $count=true
    - $expand=nested($select=field)

    Args:
        options_string: String containing query options separated by semicolons

    Returns:
        Dictionary of parsed query options

    Examples:
        >>> _parse_query_options("$select=name,email")
        {'$select': 'name,email'}

        >>> _parse_query_options("$select=name;$filter=active eq true;$top=5")
        {'$select': 'name', '$filter': 'active eq true', '$top': '5'}

        >>> _parse_query_options("$select=name;$expand=posts($top=3)")
        {'$select': 'name', '$expand': 'posts($top=3)'}
    """
    if not options_string or not options_string.strip():
        return {}

    options = {}
    current_option = ""
    paren_depth = 0

    # Add semicolon at end to process last option
    for char in options_string + ";":
        if char == "(":
            paren_depth += 1
            current_option += char
        elif char == ")":
            paren_depth -= 1
            current_option += char
        elif char == ";" and paren_depth == 0:
            # End of option at top level
            if current_option.strip():
                key, value = _parse_single_query_option(current_option.strip())
                if key:
                    options[key] = value
            current_option = ""
        else:
            current_option += char

    return options


def _parse_single_query_option(option: str) -> tuple[str, str]:
    """
    Parse a single query option like "$select=name,email".

    Args:
        option: Single query option string

    Returns:
        Tuple of (option_name, option_value)

    Examples:
        >>> _parse_single_query_option("$select=name,email")
        ('$select', 'name,email')

        >>> _parse_single_query_option("$filter=active eq true")
        ('$filter', 'active eq true')

        >>> _parse_single_query_option("$top=5")
        ('$top', '5')
    """
    if "=" not in option:
        logger.warning(f"Invalid query option format: {option}")
        return "", ""

    # Split on first '=' only
    key, value = option.split("=", 1)
    key = key.strip()
    value = value.strip()

    # Validate that key starts with $
    if not key.startswith("$"):
        logger.warning(f"Query option must start with $: {key}")
        return "", ""

    return key, value


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
