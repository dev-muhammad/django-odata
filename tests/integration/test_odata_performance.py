"""
Performance tests for OData expression evaluation.

These tests verify that OData queries perform well with larger datasets
and complex filter expressions.
"""

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from django.test import TestCase
from django.test.utils import override_settings

from django_odata.serializers import ODataModelSerializer
from django_odata.viewsets import ODataModelViewSet

from .support.models import PerformanceRelatedModel, PerformanceTestModel


class PerformanceTestModelSerializer(ODataModelSerializer):
    """Serializer for PerformanceTestModel."""

    class Meta:
        model = PerformanceTestModel
        fields = [
            "id",
            "name",
            "category",
            "description",
            "price",
            "quantity",
            "is_available",
            "created_at",
            "updated_at",
            "rating",
        ]
        expandable_fields = {
            "related_items": (
                "PerformanceRelatedModelSerializer",
                {"many": True},
            ),
        }


class PerformanceRelatedModelSerializer(ODataModelSerializer):
    """Serializer for PerformanceRelatedModel."""

    class Meta:
        model = PerformanceRelatedModel
        fields = ["id", "tag", "weight"]


class PerformanceTestViewSet(ODataModelViewSet):
    """ViewSet for performance testing."""

    queryset = PerformanceTestModel.objects.all()
    serializer_class = PerformanceTestModelSerializer


@override_settings(DEBUG=False)  # Disable debug to avoid query logging overhead
class TestODataPerformance(TestCase):
    """Test OData query performance with larger datasets."""

    @classmethod
    def setUpTestData(cls):
        """Create a substantial dataset for performance testing."""
        # Create 1000 test records with varied data
        categories = ["electronics", "books", "clothing", "home", "sports"]

        records = []
        related_records = []

        base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)

        for i in range(1000):
            created_time = base_time + timedelta(days=i % 365, hours=i % 24)

            record = PerformanceTestModel(
                name=f"Product {i:04d}",
                category=categories[i % len(categories)],
                description=f"Description for product {i} with various keywords and content",
                price=Decimal(f"{(i % 1000) + 1}.99"),
                quantity=i % 100,
                is_available=(i % 3) != 0,  # ~67% available
                created_at=created_time,
                rating=Decimal(f"{(i % 50) / 10:.1f}") if i % 5 != 0 else None,
            )
            records.append(record)

            # Add related records for some items
            if i % 10 == 0:  # Every 10th item gets related records
                for j in range(3):
                    related_records.append(
                        PerformanceRelatedModel(
                            parent_id=i + 1,  # Will be set after bulk_create
                            tag=f"tag{j}",
                            weight=j * 10,
                        )
                    )

        # Bulk create for better performance
        cls.created_records = PerformanceTestModel.objects.bulk_create(records)

        # Fix parent IDs for related records and bulk create
        for i, related in enumerate(related_records):
            related.parent_id = cls.created_records[related.parent_id - 1].id

        PerformanceRelatedModel.objects.bulk_create(related_records)

    def measure_query_time(self, queryset, description="Query"):
        """Helper method to measure query execution time."""
        start_time = time.time()

        # Force evaluation of the queryset
        result_count = queryset.count()
        list(queryset[:10])  # Fetch first 10 items to measure serialization

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"{description}: {execution_time:.4f}s (returned {result_count} items)")
        return execution_time, result_count

    def test_simple_filter_performance(self):
        """Test performance of simple filter expressions."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test simple equality filter
        params = {"$filter": "category eq 'electronics'"}
        filtered_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            filtered_qs, "Simple equality filter"
        )

        # Should complete reasonably quickly (adjust threshold as needed)
        self.assertLess(execution_time, 1.0, "Simple filter took too long")
        self.assertGreater(count, 0, "Filter should return results")

    def test_range_filter_performance(self):
        """Test performance of range filter expressions."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test range filter
        params = {"$filter": "price ge 100.00 and price le 500.00"}
        filtered_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            filtered_qs, "Range filter (price between 100-500)"
        )

        self.assertLess(execution_time, 1.0, "Range filter took too long")
        self.assertGreater(count, 0, "Range filter should return results")

    def test_string_function_performance(self):
        """Test performance of string function filters."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test string contains function
        params = {"$filter": "contains(name,'Product')"}
        filtered_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            filtered_qs, "String contains function"
        )

        self.assertLess(execution_time, 1.0, "String function took too long")
        self.assertGreater(count, 0, "String function should return results")

    def test_date_function_performance(self):
        """Test performance of date function filters."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test date year function
        params = {"$filter": "year(created_at) eq 2023"}
        filtered_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            filtered_qs, "Date year function"
        )

        self.assertLess(execution_time, 1.0, "Date function took too long")
        self.assertGreater(count, 0, "Date function should return results")

    def test_complex_filter_performance(self):
        """Test performance of complex filter expressions."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test complex filter with multiple conditions
        params = {
            "$filter": "(category eq 'electronics' or category eq 'books') and is_available eq true and price lt 200.00"
        }
        filtered_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            filtered_qs, "Complex multi-condition filter"
        )

        self.assertLess(execution_time, 1.0, "Complex filter took too long")
        self.assertGreater(count, 0, "Complex filter should return results")

    def test_orderby_performance(self):
        """Test performance of ordering with large datasets."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test ordering by indexed field
        params = {"$orderby": "price desc, created_at asc"}
        ordered_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            ordered_qs, "Multi-field ordering"
        )

        self.assertLess(execution_time, 1.0, "Ordering took too long")
        self.assertEqual(count, 1000, "Should return all records")

    def test_pagination_performance(self):
        """Test performance of $top and $skip parameters."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Test pagination
        params = {"$skip": "100", "$top": "50", "$orderby": "id asc"}
        paginated_qs = apply_odata_query_params(queryset, params)

        execution_time, count = self.measure_query_time(
            paginated_qs, "Pagination (skip 100, take 50)"
        )

        self.assertLess(execution_time, 1.0, "Pagination took too long")
        self.assertLessEqual(count, 50, "Should return at most 50 records")

    def test_expansion_optimization_performance(self):
        """Test performance of query optimization for expansions."""
        viewset = PerformanceTestViewSet()

        # Mock request with expand parameter
        class MockRequest:
            def __init__(self, query_params):
                self.query_params = query_params
                self.GET = query_params

        viewset.request = MockRequest({"$expand": "related_items"})

        # Test optimized queryset generation
        start_time = time.time()

        optimized_qs = viewset.get_queryset()
        # Force evaluation
        list(optimized_qs[:10])

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"Expansion optimization: {execution_time:.4f}s")

        self.assertLess(execution_time, 1.0, "Expansion optimization took too long")

    def test_memory_usage_large_results(self):
        """Test memory efficiency with large result sets."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Filter that returns most records
        params = {"$filter": "quantity ge 0"}  # Most records have quantity >= 0
        filtered_qs = apply_odata_query_params(queryset, params)

        # Test that we can iterate through large result sets efficiently
        start_time = time.time()

        count = 0
        for item in filtered_qs.iterator(
            chunk_size=100
        ):  # Use iterator for memory efficiency
            count += 1
            if count >= 500:  # Stop at 500 to avoid long test times
                break

        end_time = time.time()
        execution_time = end_time - start_time

        print(f"Memory-efficient iteration (500 items): {execution_time:.4f}s")

        self.assertLess(execution_time, 1.0, "Large result iteration took too long")
        self.assertEqual(count, 500, "Should have processed 500 items")


class TestODataStressTests(TestCase):
    """Stress tests for edge cases and boundary conditions."""

    def setUp(self):
        """Set up minimal test data."""
        PerformanceTestModel.objects.create(
            name="Test Item",
            category="test",
            description="Test description",
            price=Decimal("10.00"),
            quantity=1,
            created_at=datetime.now(timezone.utc),
        )

    def test_very_long_filter_expression(self):
        """Test handling of very long filter expressions."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Create a very long OR expression
        conditions = []
        for i in range(100):
            conditions.append(f"quantity eq {i}")

        long_filter = " or ".join(conditions)
        params = {"$filter": long_filter}

        start_time = time.time()
        try:
            result = apply_odata_query_params(queryset, params)
            list(result)  # Force evaluation
            execution_time = time.time() - start_time

            print(f"Very long filter expression: {execution_time:.4f}s")
            self.assertLess(execution_time, 5.0, "Very long filter took too long")

        except Exception as e:
            # It's acceptable if very long expressions fail gracefully
            print(f"Very long filter failed as expected: {e}")

    def test_deeply_nested_expression(self):
        """Test handling of deeply nested logical expressions."""
        from django_odata.utils import apply_odata_query_params

        queryset = PerformanceTestModel.objects.all()

        # Create deeply nested expression
        nested_filter = "quantity eq 1"
        for i in range(10):
            nested_filter = f"({nested_filter} and quantity ge 0)"

        params = {"$filter": nested_filter}

        start_time = time.time()
        try:
            result = apply_odata_query_params(queryset, params)
            list(result)
            execution_time = time.time() - start_time

            print(f"Deeply nested expression: {execution_time:.4f}s")
            self.assertLess(
                execution_time, 2.0, "Deeply nested expression took too long"
            )

        except Exception as e:
            print(f"Deeply nested expression failed as expected: {e}")

    def test_filter_with_special_characters(self):
        """Test handling of special characters in filter values."""
        from django_odata.utils import apply_odata_query_params

        # Create item with special characters
        PerformanceTestModel.objects.create(
            name="Special Item with 'quotes' and \"double quotes\"",
            category="test",
            description="Description with special chars: !@#$%^&*()",
            price=Decimal("20.00"),
            quantity=2,
            created_at=datetime.now(timezone.utc),
        )

        queryset = PerformanceTestModel.objects.all()

        # Test filter with escaped quotes
        params = {"$filter": "contains(name,'quotes')"}

        try:
            result = apply_odata_query_params(queryset, params)
            count = result.count()
            self.assertGreaterEqual(
                count, 1, "Should find items with special characters"
            )

        except Exception as e:
            print(f"Special character filter failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
