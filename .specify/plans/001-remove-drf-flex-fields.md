# PLAN-001: Remove drf-flex-fields Dependency

**Related Spec**: SPEC-001  
**Status**: Ready for Implementation  
**Created**: 2025-10-29  
**Start Date**: TBD  
**Target Completion**: TBD

## Overview

This plan breaks down the implementation of SPEC-001 into concrete, actionable tasks. The goal is to remove the `drf-flex-fields` dependency while maintaining full API compatibility.

## Implementation Phases

### Phase 1: Setup and Preparation (1 day)

#### 1.1 Create Performance Baseline
**File**: `tests/performance/test_baseline.py`
**Task**: Create performance tests to measure current implementation
```python
import pytest
from django.test import Client
from time import time

@pytest.mark.benchmark
def test_select_performance(db, client):
    """Measure $select query performance"""
    # Create test data
    # Measure time for queries with $select
    pass

@pytest.mark.benchmark  
def test_expand_performance(db, client):
    """Measure $expand query performance"""
    # Create test data
    # Measure time for queries with $expand
    pass
```
**Acceptance**: Baseline numbers documented in `docs/performance-baseline.md`

#### 1.2 Audit Current FlexFields Usage
**Files**: All files in `django_odata/`
**Task**: Document exactly what we use from drf-flex-fields
- List all imported classes/functions
- Document all Meta.expandable_fields usage
- Identify any undocumented features being used
**Acceptance**: Document created at `docs/flexfields-audit.md`

#### 1.3 Create Test Coverage Report
**Command**: `pytest --cov=django_odata --cov-report=html`
**Task**: Ensure we have comprehensive test coverage before changes
**Acceptance**: Coverage > 90% for all modules being changed

---

### Phase 2: Create Native Field Selection (3 days)

#### 2.1 Create native_fields.py Module
**File**: `django_odata/native_fields.py`
**Task**: Create new module for native implementations
```python
"""
Native field selection and expansion for OData serializers.
Replaces drf-flex-fields dependency.
"""

class NativeFieldSelectionMixin:
    """Handles $select parameter for dynamic field selection."""
    pass

class NativeFieldExpansionMixin:
    """Handles $expand parameter for related field expansion."""
    pass

# Helper functions
def parse_select_fields(select_string: str) -> dict:
    """Parse $select parameter into field structure."""
    pass

def parse_expand_fields(expand_string: str) -> dict:
    """Parse $expand parameter into expansion structure."""
    pass
```
**Acceptance**: Module created with basic structure

#### 2.2 Implement Field Selection Parser
**Function**: `parse_select_fields()`
**Task**: Parse OData $select parameter
```python
def parse_select_fields(select_string: str) -> dict:
    """
    Parse: "id,title,author.name" 
    Into: {
        'top_level': ['id', 'title', 'author'],
        'nested': {
            'author': ['name']
        }
    }
    """
    pass
```
**Test cases**:
- Empty string → show all
- Single field → {'top_level': ['field'], 'nested': {}}
- Multiple fields → {'top_level': ['f1', 'f2'], 'nested': {}}
- Nested fields → {'top_level': ['parent'], 'nested': {'parent': ['child']}}

**Acceptance**: All parser tests pass

#### 2.3 Implement NativeFieldSelectionMixin
**Class**: `NativeFieldSelectionMixin`
**Task**: Filter serializer fields based on $select
```python
class NativeFieldSelectionMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_selection()
    
    def _apply_field_selection(self):
        """Apply $select filtering to serializer fields."""
        odata_params = self.context.get('odata_params', {})
        select_param = odata_params.get('$select')
        
        if not select_param:
            return  # Show all fields
        
        parsed = parse_select_fields(select_param)
        allowed_fields = set(parsed['top_level'])
        
        # Remove unselected fields
        existing = list(self.fields.keys())
        for field_name in existing:
            if field_name not in allowed_fields:
                self.fields.pop(field_name)
        
        # Store nested selections for child serializers
        if parsed['nested']:
            self.context['_nested_selections'] = parsed['nested']
```

**Test cases**:
```python
def test_select_single_field():
    """$select=id should only show id field"""
    pass

def test_select_multiple_fields():
    """$select=id,title should show id and title"""
    pass

def test_select_empty():
    """Empty $select should show all fields"""
    pass

def test_select_invalid_field():
    """$select=nonexistent should ignore invalid field"""
    pass
```

**Acceptance**: All field selection tests pass

---

### Phase 3: Create Native Field Expansion (4 days)

#### 3.1 Implement Expansion Parser
**Function**: `parse_expand_fields()`
**Task**: Parse OData $expand with nested $select
```python
def parse_expand_fields(expand_string: str) -> dict:
    """
    Parse: "author,posts($select=id,title)"
    Into: {
        'author': None,  # No nested select
        'posts': 'id,title'  # Nested select
    }
    """
    pass
```

**Test cases**:
- Simple: "author" → {'author': None}
- Multiple: "author,posts" → {'author': None, 'posts': None}
- Nested: "posts($select=id,title)" → {'posts': 'id,title'}
- Complex: "author,posts($select=id,title)" → both

**Acceptance**: All parser tests pass

#### 3.2 Implement NativeFieldExpansionMixin
**Class**: `NativeFieldExpansionMixin`
**Task**: Add related serializers based on $expand
```python
class NativeFieldExpansionMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_expansion()
    
    def _apply_field_expansion(self):
        """Add expanded fields to serializer."""
        odata_params = self.context.get('odata_params', {})
        expand_param = odata_params.get('$expand')
        
        if not expand_param:
            return
        
        expandable = getattr(self.Meta, 'expandable_fields', {})
        if not expandable:
            return
        
        parsed = parse_expand_fields(expand_param)
        
        for field_name, nested_select in parsed.items():
            if field_name not in expandable:
                continue  # Skip non-expandable fields
            
            # Get serializer config
            serializer_config = expandable[field_name]
            serializer_class, options = self._parse_serializer_config(serializer_config)
            
            # Create nested context
            nested_context = self.context.copy()
            if nested_select:
                nested_context['odata_params'] = {
                    **nested_context.get('odata_params', {}),
                    '$select': nested_select
                }
            
            # Add to fields
            self.fields[field_name] = serializer_class(
                context=nested_context,
                **options
            )
    
    def _parse_serializer_config(self, config):
        """Parse expandable_fields configuration."""
        if isinstance(config, tuple):
            serializer_class = config[0]
            options = config[1] if len(config) > 1 else {}
            return serializer_class, options
        return config, {}
```

**Test cases**:
```python
def test_expand_single_relation():
    """$expand=author should include author data"""
    pass

def test_expand_multiple_relations():
    """$expand=author,categories should expand both"""
    pass

def test_expand_with_nested_select():
    """$expand=author($select=name) should only show name"""
    pass

def test_expand_many_relation():
    """$expand=posts should work with many=True"""
    pass

def test_expand_non_expandable():
    """$expand=invalid should ignore gracefully"""
    pass
```

**Acceptance**: All expansion tests pass

#### 3.3 Handle Circular References
**Task**: Prevent infinite recursion in nested expansions
```python
class NativeFieldExpansionMixin:
    MAX_EXPANSION_DEPTH = 3
    
    def _apply_field_expansion(self):
        # Check depth
        depth = self.context.get('_expansion_depth', 0)
        if depth >= self.MAX_EXPANSION_DEPTH:
            return  # Stop expanding
        
        # Increment depth for nested serializers
        self.context['_expansion_depth'] = depth + 1
        
        # ... rest of expansion logic
```

**Test case**:
```python
def test_circular_reference_protection():
    """Nested $expand should stop at max depth"""
    # Post -> Author -> Posts -> Author (should stop)
    pass
```

**Acceptance**: Circular reference test passes

---

### Phase 4: Update OData Serializers (2 days)

#### 4.1 Update ODataModelSerializer
**File**: `django_odata/serializers.py`
**Task**: Replace FlexFieldsModelSerializer with native mixins

**Before**:
```python
from rest_flex_fields import FlexFieldsModelSerializer

class ODataModelSerializer(ODataSerializerMixin, FlexFieldsModelSerializer):
    pass
```

**After**:
```python
from rest_framework import serializers
from .native_fields import NativeFieldSelectionMixin, NativeFieldExpansionMixin

class ODataModelSerializer(
    ODataSerializerMixin,
    NativeFieldSelectionMixin,
    NativeFieldExpansionMixin,
    serializers.ModelSerializer
):
    pass
```

**Acceptance**: ODataModelSerializer works with new mixins

#### 4.2 Update ODataSerializer
**File**: `django_odata/serializers.py`
**Task**: Replace FlexFieldsSerializerMixin

**Before**:
```python
from rest_flex_fields.serializers import FlexFieldsSerializerMixin

class ODataSerializer(
    ODataSerializerMixin, 
    FlexFieldsSerializerMixin, 
    serializers.Serializer
):
    pass
```

**After**:
```python
class ODataSerializer(
    ODataSerializerMixin,
    NativeFieldSelectionMixin,
    NativeFieldExpansionMixin,
    serializers.Serializer
):
    pass
```

**Acceptance**: ODataSerializer works with new mixins

#### 4.3 Clean Up ODataSerializerMixin
**File**: `django_odata/mixins.py`
**Task**: Remove FlexFields-specific code from ODataSerializerMixin
- Remove `_process_odata_params_before_init`
- Remove `_update_request_params` (setting 'fields' and 'expand' query params)
- Simplify `__init__` method

**Acceptance**: ODataSerializerMixin simplified and all tests pass

---

### Phase 5: Testing and Validation (3 days)

#### 5.1 Run Full Test Suite
**Command**: `pytest tests/ -v --cov=django_odata`
**Task**: Ensure all existing tests pass
**Success Criteria**:
- 100% of existing tests pass
- Coverage maintained > 90%
- No new warnings or errors

#### 5.2 Integration Testing
**File**: `tests/integration/test_native_fields.py`
**Task**: Create comprehensive integration tests
```python
def test_complete_odata_query():
    """Test: GET /posts?$select=id,title&$expand=author($select=name,email)"""
    response = client.get('/posts', {
        '$select': 'id,title',
        '$expand': 'author($select=name,email)'
    })
    
    expected = {
        'value': [
            {
                'id': 1,
                'title': 'Post 1',
                'author': {
                    'name': 'John',
                    'email': 'john@example.com'
                }
            }
        ]
    }
    assert response.json() == expected
```

**Test scenarios**:
- Simple $select
- Simple $expand
- Combined $select + $expand
- Nested $select in $expand
- Multiple expansions
- Edge cases (empty, invalid fields, etc.)

**Acceptance**: All integration tests pass

#### 5.3 Performance Testing
**File**: `tests/performance/test_native_performance.py`
**Task**: Compare performance before/after
```python
@pytest.mark.benchmark
def test_native_select_performance(benchmark):
    """Measure new implementation performance"""
    result = benchmark(lambda: client.get('/posts?$select=id,title'))
    assert result.status_code == 200

@pytest.mark.benchmark
def test_native_expand_performance(benchmark):
    """Measure expansion performance"""
    result = benchmark(lambda: client.get('/posts?$expand=author'))
    assert result.status_code == 200
```

**Success Criteria**:
- No performance regression
- Ideally 10-20% improvement
- Document results in `docs/performance-comparison.md`

#### 5.4 Example Project Testing
**Location**: `example/`
**Task**: Test example project works without changes
```bash
cd example
python manage.py migrate
python manage.py runserver
# Test all example endpoints
```

**Acceptance**: Example project works without modifications

---

### Phase 6: Documentation and Cleanup (2 days)

#### 6.1 Update README
**File**: `README.md`
**Changes**:
- Remove mention of drf-flex-fields
- Update installation instructions
- Update feature list
- Add "What's New in v2.0" section

#### 6.2 Update API Documentation
**File**: `docs/api.md`
**Changes**:
- Document native implementation
- Remove FlexFields references
- Update code examples
- Add migration guide

#### 6.3 Create Migration Guide
**File**: `docs/migration-v2.md`
**Content**:
```markdown
# Migrating to v2.0

## Summary
v2.0 removes the drf-flex-fields dependency with no API changes required.

## For Most Users
Simply upgrade:
```bash
pip install --upgrade django-odata
```

Your existing code will work without changes!

## Breaking Changes
None for standard usage.

## Internal Changes
- Removed drf-flex-fields dependency
- Improved performance by 15%
- Simplified codebase

## If You Encounter Issues
...
```

#### 6.4 Update Changelog
**File**: `CHANGELOG.md`
**Add**:
```markdown
## [2.0.0] - 2025-XX-XX

### Changed
- **BREAKING**: Removed drf-flex-fields dependency
- Implemented native field selection and expansion
- Improved query performance by ~15%

### Migration
No code changes required for standard usage.
See docs/migration-v2.md for details.
```

#### 6.5 Remove drf-flex-fields
**Files**: `requirements.txt`, `setup.py`, `pyproject.toml`
**Task**: Remove all references to drf-flex-fields
**Acceptance**: `pip install .` works without drf-flex-fields

---

### Phase 7: Release (1 day)

#### 7.1 Create Beta Release
**Tag**: `v2.0.0-beta.1`
**Task**: 
- Create release branch: `release/v2.0.0`
- Tag beta release
- Push to PyPI test server
```bash
git checkout -b release/v2.0.0
git tag v2.0.0-beta.1
python -m build
twine upload --repository testpypi dist/*
```

#### 7.2 Beta Testing Period
**Duration**: 1-2 weeks
**Tasks**:
- Announce beta in README
- Ask community for testing
- Monitor issues
- Fix any reported bugs

#### 7.3 Final Release
**Tag**: `v2.0.0`
**Tasks**:
- Merge release branch to main
- Create GitHub release with changelog
- Publish to PyPI
```bash
git checkout main
git merge release/v2.0.0
git tag v2.0.0
python -m build
twine upload dist/*
```

---

## Task Dependencies

```
Setup → Field Selection → Field Expansion → Update Serializers → Testing → Docs → Release
  1.1      2.1              3.1              4.1              5.1      6.1     7.1
  1.2      2.2              3.2              4.2              5.2      6.2     7.2
  1.3      2.3              3.3              4.3              5.3      6.3     7.3
                                                              5.4      6.4
                                                                       6.5
```

## Timeline Estimate

- Phase 1 (Setup): 1 day
- Phase 2 (Field Selection): 3 days
- Phase 3 (Field Expansion): 4 days
- Phase 4 (Update Serializers): 2 days
- Phase 5 (Testing): 3 days
- Phase 6 (Documentation): 2 days
- Phase 7 (Release): 1 day + 1-2 weeks beta

**Total Development Time**: ~16 days (3 weeks)
**Total Time to Release**: ~5 weeks (including beta period)

## Risk Mitigation

### If Tests Fail
1. Create comparison tests (old vs new)
2. Use git bisect to find regression
3. Fix or revert specific change
4. Add test for regression

### If Performance Regresses
1. Profile both implementations
2. Identify bottleneck
3. Optimize critical path
4. Consider hybrid approach if needed

### If API Breaks
1. Add compatibility layer
2. Extend beta period
3. Document breaking change clearly
4. Provide migration path

## Success Metrics

### Must Have
- ✅ 100% test pass rate
- ✅ 0 new dependencies
- ✅ API compatibility
- ✅ Documentation complete

### Should Have
- ✅ 90%+ code coverage
- ✅ 10%+ performance improvement
- ✅ Positive beta feedback

### Nice to Have
- ✅ 15%+ performance improvement
- ✅ Cleaner codebase
- ✅ Better error messages

## Notes for Implementation

- Keep commits small and focused
- Write tests before implementation (TDD where possible)
- Document design decisions in code comments
- Regular progress updates in GitHub issues
- Code review after each major phase

## Next Steps

1. Review and approve this plan
2. Create GitHub project board with tasks
3. Estimate effort for each task
4. Assign start date
5. Begin Phase 1: Setup
