"""
Integration tests for OData expressions using existing test infrastructure.

These tests verify OData filter expressions work correctly by using the
existing test models and setup from the main test suite.
"""

import pytest
from django.http import QueryDict
from django.test import TestCase
from rest_framework.viewsets import ModelViewSet

from django_odata.mixins import ODataMixin
from django_odata.utils import ODataQueryBuilder, parse_odata_query


class TestODataExpressionParsing(TestCase):
    """Test OData expression parsing and parameter handling."""

    def test_parse_filter_expressions(self):
        """Test parsing various OData filter expressions."""
        test_cases = [
            {
                "query": "$filter=name eq 'test'",
                "expected": {"$filter": "name eq 'test'"},
            },
            {"query": "$filter=count gt 10", "expected": {"$filter": "count gt 10"}},
            {
                "query": "$filter=is_active eq true",
                "expected": {"$filter": "is_active eq true"},
            },
            {
                "query": "$filter=contains(name,'test')",
                "expected": {"$filter": "contains(name,'test')"},
            },
            {
                "query": "$filter=year(created_at) eq 2024",
                "expected": {"$filter": "year(created_at) eq 2024"},
            },
            {
                "query": "$filter=status eq 'published' and view_count gt 50",
                "expected": {"$filter": "status eq 'published' and view_count gt 50"},
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["query"]):
                query_dict = QueryDict(case["query"])
                result = parse_odata_query(query_dict)
                self.assertEqual(result, case["expected"])

    def test_parse_complex_odata_queries(self):
        """Test parsing complex OData queries with multiple parameters."""
        complex_queries = [
            {
                "query": "$filter=status eq 'published'&$orderby=created_at desc&$top=10&$skip=5",
                "expected": {
                    "$filter": "status eq 'published'",
                    "$orderby": "created_at desc",
                    "$top": "10",
                    "$skip": "5",
                },
            },
            {
                "query": "$select=id,name,status&$expand=author,categories&$count=true",
                "expected": {
                    "$select": "id,name,status",
                    "$expand": "author,categories",
                    "$count": "true",
                },
            },
            {
                "query": "$filter=contains(name,'product') and price gt 50.00&$orderby=price asc",
                "expected": {
                    "$filter": "contains(name,'product') and price gt 50.00",
                    "$orderby": "price asc",
                },
            },
        ]

        for case in complex_queries:
            with self.subTest(case=case["query"]):
                query_dict = QueryDict(case["query"])
                result = parse_odata_query(query_dict)
                self.assertEqual(result, case["expected"])

    def test_string_function_expressions(self):
        """Test various OData string function expressions."""
        string_functions = [
            "contains(name,'test')",
            "startswith(title,'How')",
            "endswith(description,'guide')",
            "tolower(category) eq 'electronics'",
            "toupper(status) eq 'PUBLISHED'",
            "length(name) gt 10",
        ]

        for func_expr in string_functions:
            with self.subTest(expression=func_expr):
                query_dict = QueryDict(f"$filter={func_expr}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], func_expr)

    def test_date_function_expressions(self):
        """Test various OData date function expressions."""
        date_functions = [
            "year(created_at) eq 2024",
            "month(published_date) eq 12",
            "day(updated_at) eq 15",
            "hour(created_at) eq 10",
            "minute(created_at) eq 30",
            "second(created_at) eq 45",
        ]

        for func_expr in date_functions:
            with self.subTest(expression=func_expr):
                query_dict = QueryDict(f"$filter={func_expr}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], func_expr)

    def test_logical_operator_expressions(self):
        """Test logical operator expressions."""
        logical_expressions = [
            "status eq 'published' and is_active eq true",
            "price gt 100 or featured eq true",
            "not (status eq 'draft')",
            "(category eq 'books' or category eq 'electronics') and price lt 50",
            "status ne 'archived' and (featured eq true or rating ge 4.0)",
        ]

        for expr in logical_expressions:
            with self.subTest(expression=expr):
                query_dict = QueryDict(f"$filter={expr}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], expr)


class TestODataQueryBuilder(TestCase):
    """Test the OData query builder utility."""

    def test_basic_query_building(self):
        """Test basic query building functionality."""
        builder = ODataQueryBuilder()

        # Test simple filter
        result = builder.filter("name eq 'test'").build()
        expected = {"$filter": "(name eq 'test')"}
        self.assertEqual(result, expected)

        # Test ordering
        builder = ODataQueryBuilder()
        result = builder.order("created_at", desc=True).build()
        expected = {"$orderby": "created_at desc"}
        self.assertEqual(result, expected)

        # Test pagination
        builder = ODataQueryBuilder()
        result = builder.limit(10).offset(5).build()
        expected = {"$top": "10", "$skip": "5"}
        self.assertEqual(result, expected)

    def test_complex_query_building(self):
        """Test building complex queries with multiple parameters."""
        builder = ODataQueryBuilder()
        result = (
            builder.filter("status eq 'published'")
            .filter("view_count gt 100")
            .order("created_at", desc=True)
            .limit(20)
            .offset(10)
            .select("id", "title", "status")
            .expand("author", "categories")
            .build()
        )

        expected = {
            "$filter": "(status eq 'published') and (view_count gt 100)",
            "$orderby": "created_at desc",
            "$top": "20",
            "$skip": "10",
            "$select": "id,title,status",
            "$expand": "author,categories",
        }

        self.assertEqual(result, expected)

    def test_filter_combinations(self):
        """Test various filter combinations."""
        builder = ODataQueryBuilder()

        # Multiple filters should be combined with AND
        result = (
            builder.filter("category eq 'electronics'")
            .filter("price lt 500")
            .filter("is_available eq true")
            .build()
        )

        expected_filter = (
            "(category eq 'electronics') and (price lt 500) and (is_available eq true)"
        )
        self.assertEqual(result["$filter"], expected_filter)


class TestODataMixinIntegration(TestCase):
    """Test OData mixin integration with mock data."""

    def setUp(self):
        """Set up test viewset with OData mixin."""
        from django.http import QueryDict

        class MockModel:
            objects = self

            def all(self):
                return self

            def filter(self, **kwargs):
                return self

            def order_by(self, *args):
                return self

            def count(self):
                return 5

            def __getitem__(self, key):
                return self

        class MockViewSet(ODataMixin, ModelViewSet):
            queryset = MockModel()

            def __init__(self):
                super().__init__()
                self.request = None

        self.viewset = MockViewSet()
        self.mock_model = MockModel

    def test_odata_query_param_extraction(self):
        """Test OData query parameter extraction."""
        from django.http import HttpRequest

        # Mock request with OData parameters
        request = HttpRequest()
        request.GET = QueryDict(
            "$filter=name eq 'test'&$orderby=created_at desc&$top=10"
        )
        request.query_params = request.GET

        self.viewset.request = request

        odata_params = self.viewset.get_odata_query_params()

        expected = {
            "$filter": "name eq 'test'",
            "$orderby": "created_at desc",
            "$top": "10",
        }

        self.assertEqual(odata_params, expected)

    def test_odata_mixin_error_handling(self):
        """Test that OData mixin handles errors gracefully."""
        from django.http import HttpRequest

        # Mock request with potentially problematic parameters
        request = HttpRequest()
        request.GET = QueryDict("$filter=invalid syntax here")
        request.query_params = request.GET

        self.viewset.request = request

        # The mixin should handle errors gracefully and return original queryset
        queryset = self.viewset.queryset
        result = self.viewset.apply_odata_query(queryset)

        # Should return the original queryset on error
        self.assertEqual(result, queryset)


class TestODataExpressionTypes(TestCase):
    """Test different types of OData expressions and their parsing."""

    def test_comparison_operators(self):
        """Test all comparison operators."""
        operators = ["eq", "ne", "gt", "ge", "lt", "le"]

        for op in operators:
            with self.subTest(operator=op):
                expr = f"price {op} 100"
                query_dict = QueryDict(f"$filter={expr}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], expr)

    def test_data_type_expressions(self):
        """Test expressions with different data types."""
        type_expressions = [
            "name eq 'string value'",  # String
            "count eq 42",  # Integer
            "price eq 99.99",  # Decimal
            "is_active eq true",  # Boolean
            "is_archived eq false",  # Boolean
            "rating eq null",  # Null
        ]

        for expr in type_expressions:
            with self.subTest(expression=expr):
                query_dict = QueryDict(f"$filter={expr}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], expr)

    def test_nested_expressions(self):
        """Test nested logical expressions."""
        nested_expressions = [
            "(status eq 'published' and featured eq true) or priority eq 'high'",
            "not (status eq 'draft' or status eq 'archived')",
            "((price gt 50 and price lt 200) or category eq 'sale') and is_available eq true",
        ]

        for expr in nested_expressions:
            with self.subTest(expression=expr):
                query_dict = QueryDict(f"$filter={expr}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], expr)


class TestODataValidationAndErrorCases(TestCase):
    """Test validation and error handling for OData expressions."""

    def test_empty_parameters(self):
        """Test handling of empty OData parameters."""
        empty_cases = [
            "",  # Completely empty
            "$filter=",  # Empty filter
            "$orderby=",  # Empty orderby
            "$select=",  # Empty select
        ]

        for case in empty_cases:
            with self.subTest(case=case):
                query_dict = QueryDict(case)
                result = parse_odata_query(query_dict)

                # Should parse without errors
                self.assertIsInstance(result, dict)

    def test_special_characters_in_values(self):
        """Test handling of special characters in filter values."""
        special_char_cases = [
            "name eq 'value with spaces'",
            "description eq 'value with quotes'",
            "title eq 'value with single quotes'",
            "url eq 'http://example.com/path'",
        ]

        for case in special_char_cases:
            with self.subTest(case=case):
                query_dict = QueryDict(f"$filter={case}")
                result = parse_odata_query(query_dict)
                self.assertEqual(result["$filter"], case)

    def test_parameter_combinations(self):
        """Test various combinations of OData parameters."""
        combinations = [
            # All major parameters
            "$filter=status eq 'published'&$orderby=created_at desc&$top=10&$skip=5&$select=id,title&$expand=author&$count=true",
            # Subset combinations
            "$filter=featured eq true&$orderby=rating desc",
            "$select=id,name&$expand=categories",
            "$top=20&$skip=40&$count=true",
            # Order shouldn't matter
            "$orderby=title asc&$filter=is_active eq true&$top=5",
        ]

        for combo in combinations:
            with self.subTest(combination=combo):
                query_dict = QueryDict(combo)
                result = parse_odata_query(query_dict)

                # Should successfully parse all parameters
                self.assertIsInstance(result, dict)
                self.assertGreater(len(result), 0)


if __name__ == "__main__":
    pytest.main([__file__])
