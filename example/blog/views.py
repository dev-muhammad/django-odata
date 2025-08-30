"""
OData ViewSets for the blog app.
"""

from django_odata.viewsets import ODataModelViewSet
from .models import BlogPost, Author, Category, Comment, Tag
from .serializers import (
    BlogPostSerializer,
    AuthorSerializer,
    CategorySerializer,
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
    - /odata/posts/?$filter=status eq 'published'
    - /odata/posts/?$orderby=created_at desc&$top=10
    - /odata/posts/?$expand=author,categories&$select=title,content,author,categories
    - /odata/posts/?$filter=view_count gt 100&$orderby=rating desc
    """

    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer

    def get_queryset(self):
        """
        Get the queryset with any additional filtering.
        The OData filtering is applied automatically by the parent class.
        """
        queryset = super().get_queryset()

        # Add any custom business logic here
        # For example, only show published posts to non-staff users
        user = getattr(self.request, "user", None)
        if user and not user.is_staff:
            queryset = queryset.filter(status="published")

        return queryset


class AuthorViewSet(ODataModelViewSet):
    """
    OData ViewSet for Author model.

    Example queries:
    - /odata/authors/?$expand=posts
    - /odata/authors/?$filter=contains(bio,'python')
    - /odata/authors/?$orderby=created_at desc
    """

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class CategoryViewSet(ODataModelViewSet):
    """
    OData ViewSet for Category model.

    Example queries:
    - /odata/categories/?$expand=posts
    - /odata/categories/?$filter=startswith(name,'Tech')
    - /odata/categories/?$orderby=name asc
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CommentViewSet(ODataModelViewSet):
    """
    OData ViewSet for Comment model.

    Example queries:
    - /odata/comments/?$filter=is_approved eq true
    - /odata/comments/?$expand=post&$orderby=created_at desc
    """

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer


class TagViewSet(ODataModelViewSet):
    """
    OData ViewSet for Tag model.

    Example queries:
    - /odata/tags/?$expand=posts
    - /odata/tags/?$filter=color eq '#ff0000'
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
