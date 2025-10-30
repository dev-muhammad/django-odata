"""
Unit tests for enhanced $expand support with full OData v4 compliance.

Tests the parse_expand_fields_v2 function and related functionality for
parsing complex $expand expressions with nested query options.
"""

import pytest
from django_odata.utils import (
    parse_expand_fields_v2,
    _parse_single_expand_field_v2,
    _parse_query_options,
    _parse_single_query_option,
)


class TestParseExpandFieldsV2:
    """Test suite for parse_expand_fields_v2 function."""

    def test_empty_string(self):
        """Test parsing empty expand string."""
        result = parse_expand_fields_v2("")
        assert result == {}

    def test_whitespace_only(self):
        """Test parsing whitespace-only expand string."""
        result = parse_expand_fields_v2("   ")
        assert result == {}

    def test_simple_expansion(self):
        """Test simple field expansion without options."""
        result = parse_expand_fields_v2("author")
        assert result == {"author": {}}

    def test_multiple_simple_expansions(self):
        """Test multiple simple field expansions."""
        result = parse_expand_fields_v2("author,categories,tags")
        assert result == {
            "author": {},
            "categories": {},
            "tags": {},
        }

    def test_expansion_with_select(self):
        """Test expansion with $select option."""
        result = parse_expand_fields_v2("author($select=name,email)")
        assert result == {
            "author": {
                "$select": "name,email"
            }
        }

    def test_expansion_with_filter(self):
        """Test expansion with $filter option."""
        result = parse_expand_fields_v2("posts($filter=published eq true)")
        assert result == {
            "posts": {
                "$filter": "published eq true"
            }
        }

    def test_expansion_with_orderby(self):
        """Test expansion with $orderby option."""
        result = parse_expand_fields_v2("posts($orderby=publishedAt desc)")
        assert result == {
            "posts": {
                "$orderby": "publishedAt desc"
            }
        }

    def test_expansion_with_top(self):
        """Test expansion with $top option."""
        result = parse_expand_fields_v2("posts($top=10)")
        assert result == {
            "posts": {
                "$top": "10"
            }
        }

    def test_expansion_with_skip(self):
        """Test expansion with $skip option."""
        result = parse_expand_fields_v2("posts($skip=5)")
        assert result == {
            "posts": {
                "$skip": "5"
            }
        }

    def test_expansion_with_count(self):
        """Test expansion with $count option."""
        result = parse_expand_fields_v2("posts($count=true)")
        assert result == {
            "posts": {
                "$count": "true"
            }
        }

    def test_expansion_with_multiple_options(self):
        """Test expansion with multiple query options."""
        result = parse_expand_fields_v2(
            "posts($select=title,content;$filter=published eq true;$orderby=publishedAt desc;$top=5)"
        )
        assert result == {
            "posts": {
                "$select": "title,content",
                "$filter": "published eq true",
                "$orderby": "publishedAt desc",
                "$top": "5",
            }
        }

    def test_expansion_with_all_options(self):
        """Test expansion with all supported query options."""
        result = parse_expand_fields_v2(
            "orders($filter=status eq 'pending';$orderby=date desc;$top=10;$skip=5;$count=true;$select=id,total)"
        )
        assert result == {
            "orders": {
                "$filter": "status eq 'pending'",
                "$orderby": "date desc",
                "$top": "10",
                "$skip": "5",
                "$count": "true",
                "$select": "id,total",
            }
        }

    def test_nested_expansion(self):
        """Test nested $expand within $expand."""
        result = parse_expand_fields_v2("author($expand=posts($top=3))")
        assert result == {
            "author": {
                "$expand": "posts($top=3)"
            }
        }

    def test_complex_nested_expansion(self):
        """Test complex nested expansion with multiple levels."""
        result = parse_expand_fields_v2(
            "author($select=name;$expand=posts($select=title;$top=3))"
        )
        assert result == {
            "author": {
                "$select": "name",
                "$expand": "posts($select=title;$top=3)"
            }
        }

    def test_multiple_expansions_with_options(self):
        """Test multiple expansions each with their own options."""
        result = parse_expand_fields_v2(
            "author($select=name,email),categories($filter=active eq true),tags($orderby=name)"
        )
        assert result == {
            "author": {
                "$select": "name,email"
            },
            "categories": {
                "$filter": "active eq true"
            },
            "tags": {
                "$orderby": "name"
            }
        }

    def test_mixed_simple_and_complex_expansions(self):
        """Test mix of simple and complex expansions."""
        result = parse_expand_fields_v2(
            "author($select=name),categories,tags($orderby=name)"
        )
        assert result == {
            "author": {
                "$select": "name"
            },
            "categories": {},
            "tags": {
                "$orderby": "name"
            }
        }

    def test_expansion_with_spaces(self):
        """Test expansion with spaces in various places."""
        result = parse_expand_fields_v2(
            "author ( $select = name , email ; $filter = active eq true )"
        )
        assert result == {
            "author": {
                "$select": "name , email",
                "$filter": "active eq true"
            }
        }

    def test_filter_with_complex_expression(self):
        """Test $filter with complex OData expression."""
        result = parse_expand_fields_v2(
            "posts($filter=published eq true and views gt 100)"
        )
        assert result == {
            "posts": {
                "$filter": "published eq true and views gt 100"
            }
        }

    def test_filter_with_string_literals(self):
        """Test $filter with string literals containing special characters."""
        result = parse_expand_fields_v2(
            "posts($filter=status eq 'pending' or status eq 'approved')"
        )
        assert result == {
            "posts": {
                "$filter": "status eq 'pending' or status eq 'approved'"
            }
        }


class TestParseSingleExpandFieldV2:
    """Test suite for _parse_single_expand_field_v2 helper function."""

    def test_simple_field(self):
        """Test parsing simple field without options."""
        field_name, options = _parse_single_expand_field_v2("author")
        assert field_name == "author"
        assert options == {}

    def test_field_with_select(self):
        """Test parsing field with $select option."""
        field_name, options = _parse_single_expand_field_v2("author($select=name,email)")
        assert field_name == "author"
        assert options == {"$select": "name,email"}

    def test_field_with_multiple_options(self):
        """Test parsing field with multiple options."""
        field_name, options = _parse_single_expand_field_v2(
            "posts($select=title;$filter=published eq true;$top=5)"
        )
        assert field_name == "posts"
        assert options == {
            "$select": "title",
            "$filter": "published eq true",
            "$top": "5"
        }

    def test_malformed_field_missing_closing_paren(self):
        """Test parsing malformed field missing closing parenthesis."""
        field_name, options = _parse_single_expand_field_v2("author($select=name")
        # Should return field as-is with empty options
        assert field_name == "author($select=name"
        assert options == {}

    def test_field_with_nested_parentheses(self):
        """Test parsing field with nested parentheses in $expand."""
        field_name, options = _parse_single_expand_field_v2(
            "author($expand=posts($top=3))"
        )
        assert field_name == "author"
        assert options == {"$expand": "posts($top=3)"}


class TestParseQueryOptions:
    """Test suite for _parse_query_options helper function."""

    def test_empty_string(self):
        """Test parsing empty options string."""
        result = _parse_query_options("")
        assert result == {}

    def test_single_option(self):
        """Test parsing single query option."""
        result = _parse_query_options("$select=name,email")
        assert result == {"$select": "name,email"}

    def test_multiple_options(self):
        """Test parsing multiple query options."""
        result = _parse_query_options("$select=name;$filter=active eq true;$top=5")
        assert result == {
            "$select": "name",
            "$filter": "active eq true",
            "$top": "5"
        }

    def test_nested_expand_option(self):
        """Test parsing nested $expand option."""
        result = _parse_query_options("$select=name;$expand=posts($top=3)")
        assert result == {
            "$select": "name",
            "$expand": "posts($top=3)"
        }

    def test_complex_nested_expand(self):
        """Test parsing complex nested $expand with multiple levels."""
        result = _parse_query_options(
            "$expand=posts($select=title;$expand=comments($top=5))"
        )
        assert result == {
            "$expand": "posts($select=title;$expand=comments($top=5))"
        }


class TestParseSingleQueryOption:
    """Test suite for _parse_single_query_option helper function."""

    def test_select_option(self):
        """Test parsing $select option."""
        key, value = _parse_single_query_option("$select=name,email")
        assert key == "$select"
        assert value == "name,email"

    def test_filter_option(self):
        """Test parsing $filter option."""
        key, value = _parse_single_query_option("$filter=active eq true")
        assert key == "$filter"
        assert value == "active eq true"

    def test_orderby_option(self):
        """Test parsing $orderby option."""
        key, value = _parse_single_query_option("$orderby=name desc")
        assert key == "$orderby"
        assert value == "name desc"

    def test_top_option(self):
        """Test parsing $top option."""
        key, value = _parse_single_query_option("$top=10")
        assert key == "$top"
        assert value == "10"

    def test_skip_option(self):
        """Test parsing $skip option."""
        key, value = _parse_single_query_option("$skip=5")
        assert key == "$skip"
        assert value == "5"

    def test_count_option(self):
        """Test parsing $count option."""
        key, value = _parse_single_query_option("$count=true")
        assert key == "$count"
        assert value == "true"

    def test_expand_option(self):
        """Test parsing $expand option."""
        key, value = _parse_single_query_option("$expand=posts($top=3)")
        assert key == "$expand"
        assert value == "posts($top=3)"

    def test_invalid_option_no_equals(self):
        """Test parsing invalid option without equals sign."""
        key, value = _parse_single_query_option("invalid")
        assert key == ""
        assert value == ""

    def test_invalid_option_no_dollar(self):
        """Test parsing invalid option without $ prefix."""
        key, value = _parse_single_query_option("select=name")
        assert key == ""
        assert value == ""

    def test_option_with_spaces(self):
        """Test parsing option with spaces."""
        key, value = _parse_single_query_option(" $select = name , email ")
        assert key == "$select"
        assert value == "name , email"


class TestBackwardCompatibility:
    """Test suite to ensure backward compatibility with existing expand syntax."""

    def test_simple_expand_still_works(self):
        """Test that simple $expand=field still works."""
        result = parse_expand_fields_v2("author")
        assert "author" in result
        assert result["author"] == {}

    def test_expand_with_select_still_works(self):
        """Test that $expand=field($select=...) still works."""
        result = parse_expand_fields_v2("author($select=name,email)")
        assert "author" in result
        assert "$select" in result["author"]
        assert result["author"]["$select"] == "name,email"

    def test_multiple_expands_still_work(self):
        """Test that multiple expansions still work."""
        result = parse_expand_fields_v2("author,categories,tags")
        assert len(result) == 3
        assert "author" in result
        assert "categories" in result
        assert "tags" in result