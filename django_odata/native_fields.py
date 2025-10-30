"""
Native field selection and expansion for OData serializers.

This module provides native implementations to replace drf-flex-fields dependency,
offering better performance and simpler maintenance while maintaining full API compatibility.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


def parse_select_fields(select_string: str) -> Dict[str, List[str]]:
    """
    Parse OData $select parameter into field structure.
    
    Handles both simple field selection and nested field selection for expanded properties.
    
    Args:
        select_string: Comma-separated list of field names, may include dots for nested fields
                      Example: "id,title,author.name,author.email"
    
    Returns:
        Dictionary with 'top_level' and 'nested' keys:
        {
            'top_level': ['id', 'title', 'author'],
            'nested': {
                'author': ['name', 'email']
            }
        }
    
    Examples:
        >>> parse_select_fields("id,title")
        {'top_level': ['id', 'title'], 'nested': {}}
        
        >>> parse_select_fields("id,title,author.name,author.email")
        {'top_level': ['id', 'title', 'author'], 'nested': {'author': ['name', 'email']}}
    """
    if not select_string or not select_string.strip():
        return {'top_level': [], 'nested': {}}
    
    top_level = []
    nested = {}
    
    # Split by comma and process each field
    fields = [f.strip() for f in select_string.split(',') if f.strip()]
    
    for field in fields:
        if '.' in field:
            # Nested field: "author.name"
            parent, child = field.split('.', 1)
            parent = parent.strip()
            child = child.strip()
            
            # Add parent to top level if not already there
            if parent not in top_level:
                top_level.append(parent)
            
            # Add child to nested structure
            if parent not in nested:
                nested[parent] = []
            if child not in nested[parent]:
                nested[parent].append(child)
        else:
            # Top-level field
            if field not in top_level:
                top_level.append(field)
    
    return {'top_level': top_level, 'nested': nested}


def parse_expand_fields(expand_string: str) -> Dict[str, Optional[str]]:
    """
    Parse OData $expand parameter into expansion structure.
    
    Supports:
    - Simple expansion: "author"
    - Multiple expansions: "author,categories"
    - Nested $select: "author($select=name,email)"
    - Mixed: "author($select=name),categories"
    
    Args:
        expand_string: OData $expand expression
    
    Returns:
        Dictionary mapping field names to their nested $select (or None):
        {
            'author': 'name,email',  # Has nested $select
            'categories': None        # No nested $select
        }
    
    Examples:
        >>> parse_expand_fields("author")
        {'author': None}
        
        >>> parse_expand_fields("author,categories")
        {'author': None, 'categories': None}
        
        >>> parse_expand_fields("author($select=name,email)")
        {'author': 'name,email'}
        
        >>> parse_expand_fields("author($select=name),categories")
        {'author': 'name', 'categories': None}
    """
    if not expand_string or not expand_string.strip():
        return {}
    
    result = {}
    current_field = ""
    paren_depth = 0
    
    # Add comma at end to process last field
    for char in expand_string + ",":
        if char == '(' and paren_depth == 0:
            # Start of nested expression
            paren_depth += 1
            current_field += char
        elif char == '(':
            paren_depth += 1
            current_field += char
        elif char == ')':
            paren_depth -= 1
            current_field += char
        elif char == ',' and paren_depth == 0:
            # End of field at top level
            if current_field.strip():
                field_name, nested_select = _parse_single_expand_field(current_field.strip())
                result[field_name] = nested_select
            current_field = ""
        else:
            current_field += char
    
    return result


def _parse_single_expand_field(field: str) -> Tuple[str, Optional[str]]:
    """
    Parse a single expand field expression.
    
    Args:
        field: Single expand expression, e.g., "author" or "author($select=name,email)"
    
    Returns:
        Tuple of (field_name, nested_select_string or None)
    
    Examples:
        >>> _parse_single_expand_field("author")
        ('author', None)
        
        >>> _parse_single_expand_field("author($select=name,email)")
        ('author', 'name,email')
    """
    # Trim the field first
    field = field.strip()
    
    if '($select=' not in field:
        # Simple field without nested selection
        return field, None
    
    # Parse nested expression: field_name($select=field1,field2,...)
    field_name = field.split('(')[0].strip()
    
    # Extract content inside parentheses
    start_paren = field.find('(')
    end_paren = field.rfind(')')
    
    if start_paren == -1 or end_paren == -1:
        # Malformed, return as simple field
        logger.warning(f"Malformed expand expression: {field}")
        return field, None
    
    inner_content = field[start_paren + 1:end_paren]
    
    # Parse the $select parameter - preserve spaces in the value
    if inner_content.startswith('$select='):
        select_fields = inner_content[8:]  # Remove "$select=" but keep spaces
        return field_name, select_fields
    
    # Not a $select expression
    logger.warning(f"Unknown nested expression in expand: {field}")
    return field, None


class NativeFieldSelectionMixin:
    """
    Mixin for native field selection based on OData $select parameter.
    
    Replaces drf-flex-fields field filtering functionality with a native implementation
    that directly manipulates serializer fields during initialization.
    
    Usage:
        class MySerializer(NativeFieldSelectionMixin, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = '__all__'
    
    The mixin reads the $select parameter from context['odata_params'] and filters
    the serializer's fields accordingly.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize serializer and apply field selection."""
        super().__init__(*args, **kwargs)
        self._apply_field_selection()
    
    def _apply_field_selection(self):
        """
        Apply $select parameter to filter serializer fields.
        
        Algorithm:
        1. Get $select from context['odata_params']
        2. If no $select, return (show all fields)
        3. Parse field list (handle dots for nested fields)
        4. For top-level fields, keep only selected ones
        5. Store nested selections in context for child serializers
        6. Also check $expand to preserve expanded fields
        """
        # Get OData parameters from context
        if not hasattr(self, 'context') or not self.context:
            return
        
        odata_params = self.context.get('odata_params', {})
        select_param = odata_params.get('$select')
        
        if not select_param:
            # No $select parameter, show all fields
            return
        
        # Parse the $select parameter
        parsed = parse_select_fields(select_param)
        top_level_fields = parsed['top_level']
        nested_selections = parsed['nested']
        
        if not top_level_fields:
            # Empty selection, show all fields
            return
        
        # Also include fields from $expand to prevent them from being filtered out
        expand_param = odata_params.get('$expand')
        if expand_param:
            expand_fields = parse_expand_fields(expand_param)
            # Add expanded field names to allowed fields
            top_level_fields = list(set(top_level_fields) | set(expand_fields.keys()))
        
        # Filter fields: keep only selected ones
        allowed_fields = set(top_level_fields)
        existing_fields = list(self.fields.keys())
        
        for field_name in existing_fields:
            if field_name not in allowed_fields:
                self.fields.pop(field_name)
        
        # Store nested selections for child serializers
        if nested_selections:
            if '_nested_selections' not in self.context:
                self.context['_nested_selections'] = {}
            self.context['_nested_selections'].update(nested_selections)


class NativeFieldExpansionMixin:
    """
    Mixin for native field expansion based on OData $expand parameter.
    
    Replaces drf-flex-fields expansion functionality with a native implementation
    that adds related serializers based on Meta.expandable_fields configuration.
    
    Usage:
        class MySerializer(NativeFieldExpansionMixin, serializers.ModelSerializer):
            class Meta:
                model = MyModel
                fields = '__all__'
                expandable_fields = {
                    'author': (AuthorSerializer, {'many': False}),
                    'categories': (CategorySerializer, {'many': True})
                }
    
    The mixin reads the $expand parameter from context['odata_params'] and adds
    the appropriate related serializers to the fields.
    """
    
    MAX_EXPANSION_DEPTH = 3  # Prevent infinite recursion
    
    def __init__(self, *args, **kwargs):
        """Initialize serializer and apply field expansion."""
        super().__init__(*args, **kwargs)
        self._apply_field_expansion()
    
    def _apply_field_expansion(self):
        """
        Apply $expand parameter to add related serializers.
        
        Algorithm:
        1. Get $expand from context['odata_params']
        2. Check expansion depth to prevent infinite recursion
        3. Parse expansion expressions (handle nested $select)
        4. For each expansion:
           a. Look up serializer in Meta.expandable_fields
           b. Create instance with nested context
           c. Add to self.fields
        """
        # Get OData parameters from context
        if not hasattr(self, 'context') or not self.context:
            return
        
        odata_params = self.context.get('odata_params', {})
        expand_param = odata_params.get('$expand')
        
        if not expand_param:
            # No $expand parameter
            return
        
        # Check expansion depth to prevent infinite recursion
        depth = self.context.get('_expansion_depth', 0)
        if depth >= self.MAX_EXPANSION_DEPTH:
            logger.warning(
                f"Maximum expansion depth ({self.MAX_EXPANSION_DEPTH}) reached, "
                f"stopping expansion to prevent infinite recursion"
            )
            return
        
        # Get expandable fields configuration
        if not hasattr(self, 'Meta'):
            logger.debug("No Meta class defined")
            return
            
        expandable = getattr(self.Meta, 'expandable_fields', {})
        if not expandable:
            logger.debug("No expandable_fields defined in Meta")
            return
        
        # Parse the $expand parameter
        expand_fields = parse_expand_fields(expand_param)
        
        # Process each expansion
        for field_name, nested_select in expand_fields.items():
            if field_name not in expandable:
                logger.warning(
                    f"Field '{field_name}' in $expand is not in expandable_fields, ignoring"
                )
                continue
            
            # Get serializer configuration
            serializer_config = expandable[field_name]
            serializer_class, options = self._parse_serializer_config(serializer_config)
            
            # Create nested context with incremented depth
            nested_context = self.context.copy()
            nested_context['_expansion_depth'] = depth + 1
            
            # Add nested $select if provided
            if nested_select:
                nested_odata_params = nested_context.get('odata_params', {}).copy()
                nested_odata_params['$select'] = nested_select
                nested_context['odata_params'] = nested_odata_params
            
            # Instantiate the related serializer and add to fields
            try:
                self.fields[field_name] = serializer_class(
                    context=nested_context,
                    **options
                )
                logger.debug(f"Expanded field '{field_name}' with {serializer_class.__name__}")
            except Exception as e:
                logger.error(f"Error expanding field '{field_name}': {e}")
    
    def _parse_serializer_config(
        self, 
        config: Any
    ) -> Tuple[type, Dict[str, Any]]:
        """
        Parse expandable_fields configuration.
        
        Supports two formats:
        1. Tuple: (SerializerClass, {'many': True})
        2. Just the class: SerializerClass
        
        Args:
            config: Configuration from Meta.expandable_fields
        
        Returns:
            Tuple of (serializer_class, options_dict)
        """
        if isinstance(config, tuple):
            serializer_class = config[0]
            options = config[1] if len(config) > 1 else {}
            
            # Handle string class references (e.g., 'myapp.serializers.AuthorSerializer')
            if isinstance(serializer_class, str):
                serializer_class = self._import_serializer_class(serializer_class)
            
            return serializer_class, options
        else:
            # Just the class
            if isinstance(config, str):
                config = self._import_serializer_class(config)
            return config, {}
    
    def _import_serializer_class(self, class_path: str) -> type:
        """
        Import a serializer class from a string path.
        
        Args:
            class_path: Dotted path to serializer class, e.g., 'myapp.serializers.AuthorSerializer'
        
        Returns:
            The serializer class
        
        Raises:
            ImportError: If the class cannot be imported
        """
        from importlib import import_module
        
        try:
            module_path, class_name = class_path.rsplit('.', 1)
            module = import_module(module_path)
            return getattr(module, class_name)
        except (ValueError, ImportError, AttributeError) as e:
            logger.error(f"Failed to import serializer class '{class_path}': {e}")
            raise ImportError(f"Cannot import serializer class '{class_path}'") from e