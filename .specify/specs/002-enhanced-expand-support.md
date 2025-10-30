# SPEC-002: Enhanced $expand Support with Full OData v4 Compliance

**Status**: Draft  
**Created**: 2025-01-29  
**Priority**: Medium  
**Depends On**: SPEC-001 (Remove drf-flex-fields dependency)

## Overview

Enhance the `$expand` parameter implementation to support full OData v4 specification, including nested query options like `$filter`, `$orderby`, `$top`, `$skip`, and `$count` within expanded navigation properties.

## Current Limitations

Currently, `$expand` only supports nested `$select`:
```
$expand=author($select=name,email)
```

## Proposed Enhancement

Support full OData v4 expand syntax:
```
$expand=Orders($filter=Status eq 'Pending';$orderby=OrderDate desc;$top=5;$count=true)
$expand=author($select=name,email;$expand=posts($top=3))
$expand=categories($filter=active eq true),tags($orderby=name)
```

## Technical Approach

### 1. Leverage `odata-query` Library

Use the existing `odata-query` library (already a dependency) to parse complex `$expand` expressions:

```python
from odata_query import parse_expand

def parse_expand_fields_v2(expand_string: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse OData $expand with full query options support.
    
    Returns:
        {
            'author': {
                '$select': 'name,email',
                '$expand': 'posts',
                '$filter': 'active eq true'
            },
            'categories': {
                '$filter': 'featured eq true',
                '$orderby': 'name',
                '$top': 10
            }
        }
    """
    # Use odata-query to parse the expand expression
    parsed = parse_expand(expand_string)
    return parsed
```

### 2. Update NativeFieldExpansionMixin

Modify the expansion mixin to handle all query options:

```python
class NativeFieldExpansionMixin:
    def _apply_field_expansion(self):
        # Parse expand with all options
        expand_fields = parse_expand_fields_v2(expand_param)
        
        for field_name, options in expand_fields.items():
            # Create nested context with ALL query options
            nested_odata_params = {}
            
            if '$select' in options:
                nested_odata_params['$select'] = options['$select']
            if '$filter' in options:
                nested_odata_params['$filter'] = options['$filter']
            if '$orderby' in options:
                nested_odata_params['$orderby'] = options['$orderby']
            if '$top' in options:
                nested_odata_params['$top'] = options['$top']
            if '$skip' in options:
                nested_odata_params['$skip'] = options['$skip']
            if '$count' in options:
                nested_odata_params['$count'] = options['$count']
            if '$expand' in options:
                nested_odata_params['$expand'] = options['$expand']
            
            nested_context['odata_params'] = nested_odata_params
            
            # Instantiate serializer with full query context
            self.fields[field_name] = serializer_class(
                context=nested_context,
                **serializer_options
            )
```

### 3. Apply Query Options to Related QuerySets

When serializing related objects, apply the nested query options:

```python
class ODataModelSerializer(NativeFieldExpansionMixin, serializers.ModelSerializer):
    def to_representation(self, instance):
        # For each expanded field, apply its query options to the related queryset
        for field_name, field_serializer in self.fields.items():
            if hasattr(field_serializer, 'context'):
                odata_params = field_serializer.context.get('odata_params', {})
                
                # Get related queryset
                related_queryset = getattr(instance, field_name)
                
                # Apply OData query options
                if odata_params:
                    related_queryset = apply_odata_query_params(
                        related_queryset, 
                        odata_params
                    )
                
                # Serialize with filtered queryset
                # ...
```

## Benefits

1. **Full OData v4 Compliance**: Support all standard query options within `$expand`
2. **Better Performance**: Filter and limit related data at the database level
3. **Reduced Payload Size**: Only return necessary related data
4. **Nested Expansion**: Support multi-level expansions with query options at each level
5. **Leverage Existing Library**: Use `odata-query` which is already a dependency

## Implementation Phases

### Phase 1: Research & Design (2 days)
- Study `odata-query` expand parsing capabilities
- Design API for nested query options
- Create test cases for all supported scenarios

### Phase 2: Core Implementation (3 days)
- Implement `parse_expand_fields_v2()` using `odata-query`
- Update `NativeFieldExpansionMixin` to handle all query options
- Add queryset filtering for related objects

### Phase 3: Testing (2 days)
- Unit tests for expand parsing
- Integration tests for nested queries
- Performance benchmarks

### Phase 4: Documentation (1 day)
- Update README with examples
- Add migration guide from simple to enhanced expand
- Document limitations and edge cases

## Examples

### Simple Nested Filter
```
GET /api/posts?$expand=author($filter=active eq true)
```

### Complex Multi-Level Expansion
```
GET /api/posts?$expand=author($select=name;$expand=company($select=name,location)),comments($filter=approved eq true;$orderby=createdAt desc;$top=5)
```

### Pagination in Expanded Collections
```
GET /api/authors?$expand=posts($orderby=publishedAt desc;$top=10;$skip=0;$count=true)
```

## Backward Compatibility

- Maintain support for simple `$expand=field` syntax
- Maintain support for `$expand=field($select=...)` syntax
- All existing queries continue to work unchanged
- New syntax is additive, not breaking

## Success Criteria

- ✅ All OData v4 query options supported within `$expand`
- ✅ Multi-level nested expansions work correctly
- ✅ Performance improvement for filtered expansions
- ✅ 100% backward compatibility maintained
- ✅ Comprehensive test coverage (≥90%)
- ✅ Documentation with real-world examples

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex parsing errors | High | Extensive testing, fallback to simple parsing |
| Performance degradation | Medium | Benchmarking, query optimization |
| Breaking changes | High | Strict backward compatibility testing |
| `odata-query` limitations | Medium | Contribute fixes upstream if needed |

## Dependencies

- **SPEC-001**: Must be completed first (removes drf-flex-fields)
- **odata-query**: Already a dependency, may need version upgrade

## Related Issues

- Improves OData v4 compliance
- Addresses user requests for filtered expansions
- Enables more efficient API queries

## Notes

This enhancement builds on the native field expansion implemented in SPEC-001, extending it to support the full OData v4 specification for `$expand` operations.