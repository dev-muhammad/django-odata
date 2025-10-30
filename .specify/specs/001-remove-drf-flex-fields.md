# SPEC-001: Remove drf-flex-fields Dependency

**Status**: Draft  
**Priority**: High  
**Complexity**: Medium  
**Created**: 2025-10-29  
**Owner**: Alexandre Busquets

## Context

The `django-odata` library currently depends on `drf-flex-fields` for dynamic field selection and expansion. This dependency adds:
- External maintenance burden
- Potential version conflicts with user projects
- Complexity in understanding how field expansion works
- Performance overhead from the abstraction layer

The library should provide native field selection and expansion that:
- Is more performant (fewer abstraction layers)
- Is easier to understand and maintain
- Has zero external dependencies
- Maintains API compatibility with existing users

## Objectives

### Primary Goal
Remove `drf-flex-fields` dependency while maintaining 100% backward compatibility with existing API.

### Success Metrics
- Zero failing tests after migration
- No performance regression (ideally 10-20% improvement)
- API remains unchanged for end users
- Documentation reflects new implementation
- Example project works without changes

### Non-Goals (Out of Scope)
- Adding new OData features
- Changing API surface
- Refactoring other parts of the codebase
- Performance optimizations beyond removing the dependency

## Current Implementation Analysis

### Files Affected
1. **`django_odata/serializers.py`**
   - `ODataSerializer` extends `FlexFieldsSerializerMixin`
   - `ODataModelSerializer` extends `FlexFieldsModelSerializer`
   - Uses `expandable_fields` Meta attribute

2. **`django_odata/mixins.py`**
   - `ODataSerializerMixin` processes $select and $expand
   - Converts OData params to FlexFields params (fields, expand)
   - Handles nested field selections

3. **`requirements.txt`**
   - `drf-flex-fields>=1.0.0` dependency

### How drf-flex-fields Works
1. Checks `request.query_params` for `fields`, `omit`, `expand`
2. Dynamically filters serializer fields based on these params
3. Handles nested serializer expansion
4. Supports sparse fieldsets

### What We Use From drf-flex-fields
- **FlexFieldsSerializerMixin**: Field filtering logic
- **FlexFieldsModelSerializer**: Model serializer with field filtering
- **expandable_fields** Meta attribute: Defines which fields can be expanded

### What We DON'T Use
- Deep nesting beyond level 1
- Complex field expansion options
- Field omit functionality (we use $select exclusively)
- Advanced FlexFields features

## Proposed Solution

### Design Approach
Replace `drf-flex-fields` with a native implementation that:
1. Intercepts serializer initialization
2. Modifies `fields` based on `$select` parameter
3. Handles field expansion based on `$expand` parameter
4. Maintains the same external API

### Implementation Strategy

#### Phase 1: Create Native Field Selection
Create a new mixin `NativeFieldSelectionMixin` that:
- Reads `$select` from OData params
- Filters serializer fields during `__init__`
- Handles nested field selection (e.g., `posts.id,posts.title`)

```python
class NativeFieldSelectionMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_selection()
    
    def _apply_field_selection(self):
        # Parse $select parameter
        # Filter self.fields based on selection
        pass
```

#### Phase 2: Create Native Field Expansion
Create a new mixin `NativeFieldExpansionMixin` that:
- Reads `$expand` from OData params
- Adds related serializers to fields
- Handles nested expansion with $select

```python
class NativeFieldExpansionMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_expansion()
    
    def _apply_field_expansion(self):
        # Parse $expand parameter
        # Add related serializers to self.fields
        pass
```

#### Phase 3: Update OData Serializers
Modify existing serializers to use new mixins:
```python
class ODataModelSerializer(
    ODataSerializerMixin,
    NativeFieldSelectionMixin,
    NativeFieldExpansionMixin,
    serializers.ModelSerializer
):
    pass
```

#### Phase 4: Maintain expandable_fields Compatibility
Ensure `Meta.expandable_fields` still works:
```python
class Meta:
    model = Post
    fields = '__all__'
    expandable_fields = {
        'author': ('blog.AuthorSerializer', {'many': False}),
        'categories': ('blog.CategorySerializer', {'many': True})
    }
```

### API Compatibility

#### Before (with drf-flex-fields)
```python
GET /api/posts?$select=id,title&$expand=author
GET /api/posts?$expand=author($select=name,email)
```

#### After (native implementation)
```python
GET /api/posts?$select=id,title&$expand=author
GET /api/posts?$expand=author($select=name,email)
```
Same API, same behavior, different implementation.

## Technical Design

### Class Hierarchy Changes

**Before:**
```
FlexFieldsSerializerMixin
    ↓
FlexFieldsModelSerializer
    ↓
ODataSerializerMixin
    ↓
ODataModelSerializer
```

**After:**
```
serializers.ModelSerializer
    ↓
NativeFieldSelectionMixin
    ↓
NativeFieldExpansionMixin
    ↓
ODataSerializerMixin
    ↓
ODataModelSerializer
```

### Key Algorithms

#### Field Selection Algorithm
```python
def _apply_field_selection(self):
    """
    Apply $select parameter to filter fields.
    
    Algorithm:
    1. Get $select from context
    2. If no $select, return (show all fields)
    3. Parse field list (handle dots for nested)
    4. For top-level fields, keep only selected
    5. For nested fields, pass to nested serializers
    """
    odata_params = self.context.get('odata_params', {})
    select_fields = parse_select(odata_params.get('$select'))
    
    if not select_fields:
        return  # Show all fields
    
    # Split into top-level and nested
    top_level, nested = split_field_paths(select_fields)
    
    # Filter top-level fields
    existing = set(self.fields.keys())
    allowed = set(top_level)
    for field_name in existing - allowed:
        self.fields.pop(field_name)
    
    # Store nested selections for child serializers
    self._nested_selections = nested
```

#### Field Expansion Algorithm
```python
def _apply_field_expansion(self):
    """
    Apply $expand parameter to add related serializers.
    
    Algorithm:
    1. Get $expand from context
    2. Parse expansion expressions (handle nested $select)
    3. For each expansion:
       a. Look up serializer in Meta.expandable_fields
       b. Create instance with nested context
       c. Add to self.fields
    """
    odata_params = self.context.get('odata_params', {})
    expand_fields = parse_expand(odata_params.get('$expand'))
    
    if not expand_fields:
        return
    
    expandable = getattr(self.Meta, 'expandable_fields', {})
    
    for field_name, nested_select in expand_fields.items():
        if field_name not in expandable:
            continue
        
        serializer_class, options = expandable[field_name]
        
        # Create nested context with $select
        nested_context = self.context.copy()
        if nested_select:
            nested_context['odata_params'] = {'$select': nested_select}
        
        # Instantiate and add to fields
        self.fields[field_name] = serializer_class(
            context=nested_context,
            **options
        )
```

### Edge Cases to Handle

1. **Empty $select**: Should show all fields
2. **Invalid field names**: Should ignore silently or raise error?
3. **Nested $select without $expand**: Should be ignored
4. **Circular references**: Prevent infinite recursion
5. **$expand on non-expandable field**: Ignore or error?
6. **$select with $expand**: Both should work together
7. **Many=True relations**: Should use `many=True` in serializer

### Error Handling

```python
# Validate field names
if '$select' in odata_params:
    fields = parse_select(odata_params['$select'])
    valid_fields = set(self.fields.keys())
    invalid = set(fields) - valid_fields
    if invalid:
        # Option 1: Ignore silently (current behavior)
        # Option 2: Raise validation error
        pass

# Validate expandable fields
if '$expand' in odata_params:
    fields = parse_expand(odata_params['$expand'])
    expandable = set(getattr(self.Meta, 'expandable_fields', {}).keys())
    invalid = set(fields.keys()) - expandable
    if invalid:
        # Option 1: Ignore silently
        # Option 2: Raise validation error
        pass
```

## Testing Strategy

### Unit Tests
1. **Field Selection Tests**
   - Select single field
   - Select multiple fields
   - Select all fields (empty $select)
   - Select non-existent field
   - Select nested fields

2. **Field Expansion Tests**
   - Expand single relation
   - Expand multiple relations
   - Expand with nested $select
   - Expand many=True relation
   - Expand non-expandable field

3. **Combined Tests**
   - $select + $expand together
   - Nested $expand with $select
   - Complex query scenarios

### Integration Tests
Test complete request/response cycles:
```python
def test_select_and_expand():
    """Test: GET /posts?$select=id,title&$expand=author($select=name)"""
    response = client.get('/posts', {
        '$select': 'id,title',
        '$expand': 'author($select=name)'
    })
    assert response.json() == {
        'value': [
            {
                'id': 1,
                'title': 'Post 1',
                'author': {'name': 'John'}
            }
        ]
    }
```

### Regression Tests
Run existing test suite with new implementation:
```bash
pytest tests/ -v --cov=django_odata
```

Should have:
- 100% of existing tests passing
- Same or better performance
- Same behavior for all edge cases

### Performance Tests
Benchmark before and after:
```python
def test_performance_field_selection():
    """Benchmark $select performance"""
    # Before: with drf-flex-fields
    # After: with native implementation
    # Assert: no regression (or improvement)
```

## Migration Path

### For Library Developers (Internal)

**Step 1: Create new mixins**
```bash
# Create new file
touch django_odata/native_fields.py
```

**Step 2: Implement and test in isolation**
```python
# Implement NativeFieldSelectionMixin
# Test thoroughly with unit tests
```

**Step 3: Update serializers**
```python
# Replace FlexFieldsModelSerializer
# with native mixins
```

**Step 4: Run full test suite**
```bash
pytest tests/ -v
```

**Step 5: Update requirements**
```bash
# Remove drf-flex-fields from requirements.txt
```

**Step 6: Update documentation**
```bash
# Update README
# Update API docs
# Add migration notes
```

### For Library Users (External)

**No changes required!** The API remains the same:

```python
# Before and After - same code works
class PostSerializer(ODataModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'
        expandable_fields = {
            'author': (AuthorSerializer, {'many': False})
        }
```

Users can upgrade without any code changes:
```bash
pip install --upgrade django-odata
```

## Risks and Mitigations

### Risk 1: Hidden FlexFields Features
**Risk**: Users might depend on FlexFields features we don't know about  
**Mitigation**: 
- Review all FlexFields documentation
- Search GitHub for usage patterns
- Add deprecation warning in previous version
- Provide 6-month overlap period

### Risk 2: Performance Regression
**Risk**: Native implementation might be slower  
**Mitigation**:
- Benchmark current performance first
- Profile new implementation
- Optimize hot paths
- Add performance regression tests to CI

### Risk 3: Breaking Edge Cases
**Risk**: Edge cases might behave differently  
**Mitigation**:
- Comprehensive test coverage
- Beta release for early adopters
- Clear changelog documentation
- Easy rollback path (keep old version available)

### Risk 4: Circular Reference Handling
**Risk**: Infinite recursion with circular model relations  
**Mitigation**:
- Track expansion depth in context
- Limit maximum depth (e.g., 3 levels)
- Detect circular references
- Clear error messages

## Implementation Checklist

### Phase 1: Preparation
- [x] Document current behavior
- [ ] Create performance baseline
- [ ] Review all FlexFields usage
- [ ] Identify all test cases

### Phase 2: Implementation
- [ ] Create `NativeFieldSelectionMixin`
- [ ] Create `NativeFieldExpansionMixin`
- [ ] Write unit tests for new mixins
- [ ] Update `ODataModelSerializer`
- [ ] Update `ODataSerializer`

### Phase 3: Testing
- [ ] Run existing test suite
- [ ] Add new test cases
- [ ] Performance benchmarking
- [ ] Integration testing with example project

### Phase 4: Documentation
- [ ] Update README
- [ ] Update API documentation
- [ ] Create migration guide
- [ ] Update changelog

### Phase 5: Release
- [ ] Remove drf-flex-fields from requirements
- [ ] Beta release (e.g., 2.0.0b1)
- [ ] Gather feedback
- [ ] Stable release (e.g., 2.0.0)

## Open Questions

1. **Should we keep expandable_fields or introduce a new API?**
   - Keeping it maintains compatibility
   - New API could be more explicit
   - **Decision**: Keep for v2.0, consider new API in v3.0

2. **How strict should field validation be?**
   - Ignore invalid fields (current)?
   - Return error for invalid fields?
   - **Decision**: Start strict, add lenient mode if needed

3. **Should we support FlexFields' omit parameter?**
   - Not part of OData spec
   - Could be useful for users
   - **Decision**: No, keep OData compliance

4. **Maximum expansion depth?**
   - Unlimited (risk of recursion)?
   - Fixed limit (3 levels)?
   - **Decision**: Start with 3, make configurable

## Success Criteria

### Must Have
- ✅ All existing tests pass
- ✅ Zero external dependencies added
- ✅ API compatibility maintained
- ✅ Documentation updated

### Should Have
- ✅ 10% performance improvement
- ✅ Code coverage maintained (>90%)
- ✅ Example project works unchanged

### Nice to Have
- ✅ Better error messages
- ✅ Simpler codebase
- ✅ Easier to debug

## References

- [OData v4.0 Specification](http://docs.oasis-open.org/odata/odata/v4.0/odata-v4.0-part2-url-conventions.html)
- [drf-flex-fields Documentation](https://github.com/rsinger86/drf-flex-fields)
- [Django REST Framework Serializers](https://www.django-rest-framework.org/api-guide/serializers/)
- Project Repository: https://github.com/alexandre-fundcraft/fc-django-odata

---

**Approval Required From**: @alexandre-fundcraft  
**Estimated Effort**: 2-3 weeks  
**Target Release**: v2.0.0
