"""
Example project URL configuration.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from blog.views import BlogPostViewSet, AuthorViewSet, CategoryViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"posts", BlogPostViewSet, basename="blogpost")
router.register(r"authors", AuthorViewSet, basename="author")
router.register(r"categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("odata/", include(router.urls)),  # OData endpoint
    path("api-auth/", include("rest_framework.urls")),
]
