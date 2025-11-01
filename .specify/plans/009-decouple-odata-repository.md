# PLAN-009: Decouple OData Query Processing from Serialization (REVISED)

**Related Spec**: SPEC-009  
**Status**: In Progress  
**Created**: 2025-11-01  
**Revised**: 2025-11-01  
**Start Date**: TBD  
**Target Completion**: TBD

## Revision Notice

**IMPORTANT**: This plan has been revised after discovering that:
1. The project already uses [`odata-query`](https://odata-query.readthedocs.io/) library for parsing (see [`utils.py:10`](../django_odata/utils.py#L10))
2. We should leverage this library instead of duplicating its functionality
3. The real problem is extracting QuerySet optimization logic from [`ODataMixin`](../django_odata/mixins.py) into reusable functions

## Overview

This plan creates a decoupled OData query layer by:
1. **Leveraging `odata-query`** for all query parsing (already a dependency)
2. **Extracting optimization logic** from `ODataMixin` into standalone, reusable functions
3. **Creating simple wrappers** that can be used in repositories, use cases, and management commands
4. **Maintaining 100% backward compatibility** with existing `ODataModelViewSet` and `ODataMixin`

## Architecture Decision

**Chosen Pattern:** Thin Wrapper + Extracted Optimization Functions

**Rationale:**
1. `odata-query` already handles parsing - don't duplicate it
2. `ODataMixin` already has optimization logic - extract it
3. Simple wrapper function provides immediate value
4. Repository layer enables clean architecture for new features
5. Minimal code duplication and maintenance burden

## Key Functions to Create

### 1. Core Wrapper Function
```python
# django_odata/core.py

from odata_query.django import apply_odata_query
from django.db.models import QuerySet

def apply_odata_to_queryset(
    queryset: QuerySet,
    query_string: str = None,
    query_params: dict = None
) -> QuerySet:
    """
    Apply OData query to a Django QuerySet with automatic optimizations.
    
    This is the main entry point for using OData queries anywhere in your code.
    
    Args:
        queryset: Base Django QuerySet to query
        query_string: Raw query string (e.g., "$filter=status eq 'published'&$expand=author")
        query_params: Parsed query parameters dict (alternative to query_string)
    
    Returns:
        Optimized QuerySet with all OData parameters applied
        
    Examples:
        >>> # In a repository
        >>> posts = apply_odata_to_queryset(
        ...     BlogPost.objects.filter(is_active=True),
        ...     "$filter=status eq 'published'&$expand=author($select=name)"
        ... )
        
        >>> # In a management command
        >>> posts = apply_odata_to_queryset(
        ...     BlogPost.objects.all(),
        ...     "$filter=created_at ge 2024-01-01&$orderby=created_at desc&$top=100"
        ... )
    """
```

### 2. Optimization Functions (Extracted from ODataMixin)

```python
# django_odata/optimization.py

def optimize_queryset_for_select(
    queryset: QuerySet,
    select_fields: list,
    expand_fields: dict = None
) -> QuerySet:
    """
    Apply .only() optimization for field selection.
    
    Extracted from ODataMixin._apply_field_selection_optimization()
    """

def optimize_queryset_for_expand(
    queryset: QuerySet,
    expand_fields: dict
) -> QuerySet:
    """
    Apply select_related/prefetch_related for expansions.
    
    Extracted from ODataMixin._optimize_queryset_for_expansions()
    """

def categorize_relations(
    model_class,
    field_names: list
) -> tuple[list, list]:
    """
    Categorize fields into select_related vs prefetch_related.
    
    Extracted from ODataMixin._categorize_expand_fields()
    """
```

## Implementation Phases

### Phase 1: Extract Optimization Logic (Week 1)

#### 1.1 Create optimization.py Module
**File**: `django_odata/optimization.py`
**Task**: Extract optimization functions from `ODataMixin`

**Steps**:
1. Copy `_apply_field_selection_optimization()` → `optimize_queryset_for_select()`
2. Copy `_optimize_queryset_for_expansions()` → `optimize_queryset_for_expand()`
3. Copy `_categorize_expand_fields()` → `categorize_relations()`
4. Copy `_build_only_fields_list()` → `build_only_fields_list()`
5. Copy `_apply_related_field_selection()` → helper function
6. Copy `_apply_prefetch_field_selection()` → helper function

**Testing**:
```python
def test_optimize_queryset_for_select():
    """Test field selection optimization"""
    qs = BlogPost.objects.all()
    optimized = optimize_queryset_for_select(qs, ['title', 'content'])
    # Verify .only() was applied correctly

def test_optimize_queryset_for_expand():
    """Test expansion optimization"""
    qs = BlogPost.objects.all()
    optimized = optimize_queryset_for_expand(qs, {'author': {}})
    # Verify select_related was applied

def test_categorize_relations():
    """Test relation categorization"""
    select, prefetch = categorize_relations(BlogPost, ['author', 'categories'])
    assert 'author' in select  # ForeignKey
    assert 'categories' in prefetch  # ManyToMany
```

**Acceptance**: All optimization functions work independently

---

#### 1.2 Create core.py Wrapper
**File**: `django_odata/core.py`
**Task**: Create main `apply_odata_to_queryset()` function

```python
from odata_query.django import apply_odata_query
from .optimization import optimize_queryset_for_select, optimize_queryset_for_expand
from .utils import parse_odata_query, parse_expand_fields_v2

def apply_odata_to_queryset(
    queryset: QuerySet,
    query_string: str = None,
    query_params: dict = None
) -> QuerySet:
    """Main OData wrapper - combines odata-query + optimizations"""
    
    # Parse query string into dict
    if query_string:
        query_params = parse_odata_query(query_string)
    
    if not query_params:
        return queryset
    
    # Apply optimizations BEFORE filtering
    if '$select' in query_params:
        expand_fields = parse_expand_fields_v2(query_params.get('$expand', ''))
        queryset = optimize_queryset_for_select(
            queryset,
            query_params['$select'].split(','),
            expand_fields
        )
    
    if '$expand' in query_params:
        expand_fields = parse_expand_fields_v2(query_params['$expand'])
        queryset = optimize_queryset_for_expand(queryset, expand_fields)
    
    # Use odata-query for filtering
    if '$filter' in query_params:
        queryset = apply_odata_query(queryset, query_params['$filter'])
    
    # Apply ordering
    if '$orderby' in query_params:
        # Use existing _apply_orderby from utils
        from .utils import _apply_orderby
        queryset = _apply_orderby(queryset, query_params)
    
    # Apply pagination
    if '$skip' in query_params:
        from .utils import _apply_skip
        queryset = _apply_skip(queryset, query_params)
    
    if '$top' in query_params:
        from .utils import _apply_top
        queryset = _apply_top(queryset, query_params)
    
    return queryset
```

**Testing**:
```python
def test_apply_odata_to_queryset_filter():
    """Test basic filtering"""
    qs = BlogPost.objects.all()
    result = apply_odata_to_queryset(qs, "$filter=status eq 'published'")
    # Verify filtering works

def test_apply_odata_to_queryset_expand():
    """Test expansion with optimization"""
    qs = BlogPost.objects.all()
    result = apply_odata_to_queryset(qs, "$expand=author&$select=title,author")
    # Verify select_related was applied
    # Verify .only() was applied

def test_apply_odata_to_queryset_complete():
    """Test all parameters together"""
    qs = BlogPost.objects.all()
    result = apply_odata_to_queryset(
        qs,
        "$filter=status eq 'published'&$expand=author&$select=title&$orderby=created_at desc&$top=10"
    )
    # Verify all optimizations applied
```

**Acceptance**: Wrapper function works for all OData parameters

---

#### 1.3 Create ODataRepository Class
**File**: `django_odata/repository.py` (rewrite existing)
**Task**: Simple repository using `apply_odata_to_queryset()`

```python
from django.db.models import QuerySet
from typing import Optional, List
from .core import apply_odata_to_queryset

class ODataRepository:
    """
    Repository for executing OData queries on Django models.
    
    Provides a clean interface for using OData queries in repositories,
    use cases, and any code that needs QuerySets.
    """
    
    def __init__(self, model_class=None):
        """Initialize repository for a model."""
        self.model = model_class
    
    def query(
        self,
        query_string: str = None,
        model_class=None,
        base_queryset: QuerySet = None
    ) -> QuerySet:
        """
        Execute OData query and return QuerySet.
        
        Examples:
            >>> repo = ODataRepository(BlogPost)
            >>> posts = repo.query("$filter=status eq 'published'&$expand=author")
            
            >>> # With business logic
            >>> base_qs = BlogPost.objects.filter(featured=True)
            >>> posts = repo.query("$filter=rating gt 4.0", base_queryset=base_qs)
        """
        model = model_class or self.model
        if not model:
            raise ValueError("model_class required")
        
        # Get base queryset
        if base_queryset is None:
            base_queryset = model.objects.all()
        
        # Apply OData query
        return apply_odata_to_queryset(base_queryset, query_string)
    
    def count(self, query_string: str, model_class=None) -> int:
        """Get count of matching records."""
        return self.query(query_string, model_class).count()
    
    def exists(self, query_string: str, model_class=None) -> bool:
        """Check if any records match."""
        return self.query(query_string, model_class).exists()
    
    def first(self, query_string: str, model_class=None):
        """Get first matching record."""
        return self.query(query_string, model_class).first()
    
    def get_list(
        self,
        query_string: str = None,
        model_class=None,
        base_queryset: QuerySet = None
    ) -> List:
        """Get evaluated list of objects."""
        return list(self.query(query_string, model_class, base_queryset))
```

**Acceptance**: Repository class works as expected

---

### Phase 2: Backward Compatible Integration (Week 2)

#### 2.1 Refactor ODataMixin to Use Extracted Functions
**File**: `django_odata/mixins.py`
**Task**: Replace inline logic with calls to optimization functions

**Before**:
```python
def get_queryset(self):
    queryset = super().get_queryset()
    # 100+ lines of complex logic here
    queryset = self._apply_field_selection_optimization(queryset)
    queryset = self._optimize_queryset_for_expansions(queryset)
    return self.apply_odata_query(queryset)
```

**After**:
```python
from .core import apply_odata_to_queryset

def get_queryset(self):
    queryset = super().get_queryset()
    
    # Use extracted wrapper function
    query_string = self.request.META.get('QUERY_STRING', '')
    return apply_odata_to_queryset(queryset, query_string)
```

**Testing**: Run full existing test suite - must pass 100%

**Acceptance**: All existing tests pass without modifications

---

#### 2.2 Delete Duplicate Code
**Files to modify**:
- `django_odata/query/parser.py` - DELETE (duplicates odata-query)
- `django_odata/query/builder.py` - DELETE (not needed)
- `django_odata/query/optimizer.py` - DELETE (extracted to optimization.py)
- `django_odata/query/__init__.py` - DELETE directory

**Acceptance**: Duplicate code removed

---

### Phase 3: Examples and Documentation (Week 3)

#### 3.1 Create Blog Repository Example
**File**: `example/blog/repositories.py`
**Task**: Domain repository demonstrating clean architecture

```python
from django_odata.repository import ODataRepository
from .models import BlogPost

class BlogPostRepository:
    """Domain repository for BlogPost."""
    
    def __init__(self):
        self.odata = ODataRepository(BlogPost)
    
    def find_published(self, query_string: str = None):
        """Business method: find published posts."""
        base_qs = BlogPost.objects.filter(status='published')
        return self.odata.query(query_string, base_queryset=base_qs)
    
    def find_by_author(self, author_id: int, query_string: str = None):
        """Find posts by author with OData filtering."""
        base_qs = BlogPost.objects.filter(author_id=author_id)
        return self.odata.query(query_string, base_queryset=base_qs)
```

---

#### 3.2 Create Use Case Example
**File**: `example/blog/use_cases.py`

```python
from dataclasses import dataclass
from typing import List

@dataclass
class GetBlogPostsRequest:
    """Use case request."""
    odata_query: str = None
    include_drafts: bool = False

class GetBlogPostsUseCase:
    """Get blog posts with business logic."""
    
    def __init__(self, repository: BlogPostRepository):
        self.repository = repository
    
    def execute(self, request: GetBlogPostsRequest) -> List[BlogPost]:
        """Execute use case."""
        if request.include_drafts:
            queryset = BlogPost.objects.all()
        else:
            queryset = BlogPost.objects.filter(status='published')
        
        # Apply OData query
        if request.odata_query:
            queryset = self.repository.odata.query(
                request.odata_query,
                base_queryset=queryset
            )
        
        return list(queryset)
```

---

#### 3.3 Update Documentation
**File**: `docs/decoupling-guide.md`
**Content**:
- Explain the new `apply_odata_to_queryset()` function
- Show repository pattern examples
- Provide migration guide from old to new
- Document integration with `odata-query` library

---

### Phase 4: Testing and Validation (Week 4)

#### 4.1 Integration Tests
**File**: `tests/test_decoupling_integration.py`

```python
def test_apply_odata_matches_old_behavior():
    """New function should match ODataMixin behavior"""
    # Compare results from both approaches

def test_repository_without_drf():
    """Repository should work without DRF imports"""
    # Verify no DRF dependencies needed

def test_backward_compatibility():
    """ODataModelViewSet should still work"""
    # All existing views should work unchanged
```

---

#### 4.2 Performance Benchmarks
**File**: `tests/performance/test_optimization_performance.py`

```python
def test_query_count_optimization():
    """Verify optimizations reduce query count"""
    # Measure queries before/after optimization

def test_performance_vs_old_implementation():
    """Compare performance old vs new"""
    # Should be equal or better
```

---

## Task Dependencies

```
Phase 1: Extract & Create
  1.1 (optimization.py) → 1.2 (core.py) → 1.3 (repository.py)

Phase 2: Integration
  2.1 (Refactor ODataMixin) → 2.2 (Delete duplicates)

Phase 3: Examples
  3.1 (Repository) → 3.2 (Use Case) → 3.3 (Documentation)

Phase 4: Testing
  4.1 (Integration tests) → 4.2 (Performance)
```

## Timeline Estimate

- Phase 1 (Extract & Create): 1 week
- Phase 2 (Integration): 1 week
- Phase 3 (Examples): 1 week
- Phase 4 (Testing): 1 week

**Total Development Time**: ~4 weeks (reduced from original 5 weeks)

## Success Metrics

### Must Have
- ✅ Can execute OData queries without DRF/serializers
- ✅ 100% backward compatibility with existing code
- ✅ All existing tests pass without modifications
- ✅ 90%+ test coverage for new optimization functions

### Should Have
- ✅ Simple `apply_odata_to_queryset()` function works in any context
- ✅ Documentation complete with examples
- ✅ Repository pattern example working

### Nice to Have
- ✅ Performance equal or better than before
- ✅ Reduced code complexity
- ✅ Example use case demonstrating clean architecture

## Key Differences from Original Plan

| Original | Revised | Reason |
|----------|---------|--------|
| Create ODataQueryParser | Use existing `odata-query` | Don't duplicate library functionality |
| Create ODataQueryBuilder | Simple wrapper function | Simpler, more direct |
| 5 new classes | 1 wrapper function + extracted helpers | Reduced complexity |
| 5 weeks | 4 weeks | Less code to write |

## Next Steps

1. Review and approve this REVISED plan
2. Delete duplicate code already created (`django_odata/query/`)
3. Begin Phase 1.1 - Extract optimization functions
4. Create unit tests for extracted functions