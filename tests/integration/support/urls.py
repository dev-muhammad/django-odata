"""
URL configuration for django-odata tests.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ..test_odata_expressions import ODataTestViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'test-models', ODataTestViewSet, basename='test-models')

urlpatterns = [
    path('api/', include(router.urls)),
]
