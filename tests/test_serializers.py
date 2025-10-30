"""
Tests for django_odata.serializers module.
"""

import pytest

# Test models for serializer tests
from django.db import models
from django.http import QueryDict
from django.test import TestCase
from rest_framework import serializers

from django_odata.serializers import (
    ODataModelSerializer,
    ODataSerializer,
    create_odata_serializer,
)


class SerializerTestModel(models.Model):
    """Test model for serializer tests."""

    name = models.CharField(max_length=100)
    value = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tests"


class SerializerRelatedModel(models.Model):
    """Related test model."""

    test_model = models.ForeignKey(
        SerializerTestModel, on_delete=models.CASCADE, related_name="related_items"
    )
    description = models.TextField()

    class Meta:
        app_label = "tests"


class TestODataModelSerializer(TestCase):
    """Test ODataModelSerializer functionality."""

    def setUp(self):
        """Set up test serializer."""

        class SerializerTestModelSerializer(ODataModelSerializer):
            class Meta:
                model = SerializerTestModel
                fields = ["id", "name", "value", "is_active", "created_at"]
                expandable_fields = {
                    "related_items": (
                        "tests.test_serializers.RelatedModelSerializer",
                        {"many": True},
                    )
                }

        self.serializer_class = SerializerTestModelSerializer

    def test_serializer_initialization(self):
        """Test that the serializer can be initialized."""
        serializer = self.serializer_class()
        self.assertIsInstance(serializer, ODataModelSerializer)

    def test_get_field_info(self):
        """Test getting field information for metadata."""
        serializer = self.serializer_class()
        field_info = serializer.get_field_info()

        self.assertIn("name", field_info)
        self.assertIn("value", field_info)
        self.assertIn("is_active", field_info)

        # Check field type mapping
        name_info = field_info["name"]
        self.assertEqual(name_info["type"], "Edm.String")

        value_info = field_info["value"]
        self.assertEqual(value_info["type"], "Edm.Int32")

        active_info = field_info["is_active"]
        self.assertEqual(active_info["type"], "Edm.Boolean")

    def test_get_navigation_properties(self):
        """Test getting navigation properties."""
        serializer = self.serializer_class()
        nav_props = serializer.get_navigation_properties()

        self.assertIn("related_items", nav_props)
        related_info = nav_props["related_items"]
        self.assertTrue(related_info["many"])
        self.assertEqual(
            related_info["target_type"], "tests.test_serializers.RelatedModelSerializer"
        )

    def test_odata_type_mapping(self):
        """Test OData type mapping for different field types."""
        serializer = self.serializer_class()

        # Test various field types
        field_mappings = {
            serializers.CharField(): "Edm.String",
            serializers.IntegerField(): "Edm.Int32",
            serializers.BooleanField(): "Edm.Boolean",
            serializers.DateTimeField(): "Edm.DateTimeOffset",
            serializers.DecimalField(max_digits=10, decimal_places=2): "Edm.Decimal",
            serializers.EmailField(): "Edm.String",
            serializers.UUIDField(): "Edm.Guid",
        }

        for field, expected_type in field_mappings.items():
            result_type = serializer._get_odata_type(field)
            self.assertEqual(result_type, expected_type)


class TestODataSerializer(TestCase):
    """Test ODataSerializer functionality."""

    def setUp(self):
        """Set up test serializer."""

        class TestSerializer(ODataSerializer):
            name = serializers.CharField()
            value = serializers.IntegerField()

        self.serializer_class = TestSerializer

    def test_serializer_initialization(self):
        """Test that the serializer can be initialized."""
        serializer = self.serializer_class()
        self.assertIsInstance(serializer, ODataSerializer)

    def test_odata_context_generation(self):
        """Test OData context generation."""
        # Create a mock request with all necessary attributes
        from django.http import QueryDict

        class MockRequest:
            def __init__(self):
                self.query_params = QueryDict()
                self.GET = QueryDict()
                self.headers = {}
                self.META = {}

            def build_absolute_uri(self, path):
                return f"http://example.com{path}"

        context = {"request": MockRequest()}
        serializer = self.serializer_class(context=context)
        odata_context = serializer.get_odata_context()

        self.assertIn("odata_version", odata_context)
        self.assertEqual(odata_context["odata_version"], "4.0")
        self.assertIn("service_root", odata_context)


class TestCreateODataSerializer(TestCase):
    """Test the create_odata_serializer factory function."""

    def test_create_basic_serializer(self):
        """Test creating a basic OData serializer."""
        serializer_class = create_odata_serializer(SerializerTestModel)

        self.assertTrue(issubclass(serializer_class, ODataModelSerializer))
        self.assertEqual(serializer_class.Meta.model, SerializerTestModel)
        self.assertEqual(serializer_class.Meta.fields, "__all__")

    def test_create_serializer_with_fields(self):
        """Test creating serializer with specific fields."""
        serializer_class = create_odata_serializer(
            SerializerTestModel, fields=["id", "name", "value"]
        )

        self.assertEqual(serializer_class.Meta.fields, ["id", "name", "value"])

    def test_create_serializer_with_expandable_fields(self):
        """Test creating serializer with expandable fields."""
        expandable_fields = {
            "related_items": (
                "tests.test_serializers.RelatedModelSerializer",
                {"many": True},
            )
        }
        serializer_class = create_odata_serializer(
            SerializerTestModel, expandable_fields=expandable_fields
        )

        self.assertEqual(serializer_class.Meta.expandable_fields, expandable_fields)

    def test_serializer_naming(self):
        """Test that created serializers have proper names."""
        serializer_class = create_odata_serializer(SerializerTestModel)
        self.assertEqual(
            serializer_class.__name__, "SerializerTestModelODataSerializer"
        )


class RelatedModelSerializer(ODataModelSerializer):
    """Serializer for RelatedModel - used in expandable_fields tests."""

    class Meta:
        model = SerializerRelatedModel
        fields = ["id", "description"]


# TestODataNestedExpand removed - these tests were specific to drf-flex-fields
# parameter conversion which is no longer used. The native implementation is
# tested in test_native_fields.py


if __name__ == "__main__":
    pytest.main([__file__])
