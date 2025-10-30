"""
OData-compatible serializers with native field selection and expansion.
"""

from typing import Any, Dict

from rest_framework import serializers

from .mixins import ODataSerializerMixin
from .native_fields import NativeFieldSelectionMixin, NativeFieldExpansionMixin


class ODataSerializer(
    ODataSerializerMixin,
    NativeFieldSelectionMixin,
    NativeFieldExpansionMixin,
    serializers.Serializer
):
    """
    Base OData serializer with native field selection and expansion.

    This serializer provides:
    - Dynamic field selection via $select parameter
    - Field expansion via $expand parameter
    - OData context information
    - Support for OData query options

    The serializer uses native implementations instead of drf-flex-fields,
    providing better performance and simpler maintenance.
    """
    pass


class ODataModelSerializer(
    ODataSerializerMixin,
    NativeFieldSelectionMixin,
    NativeFieldExpansionMixin,
    serializers.ModelSerializer
):
    """
    OData-compatible model serializer with native field selection and expansion.

    This serializer provides:
    - Dynamic field selection via $select parameter
    - Field expansion via $expand parameter
    - OData context information
    - Support for OData query options ($select, $expand)
    - Automatic field type detection for metadata generation

    The serializer uses native implementations instead of drf-flex-fields,
    providing better performance and simpler maintenance.
    """

    def get_field_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed field information for metadata generation.

        Returns:
            Dictionary mapping field names to field metadata
        """
        field_info = {}
        fields = self.get_fields()

        for field_name, field in fields.items():
            field_info[field_name] = {
                "type": self._get_odata_type(field),
                "nullable": not field.required,
                "read_only": field.read_only,
                "max_length": getattr(field, "max_length", None),
                "choices": getattr(field, "choices", None),
            }

        return field_info

    def _get_odata_type(self, field) -> str:
        """
        Map DRF field types to OData types.

        Args:
            field: DRF field instance

        Returns:
            OData type string
        """
        field_type_mapping = {
            serializers.CharField: "Edm.String",
            serializers.EmailField: "Edm.String",
            serializers.URLField: "Edm.String",
            serializers.SlugField: "Edm.String",
            serializers.UUIDField: "Edm.Guid",
            serializers.IntegerField: "Edm.Int32",
            serializers.FloatField: "Edm.Double",
            serializers.DecimalField: "Edm.Decimal",
            serializers.BooleanField: "Edm.Boolean",
            serializers.DateField: "Edm.Date",
            serializers.DateTimeField: "Edm.DateTimeOffset",
            serializers.TimeField: "Edm.TimeOfDay",
            serializers.DurationField: "Edm.Duration",
            serializers.FileField: "Edm.String",
            serializers.ImageField: "Edm.String",
            serializers.JSONField: "Edm.String",
            serializers.DictField: "Edm.String",
            serializers.ListField: "Collection(Edm.String)",
        }

        field_type = type(field)
        return field_type_mapping.get(field_type, "Edm.String")

    def get_navigation_properties(self) -> Dict[str, Dict[str, Any]]:
        """
        Get navigation property information from expandable_fields.

        Returns:
            Dictionary mapping navigation property names to metadata
        """
        nav_props = {}

        if hasattr(self.Meta, "expandable_fields"):
            for field_name, config in self.Meta.expandable_fields.items():
                nav_props[field_name] = {
                    "target_type": (
                        config[0] if isinstance(config, tuple) else str(config)
                    ),
                    "many": (
                        config[1].get("many", False)
                        if isinstance(config, tuple) and len(config) > 1
                        else False
                    ),
                    "nullable": True,  # Default assumption
                }

        return nav_props

    class Meta:
        abstract = True


class ODataListSerializer(serializers.ListSerializer):
    """
    Custom list serializer for OData collections.
    """

    def to_representation(self, data):
        """
        Add OData collection formatting.
        """
        items = super().to_representation(data)

        # Check if we should wrap in OData format
        request = self.context.get("request")
        if request and "$format" in request.query_params:
            return {"@odata.context": self._get_context_url(), "value": items}

        return items

    def _get_context_url(self) -> str:
        """
        Generate OData context URL for collections.
        """
        request = self.context.get("request")
        if (
            request
            and hasattr(self.child, "Meta")
            and hasattr(self.child.Meta, "model")
        ):
            model_name = self.child.Meta.model.__name__.lower()
            base_url = request.build_absolute_uri("/odata/")
            return f"{base_url}$metadata#{model_name}s"

        return ""


# Convenience function for creating OData serializers
def create_odata_serializer(
    model_class, fields="__all__", expandable_fields=None, **kwargs
):
    """
    Factory function to create OData serializers for Django models.

    Args:
        model_class: Django model class
        fields: Fields to include in serialization
        expandable_fields: Dictionary of expandable field configurations
        **kwargs: Additional serializer options

    Returns:
        ODataModelSerializer subclass for the model
    """
    expandable_fields = expandable_fields or {}

    # Create Meta class with proper variable scope
    meta_attrs = {
        "model": model_class,
        "fields": fields,
        "expandable_fields": expandable_fields,
        "list_serializer_class": ODataListSerializer,
    }

    # Add any additional meta attributes
    for key, value in kwargs.items():
        if key.startswith("meta_"):
            meta_attrs[key[5:]] = value

    # Create Meta class dynamically
    Meta = type("Meta", (), meta_attrs)

    # Create the serializer class
    serializer_name = f"{model_class.__name__}ODataSerializer"
    serializer_class = type(serializer_name, (ODataModelSerializer,), {"Meta": Meta})

    return serializer_class
