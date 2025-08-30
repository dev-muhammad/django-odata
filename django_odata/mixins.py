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

from .utils import apply_odata_query_params, build_odata_metadata, parse_odata_query

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

    def __init__(self, *args, **kwargs):
        # Process OData params BEFORE calling super().__init__
        # so that drf-flex-fields sees the updated query_params
        self._process_odata_params_before_init(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def _process_odata_params_before_init(self, *args, **kwargs):
        """
        Process OData-specific query parameters before initialization.
        This ensures drf-flex-fields sees the mapped parameters.
        """
        context = self._extract_context(*args, **kwargs)
        if not context:
            return

        odata_params = context.get("odata_params", {})
        request = context.get("request")

        if not request or not odata_params:
            return

        select_fields, expand_fields = self._process_select_and_expand(odata_params)
        self._update_request_params(request, select_fields, expand_fields)

    def _extract_context(self, *args, **kwargs):
        """Extract context from args or kwargs."""
        context = kwargs.get("context")
        if context is None and len(args) > 0:
            # Check if first arg has context
            if hasattr(args[0], "context"):
                context = args[0].context
        return context

    def _process_select_and_expand(self, odata_params):
        """Process $select and $expand parameters."""
        select_fields = []
        expand_fields = []

        # Handle $select parameter
        if "$select" in odata_params:
            select_value = odata_params["$select"]
            if isinstance(select_value, list):
                select_value = select_value[0] if select_value else ""
            select_fields = [f.strip() for f in select_value.split(",") if f.strip()]

        # Handle $expand parameter
        nested_field_selections = []
        if "$expand" in odata_params:
            expand_value = odata_params["$expand"]
            if isinstance(expand_value, list):
                expand_value = expand_value[0] if expand_value else ""
            expand_fields, nested_field_selections = self._parse_expand_expression(
                expand_value
            )

        # Auto-add expanded properties to select fields
        for expand_field in expand_fields:
            if expand_field not in select_fields:
                select_fields.append(expand_field)

        # Add nested field selections to the main select fields
        select_fields.extend(nested_field_selections)

        return select_fields, expand_fields

    def _update_request_params(self, request, select_fields, expand_fields):
        """Update request query parameters with processed fields."""
        # Import QueryDict here to avoid circular imports
        from django.http import QueryDict

        # Ensure query_params exists and is mutable
        if not hasattr(request, "query_params"):
            request.query_params = QueryDict(mutable=True)
        elif hasattr(request.query_params, "_mutable"):
            request.query_params._mutable = True

        # Set the processed fields only if we have specific fields to select
        if select_fields:
            request.query_params["fields"] = ",".join(select_fields)

        # Set expand fields if any
        if expand_fields:
            request.query_params["expand"] = ",".join(expand_fields)

        if hasattr(request.query_params, "_mutable"):
            request.query_params._mutable = False

    def _parse_expand_expression(self, expand_value):
        """
        Parse OData $expand expressions and convert them to drf-flex-fields format.

        Supports:
        - Simple: "author"
        - Multiple: "author,categories"
        - Nested with $select: "posts($select=id,title,slug,status)"
        - Mixed: "author,posts($select=id,title)"

        Returns tuple: (expand_fields, nested_field_selections)
        """
        if not expand_value:
            return [], []

        expand_fields = []
        nested_field_selections = []

        # Split by comma, but be careful with nested expressions
        current_field = ""
        paren_depth = 0

        for char in expand_value + ",":  # Add comma to process last field
            if char == "(" and not paren_depth:
                # Start of nested expression
                paren_depth += 1
                current_field += char
            elif char == "(":
                paren_depth += 1
                current_field += char
            elif char == ")":
                paren_depth -= 1
                current_field += char
            elif char == "," and paren_depth == 0:
                # End of field at top level
                if current_field.strip():
                    field_name, nested_fields = self._process_expand_field(
                        current_field.strip()
                    )
                    expand_fields.append(field_name)
                    nested_field_selections.extend(nested_fields)
                current_field = ""
            else:
                current_field += char

        return expand_fields, nested_field_selections

    def _process_expand_field(self, field):
        """
        Process a single expand field, converting OData nested syntax to drf-flex-fields format.

        Converts: "posts($select=id,title,slug,status)"
        To: returns tuple ("posts", ["posts.id", "posts.title", "posts.slug", "posts.status"])

        For simple fields like "posts", returns ("posts", [])
        """
        if "($select=" not in field:
            # Simple field without nested selection
            return field, []

        # Parse nested expression: field_name($select=field1,field2,...)
        field_name = field.split("(")[0]

        # Extract the content inside parentheses
        start_paren = field.find("(")
        end_paren = field.rfind(")")

        if start_paren == -1 or end_paren == -1:
            return field, []  # Malformed, return as simple field

        inner_content = field[start_paren + 1 : end_paren]

        # Parse the $select parameter
        if inner_content.startswith("$select="):
            select_fields = inner_content[8:]  # Remove "$select="
            nested_fields = [
                f"{field_name}.{f.strip()}"
                for f in select_fields.split(",")
                if f.strip()
            ]
            return field_name, nested_fields

        return field, []  # Return as simple field if not a $select expression


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
            return apply_odata_query_params(queryset, odata_params)
        except Exception as e:
            logger.error(f"Error applying OData query: {e}")
            # Return original queryset if query fails
            return queryset

    def get_queryset(self):
        """
        Get the queryset with OData query parameters applied and optimized for expanded relations.
        """
        queryset = super().get_queryset()

        # Apply query optimizations for expanded relations
        queryset = self._optimize_queryset_for_expansions(queryset)

        # Apply OData query parameters
        return self.apply_odata_query(queryset)

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

    def _get_expand_fields(self):
        """Extract expand fields from OData parameters."""
        odata_params = self.get_odata_query_params()

        if "$expand" not in odata_params:
            return []

        expand_value = odata_params["$expand"]
        if isinstance(expand_value, list):
            expand_value = expand_value[0] if expand_value else ""

        if not expand_value:
            return []

        expand_fields, _ = self._parse_expand_expression(expand_value)
        return expand_fields

    def _categorize_expand_fields(self, model, expand_fields):
        """Categorize fields into select_related vs prefetch_related."""
        select_related_fields = []
        prefetch_related_fields = []

        for field_name in expand_fields:
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
        """Apply select_related and prefetch_related optimizations."""
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)

        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)

        return queryset

    def _parse_expand_expression(self, expand_value):
        """
        Parse OData $expand expressions to extract field names.

        This is a simplified version that just extracts the main field names for optimization.
        The full parsing is done in the serializer mixin.
        """
        if not expand_value:
            return [], []

        expand_fields = []

        # Split by comma, but be careful with nested expressions
        current_field = ""
        paren_depth = 0

        for char in expand_value + ",":  # Add comma to process last field
            if char == "(" and not paren_depth:
                # Start of nested expression
                paren_depth += 1
                current_field += char
            elif char == "(":
                paren_depth += 1
                current_field += char
            elif char == ")":
                paren_depth -= 1
                current_field += char
            elif char == "," and paren_depth == 0:
                # End of field at top level
                if current_field.strip():
                    # Extract just the field name (before any parentheses)
                    field_name = current_field.strip().split("(")[0]
                    expand_fields.append(field_name)
                current_field = ""
            else:
                current_field += char

        return expand_fields, []

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
