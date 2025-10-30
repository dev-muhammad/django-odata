# SPEC-003: Optimize Database Queries with Field Selection

**Status**: Draft  
**Priority**: High  
**Complexity**: Medium  
**Created**: 2025-10-30  
**Owner**: Alexandre Busquets

## Context

The `django-odata` library currently optimizes queries using `select_related()` and `prefetch_related()` for expanded relations to prevent N+1 queries. However, these methods fetch ALL fields from related tables, even when the user only requests specific fields via `$select`.

For example, when a user requests:
```
GET /api/posts?$expand=author($select=name)&$select=id,title
```

The current implementation:
- ✅ Correctly uses `select_related('author')` to prevent N+1 queries
- ❌ Fetches ALL author fields from the database (id, name, email, bio, created_at, etc.)
- ❌ Only filters fields in the serializer layer (after database fetch)

This results in:
- Unnecessary data transfer from database to application
- Increased memory usage
- Slower query execution for tables with many columns or large text fields
- Wasted network bandwidth between database and application

## Objectives

### Primary Goal
Optimize database queries to fetch only the fields requested in `$select` parameters, both for the main entity and for expanded relations.

### Success Metrics
- Database queries fetch only requested fields (verifiable via query logging)
- Performance improvement of 20-40% for queries with field selection
- No breaking changes to existing API
- All existing tests continue to pass
- Query optimization works with both `select_related` and `prefetch_related`

### Non-Goals (Out of Scope)
- Changing the OData API surface
- Adding new query optimization strategies beyond field selection
- Optimizing queries without `$select` (already efficient)
- Database-specific optimizations (must work with all Django-supported databases)

## Current Implementation Analysis

### Files Affected
1. **`django_odata/mixins.py`**
   - `ODataMixin._optimize_queryset_for_expansions()` - Applies select_related/prefetch_related
   - `ODataMixin._apply_query_optimizations()` - Actually calls the Django ORM methods
   - `ODataMixin._get_expand_fields()` - Parses $expand parameter

2. **`django_odata/native_fields.py`**
   - `parse_select_fields()` - Parses $select parameter
   - `parse_expand_fields()` - Parses $expand parameter
   - `NativeFieldExpansionMixin` - Handles field expansion in serializers

### Current Query Behavior

**Example Request:**
```
GET /api/posts?$expand=author($select=name)&$select=id,title
```

**Current SQL (simplified):**
```sql
-- Main query
SELECT posts.id, posts.title, posts.content, posts.created_at, posts.author_id, ...
FROM posts;

-- With select_related('author')
SELECT posts.id, posts.title, posts.content, posts.created_at, posts.author_id,
       authors.id, authors.name, authors.email, authors.bio, authors.created_at, ...
FROM posts
LEFT JOIN authors ON posts.author_id = authors.id;
```

**Desired SQL:**
```sql
-- Only fetch requested fields
SELECT posts.id, posts.title, posts.author_id,
       authors.id, authors.name
FROM posts
LEFT JOIN authors ON posts.author_id = authors.id;
```

### Django ORM Capabilities

Django's QuerySet provides `.only()` and `.defer()` methods:

```python
# Fetch only specific fields
queryset.only('id', 'title', 'author__name')

# Fetch all except specific fields
queryset.defer('content', 'metadata')
```

For `prefetch_related`, we can use `Prefetch` objects:

```python
from django.db.models import Prefetch

queryset.prefetch_related(
    Prefetch(
        'categories',
        queryset=Category.objects.only('id', 'name')
    )
)
```

## Proposed Solution

### Design Approach

Enhance the query optimization logic to:
1. Parse `$select` parameter to identify requested fields
2. Parse `$expand` with nested `$select` to identify requested related fields
3. Build field lists for `only()` method
4. Apply `only()` to both main queryset and prefetch querysets
5. Ensure primary keys and foreign keys are always included (Django requirement)

### Implementation Strategy

#### Phase 1: Add Field Selection to Main Queryset

Modify `ODataMixin.get_queryset()` to apply field selection:

```python
def get_queryset(self):
    """Get the queryset with OData query parameters applied."""
    queryset = super().get_queryset()
    
    # Apply field selection optimization
    queryset = self._apply_field_selection_optimization(queryset)
    
    # Apply query optimizations for expanded relations
    queryset = self._optimize_queryset_for_expansions(queryset)
    
    # Apply OData query parameters
    return self.apply_odata_query(queryset)

def _apply_field_selection_optimization(self, queryset):
    """
    Apply .only() to fetch only requested fields from database.
    
    Algorithm:
    1. Get $select parameter
    2. If no $select, return queryset unchanged (fetch all fields)
    3. Parse selected fields
    4. Add model's primary key (required by Django)
    5. Add foreign key fields for any expanded relations
    6. Apply .only() with the field list
    """
    odata_params = self.get_odata_query_params()
    select_param = odata_params.get('$select')
    
    if not select_param:
        return queryset  # No optimization needed
    
    # Parse selected fields
    from .native_fields import parse_select_fields
    parsed = parse_select_fields(select_param)
    selected_fields = parsed['top_level']
    
    if not selected_fields:
        return queryset
    
    # Build field list for .only()
    only_fields = self._build_only_fields_list(
        queryset.model, 
        selected_fields,
        odata_params
    )
    
    if only_fields:
        queryset = queryset.only(*only_fields)
    
    return queryset

def _build_only_fields_list(self, model, selected_fields, odata_params):
    """
    Build list of fields for .only() method.
    
    Must include:
    - Requested fields from $select
    - Model's primary key (Django requirement)
    - Foreign key fields for expanded relations (Django requirement)
    """
    only_fields = set(selected_fields)
    
    # Always include primary key
    pk_field = model._meta.pk.name
    only_fields.add(pk_field)
    
    # Add foreign key fields for expanded relations
    expand_param = odata_params.get('$expand')
    if expand_param:
        from .native_fields import parse_expand_fields
        expand_fields = parse_expand_fields(expand_param)
        
        for field_name in expand_fields.keys():
            # Check if it's a forward relation (has FK field)
            try:
                field = model._meta.get_field(field_name)
                if hasattr(field, 'attname'):  # FK field has attname (e.g., 'author_id')
                    only_fields.add(field.attname)
            except Exception:
                pass
    
    return list(only_fields)
```

#### Phase 2: Add Field Selection to select_related

Enhance `_apply_query_optimizations()` to use `only()` with `select_related`:

```python
def _apply_query_optimizations(
    self, queryset, select_related_fields, prefetch_related_fields
):
    """Apply select_related and prefetch_related with field selection."""
    
    # Apply select_related with field selection
    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)
        
        # Apply field selection for related models
        queryset = self._apply_related_field_selection(
            queryset, 
            select_related_fields
        )
    
    # Apply prefetch_related with field selection
    if prefetch_related_fields:
        queryset = self._apply_prefetch_with_field_selection(
            queryset,
            prefetch_related_fields
        )
    
    return queryset

def _apply_related_field_selection(self, queryset, select_related_fields):
    """
    Apply field selection to select_related fields using only().
    
    For each related field, determine which fields to fetch based on
    nested $select in $expand parameter.
    """
    odata_params = self.get_odata_query_params()
    expand_param = odata_params.get('$expand')
    
    if not expand_param:
        return queryset
    
    # Parse expand to get nested selections
    from .utils import parse_expand_fields_v2
    expand_fields = parse_expand_fields_v2(expand_param)
    
    # Build only() field list including related fields
    only_fields = []
    
    for related_field in select_related_fields:
        if related_field in expand_fields:
            nested_select = expand_fields[related_field].get('$select')
            
            if nested_select:
                # Parse nested $select
                from .native_fields import parse_select_fields
                parsed = parse_select_fields(nested_select)
                nested_fields = parsed['top_level']
                
                # Get related model
                try:
                    field = queryset.model._meta.get_field(related_field)
                    related_model = field.related_model
                    pk_field = related_model._meta.pk.name
                    
                    # Add pk and selected fields with relation prefix
                    only_fields.append(f"{related_field}__{pk_field}")
                    for nested_field in nested_fields:
                        only_fields.append(f"{related_field}__{nested_field}")
                except Exception as e:
                    logger.warning(f"Could not optimize fields for {related_field}: {e}")
    
    if only_fields:
        # Combine with main model fields
        existing_only = getattr(queryset.query, 'deferred_loading', (None, None))[1]
        if existing_only:
            only_fields.extend(existing_only)
        queryset = queryset.only(*only_fields)
    
    return queryset
```

#### Phase 3: Add Field Selection to prefetch_related

Use `Prefetch` objects with `only()`:

```python
def _apply_prefetch_with_field_selection(self, queryset, prefetch_related_fields):
    """
    Apply prefetch_related with field selection using Prefetch objects.
    """
    from django.db.models import Prefetch
    from .utils import parse_expand_fields_v2
    from .native_fields import parse_select_fields
    
    odata_params = self.get_odata_query_params()
    expand_param = odata_params.get('$expand')
    
    if not expand_param:
        # No field selection, use standard prefetch
        return queryset.prefetch_related(*prefetch_related_fields)
    
    expand_fields = parse_expand_fields_v2(expand_param)
    prefetch_objects = []
    
    for prefetch_field in prefetch_related_fields:
        if prefetch_field in expand_fields:
            nested_select = expand_fields[prefetch_field].get('$select')
            
            if nested_select:
                # Parse nested $select
                parsed = parse_select_fields(nested_select)
                nested_fields = parsed['top_level']
                
                # Get related model and build queryset
                try:
                    field = queryset.model._meta.get_field(prefetch_field)
                    related_model = field.related_model
                    pk_field = related_model._meta.pk.name
                    
                    # Build only() field list
                    only_fields = [pk_field] + nested_fields
                    
                    # Create Prefetch object with optimized queryset
                    prefetch_queryset = related_model.objects.only(*only_fields)
                    prefetch_objects.append(
                        Prefetch(prefetch_field, queryset=prefetch_queryset)
                    )
                except Exception as e:
                    logger.warning(f"Could not optimize prefetch for {prefetch_field}: {e}")
                    # Fallback to standard prefetch
                    prefetch_objects.append(prefetch_field)
            else:
                # No nested $select, use standard prefetch
                prefetch_objects.append(prefetch_field)
        else:
            # Not in expand, use standard prefetch
            prefetch_objects.append(prefetch_field)
    
    return queryset.prefetch_related(*prefetch_objects)
```

### Edge Cases to Handle

1. **No $select parameter**: Should fetch all fields (current behavior)
2. **$select without $expand**: Should optimize main query only
3. **$expand without nested $select**: Should fetch all fields from related model
4. **$expand with nested $select**: Should fetch only specified related fields
5. **Primary key not in $select**: Must be included automatically (Django requirement)
6. **Foreign key fields**: Must be included when relation is expanded
7. **Deferred fields and only() interaction**: Must handle correctly
8. **Multiple levels of expansion**: Should work recursively (within depth limit)
9. **Many-to-many relations**: Must work with prefetch_related
10. **Reverse relations**: Must work with prefetch_related

### Error Handling

```python
# Validate field names exist on model
def _validate_field_names(self, model, field_names):
    """Validate that field names exist on the model."""
    valid_fields = {f.name for f in model._meta.get_fields()}
    invalid_fields = set(field_names) - valid_fields
    
    if invalid_fields:
        logger.warning(
            f"Invalid field names in $select for {model.__name__}: "
            f"{', '.join(invalid_fields)}"
        )
        # Remove invalid fields
        return [f for f in field_names if f in valid_fields]
    
    return field_names
```

## Testing Strategy

### Unit Tests

1. **Field Selection Tests** (`tests/test_field_optimization.py`)
   ```python
   def test_only_selected_fields_fetched():
       """Test that only() is applied with $select parameter."""
       
   def test_primary_key_always_included():
       """Test that PK is included even if not in $select."""
       
   def test_foreign_keys_included_for_expand():
       """Test that FK fields are included when relation is expanded."""
   ```

2. **select_related Optimization Tests**
   ```python
   def test_select_related_with_nested_select():
       """Test field selection with select_related."""
       
   def test_select_related_without_nested_select():
       """Test select_related fetches all fields when no nested $select."""
   ```

3. **prefetch_related Optimization Tests**
   ```python
   def test_prefetch_related_with_nested_select():
       """Test field selection with prefetch_related using Prefetch objects."""
       
   def test_prefetch_related_many_to_many():
       """Test optimization works with M2M relations."""
   ```

### Integration Tests

Test complete request/response cycles with query logging:

```python
def test_optimized_query_execution(django_assert_num_queries):
    """Test that optimized queries execute correctly."""
    
    # Enable query logging
    with CaptureQueriesContext(connection) as queries:
        response = client.get('/posts', {
            '$select': 'id,title',
            '$expand': 'author($select=name)'
        })
        
        # Verify response is correct
        assert response.status_code == 200
        
        # Verify SQL only includes requested fields
        sql = queries[0]['sql']
        assert 'posts.id' in sql
        assert 'posts.title' in sql
        assert 'authors.name' in sql
        assert 'posts.content' not in sql  # Not requested
        assert 'authors.email' not in sql  # Not requested
```

### Performance Tests

Benchmark queries with and without field selection:

```python
def test_performance_improvement_with_field_selection(benchmark):
    """Benchmark query performance with field selection."""
    
    def query_with_selection():
        return list(Post.objects.filter(
            id__lte=100
        ).only('id', 'title', 'author__name').select_related('author'))
    
    def query_without_selection():
        return list(Post.objects.filter(
            id__lte=100
        ).select_related('author'))
    
    # Benchmark both
    time_with = benchmark(query_with_selection)
    time_without = benchmark(query_without_selection)
    
    # Assert improvement
    assert time_with < time_without * 0.8  # At least 20% faster
```

## Migration Path

### For Library Developers (Internal)

**Step 1: Implement field selection for main queryset**
- Add `_apply_field_selection_optimization()` method
- Add `_build_only_fields_list()` method
- Test with unit tests

**Step 2: Implement field selection for select_related**
- Add `_apply_related_field_selection()` method
- Test with integration tests

**Step 3: Implement field selection for prefetch_related**
- Add `_apply_prefetch_with_field_selection()` method
- Test with M2M relations

**Step 4: Integration and testing**
- Run full test suite
- Performance benchmarking
- Update documentation

### For Library Users (External)

**No changes required!** This is a pure optimization that happens transparently:

```python
# Before and After - same code, better performance
response = client.get('/api/posts', {
    '$select': 'id,title',
    '$expand': 'author($select=name)'
})
```

Users will automatically benefit from:
- Faster queries
- Lower memory usage
- Reduced database load

## Risks and Mitigations

### Risk 1: Django ORM Limitations
**Risk**: `only()` has edge cases and limitations in Django  
**Mitigation**:
- Thoroughly test with different Django versions
- Always include PK and FK fields
- Provide fallback to non-optimized queries if errors occur
- Document known limitations

### Risk 2: Breaking Deferred Field Access
**Risk**: Code accessing non-selected fields will trigger additional queries  
**Mitigation**:
- Only apply optimization when `$select` is explicitly provided
- Serializers already filter fields, so this shouldn't be an issue
- Add logging to detect unexpected field access

### Risk 3: Complex Query Interactions
**Risk**: Interaction with other QuerySet methods (annotate, aggregate, etc.)  
**Mitigation**:
- Test with complex queries
- Apply optimization early in query chain
- Document any known incompatibilities

### Risk 4: Performance Regression in Some Cases
**Risk**: `only()` might be slower for small tables or simple queries  
**Mitigation**:
- Benchmark various scenarios
- Only apply when `$select` is provided (opt-in)
- Make optimization configurable if needed

## Implementation Checklist

### Phase 1: Main Queryset Optimization
- [ ] Implement `_apply_field_selection_optimization()`
- [ ] Implement `_build_only_fields_list()`
- [ ] Add unit tests for field selection
- [ ] Test with various $select patterns

### Phase 2: select_related Optimization
- [ ] Implement `_apply_related_field_selection()`
- [ ] Add tests for nested field selection
- [ ] Verify FK fields are included
- [ ] Test with multiple related fields

### Phase 3: prefetch_related Optimization
- [ ] Implement `_apply_prefetch_with_field_selection()`
- [ ] Add tests for Prefetch objects
- [ ] Test with M2M relations
- [ ] Test with reverse relations

### Phase 4: Testing & Validation
- [ ] Run full test suite
- [ ] Performance benchmarking
- [ ] Query logging verification
- [ ] Edge case testing

### Phase 5: Documentation
- [ ] Update README with performance notes
- [ ] Document optimization behavior
- [ ] Add examples to documentation
- [ ] Update CHANGELOG

## Success Criteria

### Must Have
- ✅ Queries fetch only requested fields when `$select` is used
- ✅ All existing tests pass
- ✅ No breaking changes to API
- ✅ Works with both select_related and prefetch_related

### Should Have
- ✅ 20-40% performance improvement for selective queries
- ✅ Query logging shows optimized SQL
- ✅ Works with nested expansions
- ✅ Handles edge cases gracefully

### Nice to Have
- ✅ Configurable optimization level
- ✅ Query optimization metrics/logging
- ✅ Performance comparison documentation

## References

- [Django QuerySet.only() Documentation](https://docs.djangoproject.com/en/stable/ref/models/querysets/#only)
- [Django QuerySet.defer() Documentation](https://docs.djangoproject.com/en/stable/ref/models/querysets/#defer)
- [Django Prefetch Objects](https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-objects)
- [OData v4.0 $select System Query Option](http://docs.oasis-open.org/odata/odata/v4.0/odata-v4.0-part2-url-conventions.html#_Toc372793790)
- Project Repository: https://github.com/alexandre-fundcraft/fc-django-odata

---

**Approval Required From**: @alexandre-fundcraft  
**Estimated Effort**: 1-2 weeks  
**Target Release**: v2.1.0