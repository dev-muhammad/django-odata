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

from .optimization import optimize_queryset_for_expand, optimize_queryset_for_select
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

        # Apply optimizations using the extracted functions
        queryset = self._apply_odata_optimizations(queryset)

        # Apply OData query parameters
        return self.apply_odata_query(queryset)

    def _apply_odata_optimizations(self, queryset):
        """
        Apply OData optimizations using the extracted optimization functions.

        This method replaces the inline optimization logic with calls to the
        extracted functions for better maintainability and reusability.
        """
        odata_params = self.get_odata_query_params()

        # Parse expand fields for optimization
        expand_fields = {}
        if "$expand" in odata_params:
            expand_value = odata_params["$expand"]
            if isinstance(expand_value, list):
                expand_value = expand_value[0] if expand_value else ""
            if expand_value:
                expand_fields = parse_expand_fields_v2(expand_value)

        # Apply field selection optimization
        if "$select" in odata_params:
            select_fields = odata_params["$select"]
            if isinstance(select_fields, str):
                select_fields = [f.strip() for f in select_fields.split(",")]
            queryset = optimize_queryset_for_select(
                queryset, select_fields, expand_fields
            )

        # Apply expansion optimization
        if expand_fields:
            queryset = optimize_queryset_for_expand(queryset, expand_fields)

        return queryset

    # Removed _build_only_fields_list - now handled by optimize_queryset_for_select

    # Removed _optimize_queryset_for_expansions - now handled by _apply_odata_optimizations

    # Removed all optimization methods - now handled by extracted functions

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

        # Handle $count parameter (only include count when explicitly requested)
        odata_params = self.get_odata_query_params()
        include_count = (
            "$count" in odata_params and odata_params["$count"].lower() == "true"
        )

        # Calculate count if requested (BEFORE pagination to reflect total items)
        total_count = None
        if include_count:
            total_count = queryset.count()

        # Apply pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)

            # Get the paginated response from DRF
            paginated_response = self.get_paginated_response(serializer.data)

            # Transform DRF pagination format to OData format
            # DRF format: {"count": X, "next": "...", "previous": "...", "results": [...]}
            # OData format: {"@odata.context": "...", "@odata.count": X, "value": [...]}
            response_data = {"value": serializer.data}

            # Add count if requested
            if include_count:
                response_data["@odata.count"] = total_count

            # Add OData context for paginated responses
            if hasattr(self, "get_serializer_class"):
                serializer_class = self.get_serializer_class()
                if hasattr(serializer_class, "Meta") and hasattr(
                    serializer_class.Meta, "model"
                ):
                    model_name = serializer_class.Meta.model.__name__.lower()
                    response_data["@odata.context"] = (
                        f"{request.build_absolute_uri('/odata/')}$metadata#{model_name}s"
                    )

            # Optionally preserve DRF's next/previous links for client convenience
            # (Not part of OData spec, but useful for backward compatibility)
            if "next" in paginated_response.data:
                response_data["@odata.nextLink"] = paginated_response.data["next"]
            if "previous" in paginated_response.data:
                response_data["@odata.previousLink"] = paginated_response.data[
                    "previous"
                ]

            return Response(response_data)

        # Non-paginated response
        serializer = self.get_serializer(queryset, many=True)
        response_data = {"value": serializer.data}

        # Add count if requested
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
