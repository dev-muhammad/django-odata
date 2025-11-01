"""
OData ViewSets for the blog app.
"""

from django_odata.viewsets import ODataModelViewSet
from .models import BlogPost, Author, Category, Comment, Tag
from .serializers import (
    BlogPostSerializer,
    AuthorSerializer,
    CategorySerializer,
)
from .manual_serializers import (
    CommentSerializer,
    TagSerializer,
)

class BlogPostViewSet(ODataModelViewSet):
    """
    OData ViewSet for BlogPost model.

    Supports all OData query operations:
    - $filter: Filter posts by various criteria
    - $orderby: Sort posts by any field
    - $top/$skip: Pagination
    - $select: Choose specific fields
    - $expand: Include related data (author, categories, comments)
    - $count: Get total count

    Example queries:
    - /api/v1/odata/posts/?$filter=status eq 'published'
    - /api/v1/odata/posts/?$orderby=created_at desc&$top=10
    - /api/v1/odata/posts/?$expand=author,categories&$select=title,content,author,categories
    - /api/v1/odata/posts/?$expand=author($expand=user),categories&$select=title,content,author,categories
    - /api/v1/odata/posts/?$filter=view_count gt 100&$orderby=rating desc
    """

    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer



class AuthorViewSet(ODataModelViewSet):
    """
    OData ViewSet for Author model.

    Example queries:
    - /api/v1/odata/authors/?$expand=posts
    - /api/v1/odata/authors/?$filter=contains(bio,'python')
    - /api/v1/odata/authors/?$orderby=created_at desc
    """

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class CategoryViewSet(ODataModelViewSet):
    """
    OData ViewSet for Category model.

    Example queries:
    - /api/v1/odata/categories/?$expand=posts
    - /api/v1/odata/categories/?$filter=startswith(name,'Tech')
    - /api/v1/odata/categories/?$orderby=name asc
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CommentViewSet(ODataModelViewSet):
    """
    OData ViewSet for Comment model.

    Example queries:
    - /api/v1/odata/comments/?$filter=is_approved eq true
    - /api/v1/odata/comments/?$expand=post&$orderby=created_at desc
    """

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer


class TagViewSet(ODataModelViewSet):
    """
    OData ViewSet for Tag model.

    Example queries:
    - /api/v1/odata/tags/?$expand=posts
    - /api/v1/odata/tags/?$filter=color eq '#ff0000'
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
