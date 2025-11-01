"""
OData QuerySet Optimization Functions

Extracted from ODataMixin to provide reusable QuerySet optimization logic
that can be used independently of DRF serializers and views.
"""

import logging
from typing import Any, Dict, List, Tuple

from django.db.models import Prefetch, QuerySet

from .native_fields import parse_select_fields

logger = logging.getLogger(__name__)


def optimize_queryset_for_select(
    queryset: QuerySet, select_fields: List[str], expand_fields: Dict[str, Any] = None
) -> QuerySet:
    """
    Apply .only() optimization for field selection.

    This optimization reduces data transfer from database to application by
    fetching only the fields specified in the $select parameter.

    Algorithm:
    1. If no $select, return queryset unchanged (fetch all fields)
    2. Parse selected fields
    3. Add model's primary key (required by Django)
    4. Add foreign key fields for any expanded relations (required by Django)
    5. Apply .only() with the field list

    Args:
        queryset: Base queryset to optimize
        select_fields: List of field names from $select parameter
        expand_fields: Dictionary of expanded fields

    Returns:
        Optimized queryset with .only() applied, or original queryset if no optimization needed

    Examples:
        >>> # Request: GET /posts?$select=id,title
        >>> # SQL: SELECT id, title FROM posts

        >>> # Request: GET /posts?$select=title&$expand=author
        >>> # SQL: SELECT id, title, author_id FROM posts (includes FK for expansion)
    """
    if not select_fields:
        return queryset  # No optimization needed

    # Build field list for .only()
    only_fields = build_only_fields_list(
        queryset.model, select_fields, expand_fields or {}
    )

    if only_fields:
        queryset = queryset.only(*only_fields)
        logger.debug(
            f"Applied field selection optimization: only({', '.join(only_fields)})"
        )

    return queryset


def optimize_queryset_for_expand(
    queryset: QuerySet, expand_fields: Dict[str, Any]
) -> QuerySet:
    """
    Automatically optimize queryset for expanded relations using select_related and prefetch_related.

    This method detects $expand parameters and applies appropriate eager loading to prevent N+1 queries.

    Args:
        queryset: Base queryset to optimize
        expand_fields: Dictionary mapping field names to their OData options

    Returns:
        Queryset with select_related/prefetch_related applied

    Examples:
        >>> # Request: GET /posts?$expand=author
        >>> # Result: BlogPost.objects.select_related('author')

        >>> # Request: GET /posts?$expand=categories
        >>> # Result: BlogPost.objects.prefetch_related('categories')
    """
    if not expand_fields:
        return queryset

    # Categorize relations
    select_related_fields, prefetch_related_fields = categorize_relations(
        queryset.model, list(expand_fields.keys())
    )

    return apply_query_optimizations(
        queryset, select_related_fields, prefetch_related_fields, expand_fields
    )


def build_only_fields_list(
    model, selected_fields: List[str], expand_fields: Dict[str, Any]
) -> List[str]:
    """
    Build list of fields for .only() method.

    Must include:
    - Requested fields from $select
    - Model's primary key (Django requirement)
    - Foreign key fields for expanded relations (Django requirement)

    Args:
        model: Django model class
        selected_fields: List of field names from $select parameter
        expand_fields: Dictionary of expanded fields

    Returns:
        List of field names to pass to .only()

    Examples:
        >>> build_only_fields_list(Post, ['title'], {})
        ['id', 'title']  # Includes PK

        >>> build_only_fields_list(Post, ['title'], {'author': {}})
        ['id', 'title', 'author_id']  # Includes PK and FK
    """
    only_fields = set()

    # Always include primary key
    pk_field = model._meta.pk.name
    only_fields.add(pk_field)

    # Add only valid database fields from selected_fields
    for field_name in selected_fields:
        try:
            # Validate that field exists on model
            model._meta.get_field(field_name)
            only_fields.add(field_name)
        except Exception:
            # Field doesn't exist or is a property - skip it
            logger.debug(f"Skipping non-database field '{field_name}' in $select")

    # Add foreign key fields for expanded relations
    for field_name in expand_fields.keys():
        # Check if it's a forward relation (has FK field)
        try:
            field = model._meta.get_field(field_name)
            # FK and OneToOne fields have 'attname' (e.g., 'author_id' for 'author')
            if hasattr(field, "attname"):
                only_fields.add(field.attname)
                logger.debug(
                    f"Added FK field '{field.attname}' for expansion of '{field_name}'"
                )
        except Exception as e:
            logger.debug(f"Could not add FK for '{field_name}': {e}")

    return list(only_fields)


def categorize_relations(model, field_names: List[str]) -> Tuple[List[str], List[str]]:
    """
    Categorize fields into select_related vs prefetch_related.

    Args:
        model: Django model class
        field_names: List of field names to categorize

    Returns:
        Tuple of (select_related_fields, prefetch_related_fields)

    Examples:
        >>> categorize_relations(BlogPost, ['author', 'categories'])
        (['author'], ['categories'])  # FK → select_related, M2M → prefetch_related
    """
    select_related = []
    prefetch_related = []

    for field_name in field_names:
        if is_forward_relation(model, field_name):
            select_related.append(field_name)
        else:
            prefetch_related.append(field_name)

    return select_related, prefetch_related


def is_forward_relation(model, field_name: str) -> bool:
    """
    Check if field is a forward relation (ForeignKey/OneToOne).

    Args:
        model: Django model class
        field_name: Name of the field to check

    Returns:
        True if forward relation, False otherwise
    """
    try:
        field = model._meta.get_field(field_name)
        return hasattr(field, "related_model") and (
            field.many_to_one or field.one_to_one
        )
    except Exception:
        return False


def apply_query_optimizations(
    queryset: QuerySet,
    select_related_fields: List[str],
    prefetch_related_fields: List[str],
    expand_fields: Dict[str, Any] = None,
) -> QuerySet:
    """
    Apply select_related and prefetch_related with field selection optimizations.

    Args:
        queryset: Base queryset
        select_related_fields: Fields to select_related
        prefetch_related_fields: Fields to prefetch_related
        expand_fields: Dictionary of expanded fields with options

    Returns:
        Queryset with optimizations applied
    """
    expand_fields = expand_fields or {}

    # Apply select_related with field selection
    if select_related_fields:
        # Handle deep expansion by extending select_related_fields
        extended_select_related = list(select_related_fields)
        for field in select_related_fields:
            if field in expand_fields:
                nested_expand = expand_fields[field].get("$expand")
                if nested_expand:
                    from .native_fields import parse_expand_fields

                    nested_relations = parse_expand_fields(nested_expand)
                    extended_select_related.extend(
                        [f"{field}__{rel}" for rel in nested_relations]
                    )

        queryset = queryset.select_related(*extended_select_related)
        queryset = apply_related_field_selection(
            queryset, select_related_fields, expand_fields
        )

    # Apply prefetch_related with field selection
    if prefetch_related_fields:
        queryset = queryset.prefetch_related(*prefetch_related_fields)
        queryset = apply_prefetch_field_selection(
            queryset, prefetch_related_fields, expand_fields
        )

    return queryset


def apply_related_field_selection(
    queryset: QuerySet, select_related_fields: List[str], expand_fields: Dict[str, Any]
) -> QuerySet:
    """
    Apply field selection to select_related fields using only().

    For each related field, determine which fields to fetch based on
    nested $select in $expand parameter.

    Args:
        queryset: Queryset with select_related already applied
        select_related_fields: List of field names that were select_related
        expand_fields: Dictionary of expanded fields with options

    Returns:
        Queryset with only() applied for related fields

    Examples:
        >>> # Request: GET /posts?$expand=author($select=name)
        >>> # Adds: .only('author__id', 'author__name')
    """
    # Build only() field list including related fields
    only_fields = []

    for related_field in select_related_fields:
        if related_field in expand_fields:
            nested_select = expand_fields[related_field].get("$select")
            nested_expand = expand_fields[related_field].get("$expand")

            if nested_select:
                # Parse nested $select
                parsed = parse_select_fields(nested_select)
                nested_fields = parsed["top_level"]

                # Get related model
                try:
                    field = queryset.model._meta.get_field(related_field)
                    related_model = field.related_model
                    pk_field = related_model._meta.pk.name

                    # Add pk field
                    only_fields.append(f"{related_field}__{pk_field}")

                    # Add only actual database fields (not properties)
                    for nested_field in nested_fields:
                        try:
                            # Check if this is a real database field
                            related_model._meta.get_field(nested_field)
                            only_fields.append(f"{related_field}__{nested_field}")
                        except Exception:
                            # Field doesn't exist or is a property - skip it
                            logger.debug(
                                f"Skipping non-database field '{nested_field}' "
                                f"for related model '{related_field}'"
                            )

                    logger.debug(
                        f"Added related field selection for '{related_field}': "
                        f"{', '.join([f for f in only_fields if f.startswith(related_field)])}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not optimize fields for {related_field}: {e}"
                    )

            # Handle nested $expand for deep expansion
            if nested_expand:
                # Parse nested $expand to get related fields
                from .native_fields import parse_expand_fields

                nested_relations = parse_expand_fields(nested_expand)

                # Add foreign key fields for nested relations
                for nested_rel in nested_relations:
                    try:
                        field = queryset.model._meta.get_field(related_field)
                        related_model = field.related_model
                        nested_field = related_model._meta.get_field(nested_rel)

                        # Add FK field for nested relation
                        if hasattr(nested_field, "attname"):
                            only_fields.append(
                                f"{related_field}__{nested_field.attname}"
                            )
                            logger.debug(
                                f"Added nested FK field '{related_field}__{nested_field.attname}' "
                                f"for deep expansion of '{related_field}__{nested_rel}'"
                            )
                    except Exception as e:
                        logger.debug(
                            f"Could not add nested FK for '{related_field}__{nested_rel}': {e}"
                        )

    if only_fields:
        # Get existing only() fields from main queryset
        existing_only = get_existing_only_fields(queryset)
        if existing_only:
            only_fields.extend(existing_only)

        queryset = queryset.only(*only_fields)
        logger.debug(f"Applied related field selection: only({', '.join(only_fields)})")

    return queryset


def apply_prefetch_field_selection(
    queryset: QuerySet,
    prefetch_related_fields: List[str],
    expand_fields: Dict[str, Any],
) -> QuerySet:
    """
    Apply field selection to prefetch_related fields using Prefetch objects.

    For each prefetch_related field, create a Prefetch object with a custom
    queryset that uses only() to limit fields based on nested $select.

    Args:
        queryset: Queryset with prefetch_related already applied
        prefetch_related_fields: List of field names that were prefetch_related
        expand_fields: Dictionary of expanded fields with options

    Returns:
        Queryset with optimized Prefetch objects

    Examples:
        >>> # Request: GET /posts?$expand=categories($select=name)
        >>> # Creates: Prefetch('categories', queryset=Category.objects.only('id', 'name'))
    """
    # Build list of Prefetch objects
    prefetch_objects = []

    for prefetch_field in prefetch_related_fields:
        if prefetch_field in expand_fields:
            nested_select = expand_fields[prefetch_field].get("$select")

            if nested_select:
                # Parse nested $select
                parsed = parse_select_fields(nested_select)
                nested_fields = parsed["top_level"]

                # Get related model
                try:
                    # Handle both forward and reverse relations
                    field = None
                    related_model = None

                    # Try to get field from model meta
                    try:
                        field = queryset.model._meta.get_field(prefetch_field)
                        related_model = field.related_model
                    except Exception:
                        # Might be a reverse relation, try to find it
                        for rel in queryset.model._meta.related_objects:
                            if rel.get_accessor_name() == prefetch_field:
                                related_model = rel.related_model
                                break

                    if related_model:
                        pk_field = related_model._meta.pk.name

                        # Build only() field list for prefetch queryset
                        only_fields = [pk_field]

                        # Add only actual database fields (not properties)
                        for nested_field in nested_fields:
                            try:
                                # Check if this is a real database field
                                related_model._meta.get_field(nested_field)
                                only_fields.append(nested_field)
                            except Exception:
                                # Field doesn't exist or is a property - skip it
                                logger.debug(
                                    f"Skipping non-database field '{nested_field}' "
                                    f"for prefetch model '{prefetch_field}'"
                                )

                        # Create Prefetch object with optimized queryset
                        prefetch_queryset = related_model.objects.only(*only_fields)
                        prefetch_obj = Prefetch(
                            prefetch_field, queryset=prefetch_queryset
                        )
                        prefetch_objects.append(prefetch_obj)

                        logger.debug(
                            f"Created Prefetch for '{prefetch_field}' with fields: "
                            f"{', '.join(only_fields)}"
                        )
                    else:
                        logger.warning(
                            f"Could not find related model for prefetch field '{prefetch_field}'"
                        )
                except Exception as e:
                    logger.warning(
                        f"Could not optimize prefetch for {prefetch_field}: {e}"
                    )

    if prefetch_objects:
        # Clear existing prefetch_related and apply optimized Prefetch objects
        queryset = queryset._clone()
        queryset._prefetch_related_lookups = ()
        queryset = queryset.prefetch_related(*prefetch_objects)

        # Also add any prefetch fields that didn't have nested $select
        remaining_fields = [
            f
            for f in prefetch_related_fields
            if f
            not in [
                p.prefetch_to if isinstance(p, Prefetch) else p
                for p in prefetch_objects
            ]
        ]
        if remaining_fields:
            queryset = queryset.prefetch_related(*remaining_fields)

        logger.debug(
            f"Applied prefetch field selection with {len(prefetch_objects)} Prefetch objects"
        )

    return queryset


def get_existing_only_fields(queryset: QuerySet) -> List[str]:
    """
    Extract existing only() fields from queryset.

    Args:
        queryset: Django queryset

    Returns:
        List of field names currently in only(), or empty list

    Examples:
        >>> qs = Model.objects.only('id', 'name')
        >>> get_existing_only_fields(qs)
        ['id', 'name']
    """
    deferred_loading = getattr(queryset.query, "deferred_loading", (None, None))
    if deferred_loading[0]:  # Has only() fields
        return list(deferred_loading[0])
    return []
