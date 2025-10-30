"""
Mixin classes for adding OData functionality to Django REST Framework components.
"""

import logging
from typing import Any, Dict

from django.db.models import QuerySet
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .native_fields import parse_expand_fields
from .utils import (
    apply_odata_query_params,
    build_odata_metadata,
    parse_expand_fields_v2,
    parse_odata_query,
)

logger = logging.getLogger(__name__)


class ODataSerializerMixin:
    """
    Mixin for serializers to add OData-specific functionality.
    """

    def get_odata_context(self) -> Dict[str, Any]:
        """
        Get OData context information for the serializer.

        Returns:
            Dictionary containing OData context
        """
        context = {
            "odata_version": "4.0",
            "service_root": getattr(
                self.context.get("request"), "build_absolute_uri", lambda x: x
            )("/odata/"),
        }

        if hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            context["entity_set"] = self.Meta.model.__name__.lower() + "s"
            context["entity_type"] = self.Meta.model.__name__

        return context

    def to_representation(self, instance):
        """
        Add OData-specific representation logic.
        """
        data = super().to_representation(instance)

        # Add @odata.context if this is a single entity response
        request = self.context.get("request")
        if request and hasattr(self, "Meta") and hasattr(self.Meta, "model"):
            # Handle both DRF requests and mock requests safely
            query_params = getattr(request, "query_params", getattr(request, "GET", {}))
            headers = getattr(request, "headers", getattr(request, "META", {}))

            include_context = query_params.get("$format") == "json" or headers.get(
                "Accept", headers.get("HTTP_ACCEPT", "")
            ).startswith("application/json")

            if include_context and hasattr(instance, "pk"):
                odata_context = self.get_odata_context()
                data["@odata.context"] = (
                    f"{odata_context['service_root']}$metadata#{odata_context['entity_set']}/$entity"
                )

        return data

    # Note: Field selection and expansion are now handled by
    # NativeFieldSelectionMixin and NativeFieldExpansionMixin
    # No need for FlexFields-specific parameter mapping


class ODataMixin:
    """
    Mixin for ViewSets to add OData query support.
    """

    def get_odata_query_params(self) -> Dict[str, Any]:
        """
        Extract and parse OData query parameters from the request.

        Returns:
            Dictionary containing parsed OData query parameters
        """
        # Handle both DRF request (has query_params) and Django request (has GET)
        query_params = getattr(self.request, "query_params", self.request.GET)
        return parse_odata_query(query_params)

    def apply_odata_query(self, queryset: QuerySet) -> QuerySet:
        """
        Apply OData query parameters to the queryset.

        Args:
            queryset: Base queryset to filter

        Returns:
            Filtered and ordered queryset
        """
        odata_params = self.get_odata_query_params()

        try:
            queryset = apply_odata_query_params(queryset, odata_params)

            # Add any custom business logic here
            # For example, only show published posts to non-staff users
            user = getattr(self.request, "user", None)
            if user and not user.is_staff:
                if hasattr(queryset.model, "status"):
                    queryset = queryset.filter(status="published")
            return queryset
        except Exception as e:
            logger.error(f"Error applying OData query: {e}")
            # Return original queryset if query fails
            return queryset

    def get_queryset(self):
        """
        Get the queryset with OData query parameters applied and optimized for field selection and expanded relations.
        """
        queryset = super().get_queryset()

        # Apply field selection optimization BEFORE expansion optimization
        queryset = self._apply_field_selection_optimization(queryset)

        # Apply query optimizations for expanded relations
        queryset = self._optimize_queryset_for_expansions(queryset)

        # Apply OData query parameters
        return self.apply_odata_query(queryset)

    def _apply_field_selection_optimization(self, queryset):
        """
        Apply .only() to fetch only requested fields from database.

        This optimization reduces data transfer from database to application by
        fetching only the fields specified in the $select parameter.

        Algorithm:
        1. Get $select parameter from OData params
        2. If no $select, return queryset unchanged (fetch all fields)
        3. Parse selected fields
        4. Add model's primary key (required by Django)
        5. Add foreign key fields for any expanded relations (required by Django)
        6. Apply .only() with the field list

        Args:
            queryset: Base queryset to optimize

        Returns:
            Optimized queryset with .only() applied, or original queryset if no optimization needed

        Examples:
            >>> # Request: GET /posts?$select=id,title
            >>> # SQL: SELECT id, title FROM posts

            >>> # Request: GET /posts?$select=title&$expand=author
            >>> # SQL: SELECT id, title, author_id FROM posts (includes FK for expansion)
        """
        odata_params = self.get_odata_query_params()
        select_param = odata_params.get("$select")

        if not select_param:
            return queryset  # No optimization needed

        # Parse selected fields
        from .native_fields import parse_select_fields

        parsed = parse_select_fields(select_param)
        selected_fields = parsed["top_level"]

        if not selected_fields:
            return queryset  # Empty selection, return all fields

        # Build field list for .only()
        only_fields = self._build_only_fields_list(
            queryset.model, selected_fields, odata_params
        )

        if only_fields:
            queryset = queryset.only(*only_fields)
            logger.debug(
                f"Applied field selection optimization: only({', '.join(only_fields)})"
            )

        return queryset

    def _build_only_fields_list(self, model, selected_fields, odata_params):
        """
        Build list of fields for .only() method.

        Must include:
        - Requested fields from $select
        - Model's primary key (Django requirement)
        - Foreign key fields for expanded relations (Django requirement)

        Args:
            model: Django model class
            selected_fields: List of field names from $select parameter
            odata_params: Dictionary of OData query parameters

        Returns:
            List of field names to pass to .only()

        Examples:
            >>> _build_only_fields_list(Post, ['title'], {})
            ['id', 'title']  # Includes PK

            >>> _build_only_fields_list(Post, ['title'], {'$expand': 'author'})
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
        expand_param = odata_params.get("$expand")
        if expand_param:
            from .native_fields import parse_expand_fields

            expand_fields = parse_expand_fields(expand_param)

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

    def _optimize_queryset_for_expansions(self, queryset):
        """
        Automatically optimize queryset for expanded relations using select_related and prefetch_related.

        This method detects $expand parameters and applies appropriate eager loading to prevent N+1 queries.
        """
        expand_fields = self._get_expand_fields()
        if not expand_fields:
            return queryset

        select_related_fields, prefetch_related_fields = self._categorize_expand_fields(
            queryset.model, expand_fields
        )
        return self._apply_query_optimizations(
            queryset, select_related_fields, prefetch_related_fields
        )

    def _get_expand_fields(self) -> Dict[str, Any]:
        """Extract expand fields from OData parameters using native parser."""
        odata_params = self.get_odata_query_params()

        if "$expand" not in odata_params:
            return {}

        expand_value = odata_params["$expand"]
        if isinstance(expand_value, list):
            expand_value = expand_value[0] if expand_value else ""

        if not expand_value:
            return {}

        # Use native parser to extract field names and their options
        expand_dict = parse_expand_fields_v2(expand_value)
        return expand_dict

    def _categorize_expand_fields(self, model, expand_fields: Dict[str, Any]):
        """Categorize fields into select_related vs prefetch_related."""
        select_related_fields = []
        prefetch_related_fields = []

        for field_name in expand_fields.keys():  # Iterate over keys only
            if self._is_forward_relation(model, field_name):
                select_related_fields.append(field_name)
            else:
                prefetch_related_fields.append(field_name)

        return select_related_fields, prefetch_related_fields

    def _is_forward_relation(self, model, field_name):
        """Check if field is a forward relation (ForeignKey/OneToOne)."""
        try:
            field = model._meta.get_field(field_name)
            return hasattr(field, "related_model") and (
                field.many_to_one or field.one_to_one
            )
        except Exception:
            return False

    def _apply_query_optimizations(
        self, queryset, select_related_fields, prefetch_related_fields
    ):
        """Apply select_related and prefetch_related with field selection optimizations."""

        # Apply select_related with field selection
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)

            # Apply field selection for related models
            queryset = self._apply_related_field_selection(
                queryset, select_related_fields
            )

        # Apply prefetch_related with field selection
        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)

            # Apply field selection for prefetched models
            queryset = self._apply_prefetch_field_selection(
                queryset, prefetch_related_fields
            )

        return queryset

    def _apply_related_field_selection(self, queryset, select_related_fields):
        """
        Apply field selection to select_related fields using only().

        For each related field, determine which fields to fetch based on
        nested $select in $expand parameter.

        Args:
            queryset: Queryset with select_related already applied
            select_related_fields: List of field names that were select_related

        Returns:
            Queryset with only() applied for related fields

        Examples:
            >>> # Request: GET /posts?$expand=author($select=name)
            >>> # Adds: .only('author__id', 'author__name')
        """
        odata_params = self.get_odata_query_params()
        expand_param = odata_params.get("$expand")

        if not expand_param:
            return queryset

        # Parse expand to get nested selections
        from .utils import parse_expand_fields_v2

        expand_fields = parse_expand_fields_v2(expand_param)

        # Build only() field list including related fields
        only_fields = []

        for related_field in select_related_fields:
            if related_field in expand_fields:
                nested_select = expand_fields[related_field].get("$select")

                if nested_select:
                    # Parse nested $select
                    from .native_fields import parse_select_fields

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

        if only_fields:
            # Get existing only() fields from main queryset
            existing_only = self._get_existing_only_fields(queryset)
            if existing_only:
                only_fields.extend(existing_only)

            queryset = queryset.only(*only_fields)
            logger.debug(
                f"Applied related field selection: only({', '.join(only_fields)})"
            )

        return queryset

    def _get_existing_only_fields(self, queryset):
        """
        Extract existing only() fields from queryset.

        Args:
            queryset: Django queryset

        Returns:
            List of field names currently in only(), or empty list

        Examples:
            >>> qs = Model.objects.only('id', 'name')
            >>> _get_existing_only_fields(qs)
            ['id', 'name']
        """
        deferred_loading = getattr(queryset.query, "deferred_loading", (None, None))
        if deferred_loading[0]:  # Has only() fields
            return list(deferred_loading[0])
        return []

    def _apply_prefetch_field_selection(self, queryset, prefetch_related_fields):
        """
        Apply field selection to prefetch_related fields using Prefetch objects.

        For each prefetch_related field, create a Prefetch object with a custom
        queryset that uses only() to limit fields based on nested $select.

        Args:
            queryset: Queryset with prefetch_related already applied
            prefetch_related_fields: List of field names that were prefetch_related

        Returns:
            Queryset with optimized Prefetch objects

        Examples:
            >>> # Request: GET /posts?$expand=categories($select=name)
            >>> # Creates: Prefetch('categories', queryset=Category.objects.only('id', 'name'))
        """
        from django.db.models import Prefetch

        odata_params = self.get_odata_query_params()
        expand_param = odata_params.get("$expand")

        if not expand_param:
            return queryset

        # Parse expand to get nested selections
        from .utils import parse_expand_fields_v2

        expand_fields = parse_expand_fields_v2(expand_param)

        # Build list of Prefetch objects
        prefetch_objects = []

        for prefetch_field in prefetch_related_fields:
            if prefetch_field in expand_fields:
                nested_select = expand_fields[prefetch_field].get("$select")

                if nested_select:
                    # Parse nested $select
                    from .native_fields import parse_select_fields

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

    def get_serializer_context(self):
        """
        Add OData context to serializer.
        """
        context = super().get_serializer_context()
        context["odata_params"] = self.get_odata_query_params()
        return context

    def list(self, request, *args, **kwargs):
        """
        Enhanced list method with OData response formatting.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Handle $count parameter
        odata_params = self.get_odata_query_params()
        include_count = (
            "$count" in odata_params and odata_params["$count"].lower() == "true"
        )

        if include_count:
            total_count = queryset.count()

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data

            if include_count:
                response_data["@odata.count"] = total_count

            return Response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = {"value": serializer.data}

        if include_count:
            response_data["@odata.count"] = total_count

        # Add OData context
        if hasattr(self, "get_serializer_class"):
            serializer_class = self.get_serializer_class()
            if hasattr(serializer_class, "Meta") and hasattr(
                serializer_class.Meta, "model"
            ):
                model_name = serializer_class.Meta.model.__name__.lower()
                response_data["@odata.context"] = (
                    f"{request.build_absolute_uri('/odata/')}$metadata#{model_name}s"
                )

        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        """
        Enhanced retrieve method with OData response formatting.
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Http404:
            # Return OData-style 404 response
            return Response(
                {
                    "error": {
                        "code": "NotFound",
                        "message": "The requested resource was not found.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["get"], url_path=r"\$metadata")
    def metadata(self, request):
        """
        Return OData metadata document.
        """
        try:
            serializer_class = self.get_serializer_class()
            model_class = getattr(serializer_class.Meta, "model", None)

            if not model_class:
                return Response(
                    {
                        "error": {
                            "code": "InternalError",
                            "message": "No model class found for metadata generation.",
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            metadata = build_odata_metadata(model_class, serializer_class)

            # Build full OData metadata document
            metadata_doc = {
                "$Version": "4.0",
                "$EntityContainer": f"{model_class._meta.app_label}.Container",
                f"{model_class._meta.app_label}": {
                    "$Alias": "Self",
                    "$Kind": "Schema",
                    model_class.__name__: {
                        "$Kind": "EntityType",
                        "$Key": [
                            "id"
                        ],  # Assume 'id' is the key, could be made configurable
                        **{
                            prop_name: {"$Type": prop_info["type"]}
                            for prop_name, prop_info in metadata["properties"].items()
                        },
                    },
                    "Container": {
                        "$Kind": "EntityContainer",
                        f"{model_class.__name__.lower()}s": {
                            "$Collection": True,
                            "$Type": f"Self.{model_class.__name__}",
                        },
                    },
                },
            }

            return Response(metadata_doc, content_type="application/json")

        except Exception as e:
            logger.error(f"Error generating metadata: {e}")
            return Response(
                {
                    "error": {
                        "code": "InternalError",
                        "message": "Error generating metadata document.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="")
    def service_document(self, request):
        """
        Return OData service document.
        """
        try:
            serializer_class = self.get_serializer_class()
            model_class = getattr(serializer_class.Meta, "model", None)

            if not model_class:
                return Response(
                    {
                        "error": {
                            "code": "InternalError",
                            "message": "No model class found for service document generation.",
                        }
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            service_doc = {
                "@odata.context": f"{request.build_absolute_uri('/odata/')}$metadata",
                "value": [
                    {
                        "name": f"{model_class.__name__.lower()}s",
                        "kind": "EntitySet",
                        "url": f"{model_class.__name__.lower()}s",
                    }
                ],
            }

            return Response(service_doc)

        except Exception as e:
            logger.error(f"Error generating service document: {e}")
            return Response(
                {
                    "error": {
                        "code": "InternalError",
                        "message": "Error generating service document.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
