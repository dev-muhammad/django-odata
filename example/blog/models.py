"""
Example blog models for demonstrating django-odata functionality.
"""

from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    """Blog category model."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    """Blog author model."""

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)
    avatar = models.URLField(blank=True, help_text="URL to avatar image")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    @property
    def name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email


class BlogPost(models.Model):
    """Blog post model with various field types for OData testing."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True, help_text="Short description of the post")

    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="posts")
    categories = models.ManyToManyField(Category, related_name="posts", blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    tags = models.JSONField(default=list, blank=True, help_text="List of tags")
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional metadata"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["author", "created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == "published"

    @property
    def word_count(self):
        return len(self.content.split())


class Comment(models.Model):
    """Comment model for blog posts."""

    post = models.ForeignKey(
        BlogPost, on_delete=models.CASCADE, related_name="comments"
    )
    author_name = models.CharField(max_length=100)
    author_email = models.EmailField()
    content = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author_name} on {self.post.title}"


class Tag(models.Model):
    """Tag model for categorizing posts."""

    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7, default="#007bff", help_text="Hex color code"
    )
    posts = models.ManyToManyField(BlogPost, related_name="tag_objects", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
