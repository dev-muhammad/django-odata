# PLAN-003: Optimize Database Queries with Field Selection

**Related Spec**: SPEC-003  
**Status**: Ready for Implementation  
**Created**: 2025-10-30  
**Estimated Duration**: 1-2 weeks

## Overview

This plan details the implementation of database query optimization using Django's `.only()` method to fetch only requested fields from the database. The optimization applies to both main queries and expanded relations (via `select_related` and `prefetch_related`).

**Key Principle**: Only apply optimization when `$select` is explicitly provided, maintaining backward compatibility.

## Implementation Phases

### Phase 1: Main Queryset Field Selection (2 days)

#### 1.1 Add Field Selection Helper Methods
**File**: `django_odata/mixins.py`  
**Task**: Add helper methods for building field lists

**Code to Add**:
```python
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

**Acceptance**: 
- Methods added to `ODataMixin` class
- Code compiles without errors
- Helper methods are properly documented

#### 1.2 Integrate Field Selection into get_queryset
**File**: `django_odata/mixins.py`  
**Task**: Modify `get_queryset()` to apply field selection

**Code to Modify**:
```python
def get_queryset(self):
    """
    Get the queryset with OData query parameters applied and optimized for field selection.
    """
    queryset = super().get_queryset()

    # Apply field selection optimization BEFORE expansion optimization
    queryset = self._apply_field_selection_optimization(queryset)

    # Apply query optimizations for expanded relations
    queryset = self._optimize_queryset_for_expansions(queryset)

    # Apply OData query parameters
    return self.apply_odata_query(queryset)
```

**Acceptance**:
- Field selection applied before expansion optimization
- Existing tests still pass
- No breaking changes to API

#### 1.3 Add Unit Tests for Main Queryset Optimization
**File**: `tests/test_field_optimization.py` (new file)  
**Task**: Create comprehensive unit tests

**Tests to Add**:
```python
import pytest
from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext


class TestFieldSelectionOptimization(TestCase):
    """Test field selection optimization with .only()"""
    
    def test_only_selected_fields_fetched(self):
        """Test that only() is applied with $select parameter."""
        # Test that queryset uses .only() when $select is provided
        pass
    
    def test_primary_key_always_included(self):
        """Test that PK is included even if not in $select."""
        # Verify PK is in only() field list
        pass
    
    def test_foreign_keys_included_for_expand(self):
        """Test that FK fields are included when relation is expanded."""
        # Verify FK fields added when $expand is present
        pass
    
    def test_no_optimization_without_select(self):
        """Test that no .only() is applied without $select."""
        # Verify queryset unchanged when no $select
        pass
    
    def test_empty_select_returns_all_fields(self):
        """Test that empty $select returns all fields."""
        # Edge case: $select with empty value
        pass
```

**Acceptance**:
- All tests pass
- Tests cover main scenarios and edge cases
- Tests verify SQL queries using CaptureQueriesContext

### Phase 2: select_related Field Selection (3 days)

#### 2.1 Add Related Field Selection Method
**File**: `django_odata/mixins.py`  
**Task**: Implement field selection for select_related

**Code to Add**:
```python
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
        # Get existing only() fields from main queryset
        existing_only = self._get_existing_only_fields(queryset)
        if existing_only:
            only_fields.extend(existing_only)
        queryset = queryset.only(*only_fields)
    
    return queryset

def _get_existing_only_fields(self, queryset):
    """Extract existing only() fields from queryset."""
    deferred_loading = getattr(queryset.query, 'deferred_loading', (None, None))
    if deferred_loading[0]:  # Has only() fields
        return list(deferred_loading[0])
    return []
```

**Acceptance**:
- Method properly handles nested $select in $expand
- Combines with existing only() fields
- Handles errors gracefully

#### 2.2 Integrate into Query Optimization
**File**: `django_odata/mixins.py`  
**Task**: Update `_apply_query_optimizations()` to use field selection

**Code to Modify**:
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
    
    # Apply prefetch_related (will be enhanced in Phase 3)
    if prefetch_related_fields:
        queryset = queryset.prefetch_related(*prefetch_related_fields)
    
    return queryset
```

**Acceptance**:
- Field selection applied after select_related
- Existing functionality preserved
- Tests pass

#### 2.3 Add Tests for select_related Optimization
**File**: `tests/test_field_optimization.py`  
**Task**: Add tests for select_related field selection

**Tests to Add**:
```python
def test_select_related_with_nested_select(self):
    """Test field selection with select_related."""
    # Verify only nested $select fields are fetched
    pass

def test_select_related_without_nested_select(self):
    """Test select_related fetches all fields when no nested $select."""
    # Verify all related fields fetched without nested $select
    pass

def test_select_related_multiple_relations(self):
    """Test field selection with multiple select_related."""
    # Test with multiple expanded relations
    pass

def test_select_related_pk_always_included(self):
    """Test related model PK is always included."""
    # Verify related PK in field list
    pass
```

**Acceptance**:
- All tests pass
- SQL queries verified with CaptureQueriesContext
- Edge cases covered

### Phase 3: prefetch_related Field Selection (3 days)

#### 3.1 Add Prefetch Field Selection Method
**File**: `django_odata/mixins.py`  
**Task**: Implement field selection for prefetch_related using Prefetch objects

**Code to Add**:
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

**Acceptance**:
- Prefetch objects created with optimized querysets
- Fallback to standard prefetch on errors
- Handles both string and Prefetch object inputs

#### 3.2 Integrate Prefetch Optimization
**File**: `django_odata/mixins.py`  
**Task**: Update `_apply_query_optimizations()` to use prefetch field selection

**Code to Modify**:
```python
def _apply_query_optimizations(
    self, queryset, select_related_fields, prefetch_related_fields
):
    """Apply select_related and prefetch_related with field selection."""
    
    # Apply select_related with field selection
    if select_related_fields:
        queryset = queryset.select_related(*select_related_fields)
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
```

**Acceptance**:
- Prefetch optimization integrated
- Both select_related and prefetch_related optimized
- Tests pass

#### 3.3 Add Tests for prefetch_related Optimization
**File**: `tests/test_field_optimization.py`  
**Task**: Add tests for prefetch_related field selection

**Tests to Add**:
```python
def test_prefetch_related_with_nested_select(self):
    """Test field selection with prefetch_related using Prefetch objects."""
    # Verify Prefetch objects created with only()
    pass

def test_prefetch_related_many_to_many(self):
    """Test optimization works with M2M relations."""
    # Test M2M field optimization
    pass

def test_prefetch_related_reverse_fk(self):
    """Test optimization works with reverse FK relations."""
    # Test reverse relation optimization
    pass

def test_prefetch_related_without_nested_select(self):
    """Test prefetch without nested $select uses standard prefetch."""
    # Verify fallback behavior
    pass
```

**Acceptance**:
- All tests pass
- Prefetch objects verified
- M2M and reverse relations tested

### Phase 4: Integration Testing & Performance (2 days)

#### 4.1 Add Integration Tests
**File**: `tests/integration/test_field_optimization_integration.py` (new file)  
**Task**: Create end-to-end integration tests

**Tests to Add**:
```python
from django.test import TestCase, Client
from django.test.utils import CaptureQueriesContext
from django.db import connection


class TestFieldOptimizationIntegration(TestCase):
    """Integration tests for field optimization."""
    
    def setUp(self):
        self.client = Client()
        # Create test data
        pass
    
    def test_complete_request_with_field_selection(self):
        """Test complete request/response with field optimization."""
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/odata/posts/', {
                '$select': 'id,title',
                '$expand': 'author($select=name)'
            })
            
            # Verify response
            assert response.status_code == 200
            
            # Verify SQL optimization
            sql = queries[0]['sql']
            assert 'posts.id' in sql
            assert 'posts.title' in sql
            assert 'authors.name' in sql
            assert 'posts.content' not in sql
            assert 'authors.email' not in sql
    
    def test_complex_nested_expansion(self):
        """Test field optimization with complex nested expansions."""
        # Test multiple levels of expansion
        pass
    
    def test_mixed_select_related_and_prefetch(self):
        """Test optimization with both select_related and prefetch_related."""
        # Test combined optimization
        pass
```

**Acceptance**:
- Integration tests pass
- SQL queries verified
- Real request/response cycle tested

#### 4.2 Add Performance Benchmarks
**File**: `tests/performance/test_field_optimization_performance.py` (new file)  
**Task**: Create performance benchmark tests

**Tests to Add**:
```python
import pytest
from django.test import TestCase


class TestFieldOptimizationPerformance(TestCase):
    """Performance benchmarks for field optimization."""
    
    @pytest.mark.benchmark
    def test_performance_with_field_selection(self, benchmark):
        """Benchmark query performance with field selection."""
        
        def query_with_selection():
            # Query with $select
            pass
        
        result = benchmark(query_with_selection)
        # Assert performance metrics
    
    @pytest.mark.benchmark
    def test_performance_without_field_selection(self, benchmark):
        """Benchmark query performance without field selection."""
        
        def query_without_selection():
            # Query without $select
            pass
        
        result = benchmark(query_without_selection)
    
    def test_performance_improvement(self):
        """Verify performance improvement with field selection."""
        # Compare with/without optimization
        # Assert at least 20% improvement
        pass
```

**Acceptance**:
- Benchmarks run successfully
- Performance improvement verified (20-40%)
- Results documented

#### 4.3 Run Full Test Suite
**Task**: Ensure all existing tests still pass

**Commands**:
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=django_odata --cov-report=html

# Run performance tests
pytest tests/performance/ --benchmark-only
```

**Acceptance**:
- All existing tests pass
- No regressions introduced
- Coverage maintained ≥90%

### Phase 5: Documentation & Release (2 days)

#### 5.1 Update README
**File**: `README.md`  
**Task**: Add documentation about field optimization

**Content to Add**:
```markdown
### Performance Optimization

Django OData automatically optimizes database queries when you use the `$select` parameter:

```python
# Only fetches id and title from database
GET /odata/posts?$select=id,title

# Fetches only specified fields from related models
GET /odata/posts?$select=id,title&$expand=author($select=name)
```

This optimization:
- Reduces data transfer from database to application
- Lowers memory usage
- Improves query performance by 20-40% for selective queries
- Works automatically with both `select_related` and `prefetch_related`

**Note**: Optimization only applies when `$select` is explicitly provided.
```

**Acceptance**:
- README updated with clear examples
- Performance benefits documented
- Usage examples provided

#### 5.2 Update CHANGELOG
**File**: `CHANGELOG.md`  
**Task**: Document the new feature

**Content to Add**:
```markdown
## [Unreleased]

### Added
- **Field Selection Optimization** (#003)
  - Database queries now fetch only requested fields when `$select` is used
  - Applies to both main queries and expanded relations
  - Uses Django's `.only()` method with `select_related()`
  - Uses `Prefetch` objects with `prefetch_related()`
  - 20-40% performance improvement for selective queries
  - Automatic optimization with zero configuration required

### Performance
- Reduced database-to-application data transfer
- Lower memory usage for queries with field selection
- Faster execution for tables with many columns
```

**Acceptance**:
- CHANGELOG updated
- Changes clearly documented
- Version number updated if needed

#### 5.3 Add Code Documentation
**File**: `django_odata/mixins.py`  
**Task**: Ensure all new methods have comprehensive docstrings

**Acceptance**:
- All methods have Google-style docstrings
- Parameters and return values documented
- Examples provided where helpful
- Edge cases noted

## Task Dependencies

```
Phase 1 (Main Queryset)
  ├─ 1.1 Helper Methods
  ├─ 1.2 Integration
  └─ 1.3 Unit Tests
      ↓
Phase 2 (select_related)
  ├─ 2.1 Related Field Selection
  ├─ 2.2 Integration
  └─ 2.3 Tests
      ↓
Phase 3 (prefetch_related)
  ├─ 3.1 Prefetch Field Selection
  ├─ 3.2 Integration
  └─ 3.3 Tests
      ↓
Phase 4 (Integration & Performance)
  ├─ 4.1 Integration Tests
  ├─ 4.2 Performance Benchmarks
  └─ 4.3 Full Test Suite
      ↓
Phase 5 (Documentation)
  ├─ 5.1 README
  ├─ 5.2 CHANGELOG
  └─ 5.3 Code Documentation
```

## Timeline Estimate

- **Phase 1**: 2 days (Main queryset optimization)
- **Phase 2**: 3 days (select_related optimization)
- **Phase 3**: 3 days (prefetch_related optimization)
- **Phase 4**: 2 days (Integration testing & performance)
- **Phase 5**: 2 days (Documentation)

**Total**: 12 days (~2.5 weeks with buffer)

## Risk Mitigation

### Risk: Django ORM Edge Cases
**Mitigation**: 
- Test with multiple Django versions (4.2, 5.0, 5.1)
- Always include PK and FK fields
- Provide fallback to non-optimized queries on errors

### Risk: Breaking Existing Functionality
**Mitigation**:
- Only apply optimization when `$select` is provided
- Run full test suite after each phase
- Maintain backward compatibility

### Risk: Performance Regression
**Mitigation**:
- Benchmark before and after
- Only optimize when beneficial
- Make optimization opt-in if needed

## Success Criteria

### Must Have
- ✅ Queries fetch only requested fields when `$select` is used
- ✅ All existing tests pass
- ✅ No breaking changes to API
- ✅ Works with both select_related and prefetch_related

### Should Have
- ✅ 20-40% performance improvement verified
- ✅ Query logging shows optimized SQL
- ✅ Works with nested expansions
- ✅ Comprehensive test coverage

### Nice to Have
- ✅ Performance metrics documented
- ✅ Query optimization examples in docs
- ✅ Benchmark comparison charts

## Notes

- All code must follow project style guidelines (black, isort, flake8)
- Type hints required for all new methods
- Comprehensive docstrings required
- Test coverage must remain ≥90%

---

**Created by**: Alexandre Busquets  
**Last Updated**: 2025-10-30  
**Ready for Implementation**: Yes