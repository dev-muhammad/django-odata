# SPEC-009: Decouple OData Query Processing from Serialization

**Status**: In Progress
**Priority**: High
**Complexity**: Medium
**Created**: 2025-11-01
**Updated**: 2025-11-01
**Owner**: Alexandre Busquets

## Context

The `django-odata` library currently has OData query processing logic tightly coupled with Django REST Framework serializers in [`ODataMixin`](../django_odata/mixins.py) and [`ODataModelSerializer`](../django_odata/serializers.py). This coupling:
- Prevents using OData queries outside of DRF views (e.g., in repositories, management commands, background tasks)
- Makes testing difficult (requires full DRF stack setup)
- Violates clean architecture principles (infrastructure mixed with business logic)
- Limits code reusability across different layers
- Makes it harder to maintain and extend the codebase

**Key Discovery**: The library already uses [`odata-query`](https://odata-query.readthedocs.io/) for parsing `$filter` expressions (see [`utils.py:10`](../django_odata/utils.py#L10)). We should leverage this library fully instead of duplicating parsing logic.

The library should provide a decoupled OData query layer that:
- Can be used independently of DRF serializers
- Leverages existing `odata-query` library for all parsing
- Enables clean architecture patterns (Repository → Use Case → Controller)
- Improves testability through isolated components
- Maintains backward compatibility with existing API
- Follows Django best practices for QuerySet manipulation

## Objectives

### Primary Goal
Create a decoupled OData query processing layer that can be used in any part of the application (repositories, use cases, views, commands, tasks) without requiring DRF components.

### Success Metrics
- Can execute OData queries without DRF/serializers
- 100% backward compatibility maintained
- Zero failing tests after migration
- 50%+ reduction in database queries for complex scenarios
- 90%+ test coverage for new components
- Code can be tested in isolation without DRF stack

### Non-Goals (Out of Scope)
- Adding new OData features
- Changing existing OData query syntax
- Modifying the external API for current users
- Performance optimizations beyond decoupling benefits

## User Scenarios & Testing

### User Story 1 - Repository Layer Query Execution (Priority: P1)

As a developer following clean architecture, I want to execute OData queries in my repository layer so that I can separate infrastructure concerns from business logic.

**Why this priority**: This is the core value proposition - enabling clean architecture patterns.

**Independent Test**: Can create a repository class that uses ODataRepository to query models and returns QuerySets, completely independent of views or serializers.

**Acceptance Scenarios**:

1. **Given** a BlogPost model and OData query string, **When** I create an ODataRepository and call query(), **Then** I receive an optimized Django QuerySet
2. **Given** an OData query with $filter and $expand, **When** executed via repository, **Then** the QuerySet uses select_related/prefetch_related appropriately
3. **Given** a repository method combining business rules with OData, **When** using a base queryset with OData query, **Then** both filters are applied correctly

---

### User Story 2 - Use OData in Management Commands (Priority: P2)

As a developer creating data export commands, I want to use OData queries to filter and shape data so that I can leverage the same powerful query syntax available in the API.

**Why this priority**: Common use case that demonstrates the value of decoupling from web layer.

**Independent Test**: Can create a Django management command that uses ODataRepository to export filtered data without any DRF dependencies.

**Acceptance Scenarios**:

1. **Given** a management command needing to export posts, **When** using ODataRepository with query string, **Then** data is filtered correctly
2. **Given** complex filter requirements in a command, **When** building query with ODataQueryBuilder, **Then** QuerySet is constructed with proper optimizations

---

### User Story 3 - Testing Without DRF Stack (Priority: P2)

As a developer writing tests, I want to test OData query logic in isolation so that tests are faster and more focused.

**Why this priority**: Improves developer experience and test quality significantly.

**Independent Test**: Can write unit tests for OData query logic using only Django TestCase without APITestCase or request factories.

**Acceptance Scenarios**:

1. **Given** a simple OData filter query, **When** testing with ODataRepository, **Then** test runs without DRF request factory or views
2. **Given** complex expansion scenario, **When** testing ODataQueryBuilder, **Then** can verify QuerySet optimization without serialization

---

### User Story 4 - Background Task Processing (Priority: P3)

As a developer creating Celery tasks, I want to use OData queries to select data for processing so that I can leverage consistent query syntax across the application.

**Why this priority**: Extends the value but less critical than core repository usage.

**Independent Test**: Can create a Celery task that uses ODataRepository to process batches of data.

**Acceptance Scenarios**:

1. **Given** a periodic task needing to process recent items, **When** using OData query with date filters, **Then** correct items are selected for processing

---

### User Story 5 - Backward Compatible Views (Priority: P1)

As an existing library user, I want my current ODataModelViewSet code to continue working unchanged so that I can upgrade without breaking changes.

**Why this priority**: Critical for library adoption - breaking changes would prevent upgrades.

**Independent Test**: Existing test suite passes 100% without code changes.

**Acceptance Scenarios**:

1. **Given** existing ODataModelViewSet implementation, **When** upgrading to new version, **Then** all API endpoints work identically
2. **Given** existing serializer with expandable_fields, **When** using new version, **Then** expansion works as before

---

### Edge Cases

- What happens when circular model relationships exist in $expand?
- How does the system handle invalid field names in $select?
- What happens with deeply nested $expand (e.g., 5+ levels)?
- How are empty query strings handled?
- What happens with $expand on non-existent relations?
- How are Many-to-Many relationships optimized differently from ForeignKey?

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide ODataRepository class that accepts model class and query string
- **FR-002**: ODataRepository MUST return Django QuerySet objects (not serialized data)
- **FR-003**: System MUST parse OData query strings into structured parameters
- **FR-004**: System MUST optimize QuerySets using select_related for forward relations
- **FR-005**: System MUST optimize QuerySets using prefetch_related for reverse/M2M relations
- **FR-006**: System MUST apply field selection using Django's .only() method
- **FR-007**: System MUST support all existing OData parameters ($filter, $expand, $select, $orderby, $top, $skip)
- **FR-008**: ODataQueryBuilder MUST provide fluent API for programmatic query construction
- **FR-009**: System MUST prevent infinite recursion in circular model relationships
- **FR-010**: Existing ODataModelViewSet MUST work without code changes (backward compatibility)
- **FR-011**: System MUST maintain existing serializer expandable_fields configuration

### Key Entities

**New Architecture (Leveraging `odata-query`):**

- **`apply_odata_to_queryset()`**: Main function - wraps `odata-query` + optimization logic
- **`optimize_queryset_for_odata()`**: Extracts optimization logic from `ODataMixin`
- **`ODataRepository`**: Repository pattern interface using `apply_odata_to_queryset()` internally
- **Existing `odata-query` library**: Handles all query parsing ($filter, $orderby, $top, $skip, etc.)

**Deprecated/Removed:**
- ~~**ODataQueryParser**~~: Not needed - `odata-query` handles parsing
- ~~**ODataQueryBuilder**~~: Simplified to direct `odata-query` usage
- ~~**ODataQueryParams**~~: Not needed - use `odata-query` structures directly

## Success Criteria

### Measurable Outcomes

- **SC-001**: Developers can execute OData queries in repositories without importing any DRF classes
- **SC-002**: Complex queries with $expand show 50-80% reduction in database queries compared to current N+1 patterns
- **SC-003**: Tests for OData logic run without APITestCase or request factories
- **SC-004**: 100% of existing tests pass without modifications
- **SC-005**: New components achieve 90%+ code coverage
- **SC-006**: Performance benchmarks show no regression (or improvement) compared to current implementation

---

**Approval Required From**: @alexandre-fundcraft  
**Estimated Effort**: 4-5 weeks  
**Target Release**: v3.0.0