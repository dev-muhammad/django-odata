"""
Test models for django-odata test suite.
"""

from django.db import models


class ODataTestModel(models.Model):
    """Test model with various field types for comprehensive OData testing."""

    # String fields
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Numeric fields
    count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Boolean field
    is_active = models.BooleanField(default=True)

    # Date/Time fields
    created_at = models.DateTimeField()
    published_date = models.DateField(null=True, blank=True)

    # Choice field
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    class Meta:
        pass


class ODataRelatedModel(models.Model):
    """Related model for testing navigation properties."""

    test_model = models.ForeignKey(
        ODataTestModel, on_delete=models.CASCADE, related_name="related_items"
    )
    title = models.CharField(max_length=50)
    value = models.IntegerField()

    class Meta:
        pass


class PerformanceTestModel(models.Model):
    """Model for performance testing with various indexed fields."""

    name = models.CharField(max_length=100, db_index=True)
    category = models.CharField(max_length=50, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    quantity = models.IntegerField(db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_available"]),
            models.Index(fields=["price", "quantity"]),
            models.Index(fields=["created_at", "rating"]),
        ]


class PerformanceRelatedModel(models.Model):
    """Related model for testing join performance."""

    parent = models.ForeignKey(
        PerformanceTestModel, on_delete=models.CASCADE, related_name="related_items"
    )
    tag = models.CharField(max_length=30)
    weight = models.IntegerField()

    class Meta:
        pass
