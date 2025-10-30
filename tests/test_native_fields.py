"""
Unit tests for native field selection and expansion.

Tests the native implementations that replace drf-flex-fields functionality.
"""

import pytest
from django_odata.native_fields import (
    parse_select_fields,
    parse_expand_fields,
    _parse_single_expand_field,
    NativeFieldSelectionMixin,
    NativeFieldExpansionMixin,
)
from rest_framework import serializers


class TestParseSelectFields:
    """Test parse_select_fields() function."""
    
    def test_empty_string(self):
        """Empty string should return empty lists."""
        result = parse_select_fields("")
        assert result == {'top_level': [], 'nested': {}}
    
    def test_whitespace_only(self):
        """Whitespace-only string should return empty lists."""
        result = parse_select_fields("   ")
        assert result == {'top_level': [], 'nested': {}}
    
    def test_single_field(self):
        """Single field should be in top_level."""
        result = parse_select_fields("id")
        assert result == {'top_level': ['id'], 'nested': {}}
    
    def test_multiple_fields(self):
        """Multiple fields should all be in top_level."""
        result = parse_select_fields("id,title,status")
        assert result['top_level'] == ['id', 'title', 'status']
        assert result['nested'] == {}
    
    def test_fields_with_spaces(self):
        """Fields with spaces should be trimmed."""
        result = parse_select_fields(" id , title , status ")
        assert result['top_level'] == ['id', 'title', 'status']
    
    def test_nested_field_single(self):
        """Nested field should split into parent and child."""
        result = parse_select_fields("author.name")
        assert result['top_level'] == ['author']
        assert result['nested'] == {'author': ['name']}
    
    def test_nested_field_multiple(self):
        """Multiple nested fields for same parent."""
        result = parse_select_fields("author.name,author.email")
        assert result['top_level'] == ['author']
        assert result['nested'] == {'author': ['name', 'email']}
    
    def test_mixed_top_level_and_nested(self):
        """Mix of top-level and nested fields."""
        result = parse_select_fields("id,title,author.name,author.email")
        assert set(result['top_level']) == {'id', 'title', 'author'}
        assert result['nested'] == {'author': ['name', 'email']}
    
    def test_multiple_parents_with_nested(self):
        """Multiple parents each with nested fields."""
        result = parse_select_fields("author.name,author.email,category.id,category.name")
        assert set(result['top_level']) == {'author', 'category'}
        assert result['nested'] == {
            'author': ['name', 'email'],
            'category': ['id', 'name']
        }
    
    def test_duplicate_fields(self):
        """Duplicate fields should not appear twice."""
        result = parse_select_fields("id,title,id,title")
        assert result['top_level'] == ['id', 'title']
    
    def test_duplicate_nested_fields(self):
        """Duplicate nested fields should not appear twice."""
        result = parse_select_fields("author.name,author.name")
        assert result['top_level'] == ['author']
        assert result['nested'] == {'author': ['name']}


class TestParseExpandFields:
    """Test parse_expand_fields() function."""
    
    def test_empty_string(self):
        """Empty string should return empty dict."""
        result = parse_expand_fields("")
        assert result == {}
    
    def test_whitespace_only(self):
        """Whitespace-only string should return empty dict."""
        result = parse_expand_fields("   ")
        assert result == {}
    
    def test_single_field(self):
        """Single field without nested select."""
        result = parse_expand_fields("author")
        assert result == {'author': None}
    
    def test_multiple_fields(self):
        """Multiple fields without nested select."""
        result = parse_expand_fields("author,categories")
        assert result == {'author': None, 'categories': None}
    
    def test_fields_with_spaces(self):
        """Fields with spaces should be trimmed."""
        result = parse_expand_fields(" author , categories ")
        assert result == {'author': None, 'categories': None}
    
    def test_single_field_with_nested_select(self):
        """Field with nested $select."""
        result = parse_expand_fields("author($select=name,email)")
        assert result == {'author': 'name,email'}
    
    def test_multiple_fields_with_nested_select(self):
        """Multiple fields, some with nested $select."""
        result = parse_expand_fields("author($select=name,email),categories")
        assert result == {
            'author': 'name,email',
            'categories': None
        }
    
    def test_all_fields_with_nested_select(self):
        """All fields with nested $select."""
        result = parse_expand_fields("author($select=name),categories($select=id,name)")
        assert result == {
            'author': 'name',
            'categories': 'id,name'
        }
    
    def test_nested_select_with_spaces(self):
        """Nested $select with spaces should be preserved."""
        result = parse_expand_fields("author($select= name , email )")
        assert result == {'author': ' name , email '}
    
    def test_complex_expression(self):
        """Complex expression with multiple fields and nested selects."""
        result = parse_expand_fields(
            "author($select=name,email),categories($select=id,name),tags"
        )
        assert result == {
            'author': 'name,email',
            'categories': 'id,name',
            'tags': None
        }


class TestParseSingleExpandField:
    """Test _parse_single_expand_field() helper function."""
    
    def test_simple_field(self):
        """Simple field without nested select."""
        field_name, nested_select = _parse_single_expand_field("author")
        assert field_name == "author"
        assert nested_select is None
    
    def test_field_with_nested_select(self):
        """Field with nested $select."""
        field_name, nested_select = _parse_single_expand_field("author($select=name,email)")
        assert field_name == "author"
        assert nested_select == "name,email"
    
    def test_field_with_spaces(self):
        """Field with spaces should be trimmed."""
        field_name, nested_select = _parse_single_expand_field(" author ")
        assert field_name == "author"
        assert nested_select is None
    
    def test_malformed_parentheses(self):
        """Malformed parentheses should return field as-is."""
        field_name, nested_select = _parse_single_expand_field("author(")
        assert field_name == "author("
        assert nested_select is None
    
    def test_empty_nested_select(self):
        """Empty nested $select."""
        field_name, nested_select = _parse_single_expand_field("author($select=)")
        assert field_name == "author"
        assert nested_select == ""


class TestNativeFieldSelectionMixin:
    """Test NativeFieldSelectionMixin."""
    
    def test_no_context(self):
        """Serializer without context should not crash."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
        
        # Should not raise an error
        serializer = TestSerializer()
        assert 'id' in serializer.fields
        assert 'title' in serializer.fields
    
    def test_empty_context(self):
        """Empty context should show all fields."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
        
        serializer = TestSerializer(context={})
        assert 'id' in serializer.fields
        assert 'title' in serializer.fields
    
    def test_no_select_param(self):
        """No $select parameter should show all fields."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
        
        context = {'odata_params': {}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'title' in serializer.fields
    
    def test_select_single_field(self):
        """$select with single field should show only that field."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
            status = serializers.CharField()
        
        context = {'odata_params': {'$select': 'id'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'title' not in serializer.fields
        assert 'status' not in serializer.fields
    
    def test_select_multiple_fields(self):
        """$select with multiple fields should show only those fields."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
            status = serializers.CharField()
            content = serializers.CharField()
        
        context = {'odata_params': {'$select': 'id,title'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'title' in serializer.fields
        assert 'status' not in serializer.fields
        assert 'content' not in serializer.fields
    
    def test_select_with_spaces(self):
        """$select with spaces should work correctly."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
        
        context = {'odata_params': {'$select': ' id , title '}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'title' in serializer.fields
    
    def test_select_nonexistent_field(self):
        """$select with non-existent field should not crash."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            title = serializers.CharField()
        
        context = {'odata_params': {'$select': 'id,nonexistent'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'title' not in serializer.fields
        assert 'nonexistent' not in serializer.fields
    
    def test_nested_selections_stored_in_context(self):
        """Nested selections should be stored in context."""
        class TestSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            author = serializers.CharField()
        
        context = {'odata_params': {'$select': 'id,author.name,author.email'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'author' in serializer.fields
        assert '_nested_selections' in context
        assert context['_nested_selections'] == {'author': ['name', 'email']}


class TestNativeFieldExpansionMixin:
    """Test NativeFieldExpansionMixin."""
    
    def test_no_context(self):
        """Serializer without context should not crash."""
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {}
        
        # Should not raise an error
        serializer = TestSerializer()
        assert 'id' in serializer.fields
    
    def test_no_expand_param(self):
        """No $expand parameter should not add fields."""
        class AuthorSerializer(serializers.Serializer):
            name = serializers.CharField()
        
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {
                    'author': (AuthorSerializer, {})
                }
        
        context = {'odata_params': {}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'author' not in serializer.fields
    
    def test_no_expandable_fields(self):
        """No expandable_fields in Meta should not crash."""
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
        
        context = {'odata_params': {'$expand': 'author'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'author' not in serializer.fields
    
    def test_expand_single_field(self):
        """$expand with single field should add that field."""
        class AuthorSerializer(serializers.Serializer):
            name = serializers.CharField()
        
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {
                    'author': (AuthorSerializer, {})
                }
        
        context = {'odata_params': {'$expand': 'author'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'author' in serializer.fields
        assert isinstance(serializer.fields['author'], AuthorSerializer)
    
    def test_expand_multiple_fields(self):
        """$expand with multiple fields should add all fields."""
        class AuthorSerializer(serializers.Serializer):
            name = serializers.CharField()
        
        class CategorySerializer(serializers.Serializer):
            name = serializers.CharField()
        
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {
                    'author': (AuthorSerializer, {}),
                    'categories': (CategorySerializer, {'many': True})
                }
        
        context = {'odata_params': {'$expand': 'author,categories'}}
        serializer = TestSerializer(context=context)
        assert 'author' in serializer.fields
        assert 'categories' in serializer.fields
    
    def test_expand_with_nested_select(self):
        """$expand with nested $select should pass it to child serializer."""
        class AuthorSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()
            email = serializers.CharField()
        
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {
                    'author': (AuthorSerializer, {})
                }
        
        context = {'odata_params': {'$expand': 'author($select=name,email)'}}
        serializer = TestSerializer(context=context)
        assert 'author' in serializer.fields
        
        # Check that nested serializer received the $select
        author_serializer = serializer.fields['author']
        assert 'name' in author_serializer.fields
        assert 'email' in author_serializer.fields
        assert 'id' not in author_serializer.fields  # Should be filtered out
    
    def test_expand_nonexistent_field(self):
        """$expand with non-existent field should be ignored."""
        class AuthorSerializer(serializers.Serializer):
            name = serializers.CharField()
        
        class TestSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {
                    'author': (AuthorSerializer, {})
                }
        
        context = {'odata_params': {'$expand': 'nonexistent'}}
        serializer = TestSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'nonexistent' not in serializer.fields
    
    def test_max_expansion_depth(self):
        """Expansion should stop at MAX_EXPANSION_DEPTH."""
        class RecursiveSerializer(NativeFieldExpansionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            
            class Meta:
                expandable_fields = {}
        
        # Set expandable_fields to reference itself (circular)
        RecursiveSerializer.Meta.expandable_fields = {
            'parent': (RecursiveSerializer, {})
        }
        
        context = {
            'odata_params': {'$expand': 'parent'},
            '_expansion_depth': NativeFieldExpansionMixin.MAX_EXPANSION_DEPTH
        }
        
        # Should not crash or recurse infinitely
        serializer = RecursiveSerializer(context=context)
        assert 'id' in serializer.fields
        assert 'parent' not in serializer.fields  # Should not expand due to depth limit


class TestCombinedMixins:
    """Test NativeFieldSelectionMixin and NativeFieldExpansionMixin together."""
    
    def test_select_and_expand_together(self):
        """$select and $expand should work together."""
        class AuthorSerializer(NativeFieldSelectionMixin, serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()
            email = serializers.CharField()
        
        class TestSerializer(
            NativeFieldSelectionMixin,
            NativeFieldExpansionMixin,
            serializers.Serializer
        ):
            id = serializers.IntegerField()
            title = serializers.CharField()
            status = serializers.CharField()
            
            class Meta:
                expandable_fields = {
                    'author': (AuthorSerializer, {})
                }
        
        context = {
            'odata_params': {
                '$select': 'id,title',
                '$expand': 'author($select=name)'
            }
        }
        
        serializer = TestSerializer(context=context)
        
        # Check top-level fields
        assert 'id' in serializer.fields
        assert 'title' in serializer.fields
        assert 'status' not in serializer.fields  # Filtered by $select
        assert 'author' in serializer.fields  # Added by $expand
        
        # Check nested fields
        author_serializer = serializer.fields['author']
        assert 'name' in author_serializer.fields
        assert 'id' not in author_serializer.fields  # Filtered by nested $select
        assert 'email' not in author_serializer.fields  # Filtered by nested $select