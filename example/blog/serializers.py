"""
OData serializers for the blog app.
"""

from django_odata.serializers import ODataModelSerializer
from .models import BlogPost, Author, Category, Comment, Tag


class CategorySerializer(ODataModelSerializer):
    """OData serializer for Category model."""

    class Meta:
        model = Category
        fields = ["id", "name", "description", "created_at"]
        expandable_fields = {
            "posts": ("blog.serializers.BlogPostSerializer", {"many": True}),
        }


class AuthorSerializer(ODataModelSerializer):
    """OData serializer for Author model."""

    class Meta:
        model = Author
        fields = ["id", "name", "email", "bio", "website", "avatar", "created_at"]
        expandable_fields = {
            "posts": ("blog.serializers.BlogPostSerializer", {"many": True}),
        }


class CommentSerializer(ODataModelSerializer):
    """OData serializer for Comment model."""

    class Meta:
        model = Comment
        fields = [
            "id",
            "author_name",
            "author_email",
            "content",
            "is_approved",
            "created_at",
        ]
        expandable_fields = {
            "post": ("blog.serializers.BlogPostSerializer", {}),
        }


class TagSerializer(ODataModelSerializer):
    """OData serializer for Tag model."""

    class Meta:
        model = Tag
        fields = ["id", "name", "color"]
        expandable_fields = {
            "posts": ("blog.serializers.BlogPostSerializer", {"many": True}),
        }


class BlogPostSerializer(ODataModelSerializer):
    """OData serializer for BlogPost model."""

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "excerpt",
            "status",
            "featured",
            "view_count",
            "rating",
            "created_at",
            "updated_at",
            "published_at",
            "tags",
            "metadata",
            "is_published",
            "word_count",
        ]
        expandable_fields = {
            "author": (AuthorSerializer, {}),
            "categories": (CategorySerializer, {"many": True}),
            "comments": (CommentSerializer, {"many": True}),
            "tag_objects": (TagSerializer, {"many": True}),
        }
