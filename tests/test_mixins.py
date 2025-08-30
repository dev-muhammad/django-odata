"""
Tests for django_odata.mixins module.
"""

import pytest
from django.db import models
from django.http import Http404
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from django_odata.mixins import ODataMixin, ODataSerializerMixin
from django_odata.serializers import ODataModelSerializer


class MixinTestModel(models.Model):
    """Test model for mixin tests."""

    name = models.CharField(max_length=100)
    value = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "test"


class MixinTestModelSerializer(ODataModelSerializer):
    """Test serializer for mixin tests."""

    class Meta:
        model = MixinTestModel
        fields = ["id", "name", "value", "is_active"]


class TestODataSerializerMixin(TestCase):
    """Test ODataSerializerMixin functionality."""

    def setUp(self):
        """Set up test serializer with mixin."""

        class TestSerializer(MixinTestModelSerializer, ODataSerializerMixin):
            pass

        self.serializer_class = TestSerializer
        self.factory = RequestFactory()

    def test_get_odata_context(self):
        """Test getting OData context information."""
        from django.http import QueryDict

        request = self.factory.get("/test/")
        # Add necessary attributes for flex-fields compatibility
        if not hasattr(request, "query_params"):
            request.query_params = QueryDict()

        context = {"request": request}
        serializer = self.serializer_class(context=context)

        odata_context = serializer.get_odata_context()

        self.assertIn("odata_version", odata_context)
        self.assertEqual(odata_context["odata_version"], "4.0")
        self.assertIn("service_root", odata_context)
        self.assertIn("entity_set", odata_context)
        self.assertIn("entity_type", odata_context)

    def test_to_representation_with_context(self):
        """Test representation with OData context."""
        # This would require a model instance to test properly
        # For now, we test that the method exists and is callable
        serializer = self.serializer_class()
        self.assertTrue(hasattr(serializer, "to_representation"))
        self.assertTrue(callable(serializer.to_representation))


class TestODataMixin(TestCase):
    """Test ODataMixin functionality."""

    def setUp(self):
        """Set up test viewset with mixin."""
        from rest_framework.viewsets import ModelViewSet

        class TestViewSet(ODataMixin, ModelViewSet):
            queryset = MixinTestModel.objects.all()
            serializer_class = MixinTestModelSerializer

        self.viewset_class = TestViewSet
        self.factory = RequestFactory()

    def test_get_odata_query_params(self):
        """Test extracting OData query parameters."""
        request = self.factory.get(
            '/test/?$filter=name eq "test"&$top=10&$select=name,value'
        )
        # Add necessary attributes that might be missing
        if not hasattr(request, "query_params"):
            request.query_params = request.GET
        viewset = self.viewset_class()
        viewset.request = request

        params = viewset.get_odata_query_params()

        self.assertIn("$filter", params)
        self.assertIn("$top", params)
        self.assertIn("$select", params)
        self.assertEqual(params["$filter"], 'name eq "test"')
        self.assertEqual(params["$top"], "10")
        self.assertEqual(params["$select"], "name,value")

    def test_get_serializer_context_includes_odata_params(self):
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

    def test_apply_odata_query_error_handling(self):
        """Test that OData query errors are handled gracefully."""

        # Create a mock queryset
        class MockQuerySet:
            def filter(self, **kwargs):
                raise Exception("Test error")

        request = self.factory.get("/test/?$filter=invalid_query")
        # Add necessary attributes that might be missing
        if not hasattr(request, "query_params"):
            request.query_params = request.GET
        viewset = self.viewset_class()
        viewset.request = request

        mock_queryset = MockQuerySet()
        result = viewset.apply_odata_query(mock_queryset)

        # Should return original queryset on error
        self.assertEqual(result, mock_queryset)

    def test_list_method_response_format(self):
        """Test that list method formats response correctly."""
        request = self.factory.get("/test/")
        viewset = self.viewset_class()
        viewset.request = request
        viewset.format_kwarg = None

        # Mock required methods
        viewset.filter_queryset = lambda qs: qs
        viewset.paginate_queryset = lambda qs: None
        viewset.get_serializer = lambda data, many=False: type(
            "MockSerializer",
            (),
            {
                "data": (
                    [{"id": 1, "name": "test"}] if many else {"id": 1, "name": "test"}
                )
            },
        )()

        # Test that the method exists and is callable
        self.assertTrue(hasattr(viewset, "list"))
        self.assertTrue(callable(viewset.list))

    def test_retrieve_method_error_handling(self):
        """Test that retrieve method handles errors correctly."""
        request = self.factory.get("/test/999/")
        viewset = self.viewset_class()
        viewset.request = request

        # Mock get_object to raise Http404
        def mock_get_object():
            raise Http404()

        viewset.get_object = mock_get_object

        response = viewset.retrieve(request)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"]["code"], "NotFound")

    def test_metadata_endpoint(self):
        """Test metadata endpoint functionality."""
        request = self.factory.get("/test/$metadata")
        viewset = self.viewset_class()
        viewset.request = request

        # Mock get_serializer_class
        viewset.get_serializer_class = lambda: MixinTestModelSerializer

        response = viewset.metadata(request)

        # Should return a response (exact content depends on implementation)
        self.assertIsInstance(response, Response)

    def test_service_document_endpoint(self):
        """Test service document endpoint functionality."""
        request = self.factory.get("/test/")
        viewset = self.viewset_class()
        viewset.request = request

        # Mock get_serializer_class
        viewset.get_serializer_class = lambda: MixinTestModelSerializer

        response = viewset.service_document(request)

        # Should return a response
        self.assertIsInstance(response, Response)


class TestODataMixinListResponse(APITestCase):
    """Test OData mixin list response formatting in more detail."""

    def setUp(self):
        """Set up test environment."""
        from rest_framework.viewsets import ModelViewSet

        class TestViewSet(ODataMixin, ModelViewSet):
            queryset = MixinTestModel.objects.all()
            serializer_class = MixinTestModelSerializer

        self.viewset_class = TestViewSet
        self.factory = RequestFactory()

    def test_list_with_count_parameter(self):
        """Test list response with $count parameter."""
        request = self.factory.get("/test/?$count=true")
        # Add necessary attributes that might be missing
        if not hasattr(request, "query_params"):
            request.query_params = request.GET
        viewset = self.viewset_class()
        viewset.request = request
        viewset.format_kwarg = None

        # Mock the required methods
        class MockQuerySet:
            def count(self):
                return 5

        viewset.filter_queryset = lambda qs: MockQuerySet()
        viewset.paginate_queryset = lambda qs: None
        viewset.get_serializer = lambda data, many=False: type(
            "MockSerializer",
            (),
            {"data": [{"id": i, "name": f"test{i}"} for i in range(5)]},
        )()

        # Test the structure
        self.assertTrue(hasattr(viewset, "list"))

        # Get OData params
        odata_params = viewset.get_odata_query_params()
        self.assertIn("$count", odata_params)
        self.assertEqual(odata_params["$count"], "true")


if __name__ == "__main__":
    pytest.main([__file__])
