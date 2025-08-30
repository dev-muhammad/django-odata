#!/usr/bin/env python
"""
Quick example of how to use django-odata in your Django project.

This is a minimal example showing the main components and usage patterns.
"""

# 1. In your models.py
"""
from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    bio = models.TextField(blank=True)

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
"""

# 2. In your serializers.py
"""
from django_odata.serializers import ODataModelSerializer
from .models import BlogPost, Author

class AuthorSerializer(ODataModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'bio']

class BlogPostSerializer(ODataModelSerializer):
    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'content', 'created_at', 'view_count', 'is_published']
        expandable_fields = {
            'author': (AuthorSerializer, {}),
        }
"""

# 3. In your views.py
"""
from django_odata.viewsets import ODataModelViewSet
from .models import BlogPost, Author
from .serializers import BlogPostSerializer, AuthorSerializer

class BlogPostViewSet(ODataModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer

class AuthorViewSet(ODataModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
"""

# 4. In your urls.py
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet, AuthorViewSet

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet)
router.register(r'authors', AuthorViewSet)

urlpatterns = [
    path('odata/', include(router.urls)),
]
"""

# 5. Example API calls you can now make:

EXAMPLE_QUERIES = {
    "Basic collection": "/odata/posts/",
    "Single entity": "/odata/posts/1/",
    "Filter published posts": "/odata/posts/?$filter=is_published eq true",
    "Sort by date": "/odata/posts/?$orderby=created_at desc",
    "Pagination": "/odata/posts/?$top=10&$skip=20",
    "Select fields": "/odata/posts/?$select=id,title,created_at",
    "Expand author": "/odata/posts/?$expand=author",
    "Complex query": "/odata/posts/?$filter=is_published eq true and view_count gt 100&$orderby=created_at desc&$top=5&$expand=author&$select=id,title,author,view_count",
    "Count results": "/odata/posts/?$count=true",
    "Metadata": "/odata/posts/$metadata",
    "Search in title": "/odata/posts/?$filter=contains(title,'django')",
    "Posts from 2024": "/odata/posts/?$filter=year(created_at) eq 2024",
}

print("Django OData - Example Usage")
print("=" * 40)
print("\nAfter setting up the models, serializers, and views as shown above,")
print("you can make these OData-compliant API calls:")
print()

for description, query in EXAMPLE_QUERIES.items():
    print(f"{description:20}: {query}")

print("\nKey Features:")
print("- Automatic OData query translation to Django ORM")
print("- Dynamic field selection with $select")
print("- Related data expansion with $expand")
print("- Filtering with $filter (supports complex expressions)")
print("- Sorting with $orderby")
print("- Pagination with $top and $skip")
print("- Metadata endpoints for service discovery")
print("- Full compatibility with Django REST Framework")

print("\nFor a complete working example, see the 'example/' directory.")
