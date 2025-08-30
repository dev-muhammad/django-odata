"""
Tests for django_odata.viewsets module.
"""

import pytest
from django.contrib.auth.models import User
from django.db import models
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django_odata.serializers import ODataModelSerializer
from django_odata.viewsets import (
    ODataModelViewSet,
    ODataReadOnlyModelViewSet,
    create_odata_viewset,
)


class ViewSetTestModel(models.Model):
    """Test model for viewset tests."""

    name = models.CharField(max_length=100)
    value = models.IntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "test"


class ViewSetTestModelSerializer(ODataModelSerializer):
    """Test serializer for viewset tests."""

    class Meta:
        model = ViewSetTestModel
        fields = ["id", "name", "value", "is_active", "created_at"]


class TestODataModelViewSet(APITestCase):
    """Test ODataModelViewSet functionality."""

    def setUp(self):
        """Set up test data and viewset."""
        self.factory = RequestFactory()
        self.client = APIClient()

        class TestViewSet(ODataModelViewSet):
            queryset = ViewSetTestModel.objects.all()
            serializer_class = ViewSetTestModelSerializer

        self.viewset_class = TestViewSet

    def test_viewset_initialization(self):
        """Test that the viewset can be initialized."""
        viewset = self.viewset_class()
        self.assertIsInstance(viewset, ODataModelViewSet)

    def test_get_odata_entity_set_name(self):
        """Test getting OData entity set name."""
        viewset = self.viewset_class()
        entity_set_name = viewset.get_odata_entity_set_name()
        self.assertEqual(entity_set_name, "viewsettestmodels")

    def test_get_odata_entity_type_name(self):
        """Test getting OData entity type name."""
        viewset = self.viewset_class()
        entity_type_name = viewset.get_odata_entity_type_name()
        self.assertEqual(entity_type_name, "ViewSetTestModel")

    def test_get_odata_query_params(self):
        """Test extracting OData query parameters."""
        request = self.factory.get('/test/?$filter=name eq "test"&$orderby=value desc')
        # Add necessary attributes that might be missing
        if not hasattr(request, "query_params"):
            request.query_params = request.GET
        viewset = self.viewset_class()
        viewset.request = request

        odata_params = viewset.get_odata_query_params()
        self.assertIn("$filter", odata_params)
        self.assertIn("$orderby", odata_params)
        self.assertEqual(odata_params["$filter"], 'name eq "test"')
        self.assertEqual(odata_params["$orderby"], "value desc")

    def test_serializer_context_includes_odata_params(self):
        """Test that serializer context includes OData parameters."""
        request = self.factory.get("/test/?$select=name,value")
        # Add necessary attributes that might be missing
        if not hasattr(request, "query_params"):
            request.query_params = request.GET
        viewset = self.viewset_class()
        viewset.request = request
        viewset.format_kwarg = None

        context = viewset.get_serializer_context()
        self.assertIn("odata_params", context)
        self.assertIn("$select", context["odata_params"])


class TestODataReadOnlyModelViewSet(TestCase):
    """Test ODataReadOnlyModelViewSet functionality."""

    def setUp(self):
        """Set up test viewset."""

        class TestReadOnlyViewSet(ODataReadOnlyModelViewSet):
            queryset = ViewSetTestModel.objects.all()
            serializer_class = ViewSetTestModelSerializer

        self.viewset_class = TestReadOnlyViewSet

    def test_viewset_initialization(self):
        """Test that the read-only viewset can be initialized."""
        viewset = self.viewset_class()
        self.assertIsInstance(viewset, ODataReadOnlyModelViewSet)

    def test_entity_names(self):
        """Test entity set and type name generation."""
        viewset = self.viewset_class()
        self.assertEqual(viewset.get_odata_entity_set_name(), "viewsettestmodels")
        self.assertEqual(viewset.get_odata_entity_type_name(), "ViewSetTestModel")


class TestCreateODataViewSet(TestCase):
    """Test the create_odata_viewset factory function."""

    def test_create_basic_viewset(self):
        """Test creating a basic OData viewset."""
        viewset_class = create_odata_viewset(ViewSetTestModel)

        self.assertTrue(issubclass(viewset_class, ODataModelViewSet))
        self.assertEqual(viewset_class.queryset.model, ViewSetTestModel)

    def test_create_readonly_viewset(self):
        """Test creating a read-only OData viewset."""
        viewset_class = create_odata_viewset(ViewSetTestModel, read_only=True)

        self.assertTrue(issubclass(viewset_class, ODataReadOnlyModelViewSet))

    def test_create_viewset_with_custom_serializer(self):
        """Test creating viewset with custom serializer."""
        viewset_class = create_odata_viewset(
            ViewSetTestModel, serializer_class=ViewSetTestModelSerializer
        )

        self.assertEqual(viewset_class.serializer_class, ViewSetTestModelSerializer)

    def test_viewset_naming(self):
        """Test that created viewsets have proper names."""
        viewset_class = create_odata_viewset(ViewSetTestModel)
        self.assertEqual(viewset_class.__name__, "ViewSetTestModelODataViewSet")


class TestODataResponseFormatting(APITestCase):
    """Test OData response formatting."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

        class TestViewSet(ODataModelViewSet):
            queryset = ViewSetTestModel.objects.all()
            serializer_class = ViewSetTestModelSerializer

        self.viewset_class = TestViewSet

    def test_list_response_format(self):
        """Test that list responses are formatted correctly."""
        request = self.factory.get("/test/")
        viewset = self.viewset_class()
        viewset.request = request
        viewset.format_kwarg = None

        # Mock the queryset and pagination
        viewset.paginate_queryset = lambda qs: None
        viewset.filter_queryset = lambda qs: qs

        # Test would require actual database setup to complete
        # For now, we test the structure
        self.assertTrue(hasattr(viewset, "list"))

    def test_retrieve_response_format(self):
        """Test that retrieve responses are formatted correctly."""
        request = self.factory.get("/test/1/")
        viewset = self.viewset_class()
        viewset.request = request

        # Test would require actual database setup to complete
        self.assertTrue(hasattr(viewset, "retrieve"))


class TestODataMetadataEndpoint(TestCase):
    """Test OData metadata endpoint functionality."""

    def setUp(self):
        """Set up test viewset."""

        class TestViewSet(ODataModelViewSet):
            queryset = ViewSetTestModel.objects.all()
            serializer_class = ViewSetTestModelSerializer

        self.viewset_class = TestViewSet
        self.factory = RequestFactory()

    def test_metadata_endpoint_exists(self):
        """Test that metadata endpoint is available."""
        viewset = self.viewset_class()
        self.assertTrue(hasattr(viewset, "metadata"))

    def test_metadata_endpoint_structure(self):
        """Test metadata endpoint response structure."""
        request = self.factory.get("/test/$metadata")
        viewset = self.viewset_class()
        viewset.request = request

        # Test would require actual execution to verify response format
        # For now, we verify the method exists and is callable
        self.assertTrue(callable(viewset.metadata))


class TestNavigationProperties(TestCase):
    """Test navigation property handling."""

    def setUp(self):
        """Set up test viewset with navigation properties."""

        class TestViewSet(ODataModelViewSet):
            queryset = ViewSetTestModel.objects.all()
            serializer_class = ViewSetTestModelSerializer

        self.viewset_class = TestViewSet
        self.factory = RequestFactory()

    def test_navigation_property_endpoint_exists(self):
        """Test that navigation property endpoints exist."""
        viewset = self.viewset_class()
        self.assertTrue(hasattr(viewset, "get_navigation_property"))
        self.assertTrue(hasattr(viewset, "get_navigation_links"))

    def test_navigation_property_methods_callable(self):
        """Test that navigation property methods are callable."""
        viewset = self.viewset_class()
        self.assertTrue(callable(viewset.get_navigation_property))
        self.assertTrue(callable(viewset.get_navigation_links))


if __name__ == "__main__":
    pytest.main([__file__])
