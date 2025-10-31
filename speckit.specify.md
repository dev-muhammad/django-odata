# Django OData - Speckit Configuration

**Project**: Django OData  
**Type**: Python Library  
**Repository**: https://github.com/alexandre-fundcraft/fc-django-odata  
**Last Updated**: 2025-10-30

## Project Overview

Django OData is a comprehensive Django package that implements the OData (Open Data Protocol) v4.0 specification for REST APIs. It transforms Django models into OData-compliant endpoints with powerful querying capabilities, enabling standardized data access patterns with minimal configuration.

### Core Purpose
Provide enterprise-grade OData functionality for Django applications while maintaining:
- **Standards Compliance**: Full OData v4.0 specification adherence
- **Zero Dependencies**: Native implementations without external library dependencies
- **Developer Experience**: Minimal configuration (≤5 lines to transform models)
- **Performance**: Automatic query optimization and efficient data loading

## Active Technologies

### Core Stack
- **Python**: ≥3.8
- **Django**: ≥4.2 LTS (supported until April 2026)
- **Django REST Framework**: ≥3.12.0

### Development Tools
- **Testing**: pytest, pytest-cov, pytest-django
- **Code Quality**: ruff, mypy
- **Build**: setuptools, wheel, twine
- **Documentation**: Markdown

### Current Dependencies (Transitioning)
- **drf-flex-fields**: ≥1.0.0 (being removed in v2.0.0 - see SPEC-001)

## Project Structure

```text
fc-django-odata/
├── .specify/                    # Speckit configuration and workflows
│   ├── memory/
│   │   └── constitution.md      # Project constitution and governance
│   ├── specs/                   # Feature specifications
│   │   └── 001-remove-drf-flex-fields.md
│   ├── plans/                   # Implementation plans
│   │   └── 001-remove-drf-flex-fields.md
│   ├── scripts/                 # Automation scripts
│   └── templates/               # Document templates
├── django_odata/                # Main package
│   ├── __init__.py
│   ├── serializers.py          # OData serializers
│   ├── viewsets.py             # OData viewsets
│   ├── mixins.py               # OData mixins
│   └── utils.py                # Utility functions
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── performance/            # Performance benchmarks
├── example/                     # Example Django project
│   └── blog/                   # Sample blog application
├── docs/                        # Documentation (future)
├── README.md                    # Main documentation
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Development dependencies
├── setup.py                     # Package configuration
└── pyproject.toml              # Build system configuration
```

## Development Commands

### Environment Setup
```bash
# Sync dependencies with uv (creates venv automatically)
uv sync --group dev

# Install package in development mode
uv pip install -e .
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=django_odata --cov-report=html

# Run specific test file
uv run pytest tests/test_serializers.py

# Run integration tests only
uv run pytest tests/integration/

# Run performance benchmarks
uv run pytest tests/performance/ --benchmark-only

# Or use Makefile shortcuts
make test              # Run all tests
make test-unit         # Run unit tests only
make test-coverage     # Run with coverage
```

### Code Quality
```bash
# Format code with ruff
uv run ruff format django_odata/ tests/

# Lint code with ruff
uv run ruff check django_odata/ tests/

# Auto-fix issues with ruff
uv run ruff check --fix django_odata/ tests/

# Lint code
uv run flake8 django_odata/ tests/

# Type checking
uv run mypy django_odata/

# Or use Makefile shortcuts
make format    # Format code with ruff
make lint      # Run linters with ruff
```

### Example Project
```bash
# Run example project
cd example/
uv run python manage.py migrate
uv run python manage.py runserver

# Or use Makefile shortcuts
make example-setup    # Setup database
make example-run      # Run server

# Test OData endpoints
curl "http://localhost:8000/odata/posts/"
curl "http://localhost:8000/odata/posts/?$select=id,title&$expand=author"
```

### Package Management
```bash
# Build package
python -m build

# Upload to PyPI (test)
twine upload --repository testpypi dist/*

# Upload to PyPI (production)
twine upload dist/*
```

## Code Style Guidelines

### Python Style
- **Formatter**: Ruff (line length: 88)
- **Linting**: Ruff with flake8-compatible rules
- **Type Hints**: Required for all public APIs
- **Docstrings**: Google style for all public classes/functions

### Django/DRF Conventions
- **Serializers**: Inherit from `ODataModelSerializer` or `ODataSerializer`
- **ViewSets**: Inherit from `ODataModelViewSet`
- **Mixins**: Use composition over inheritance where possible
- **Models**: Follow Django best practices, use explicit field types

### Testing Standards
- **Coverage**: Minimum 90% for all modules
- **Test Organization**: Unit tests in `tests/`, integration in `tests/integration/`
- **Naming**: `test_<functionality>_<scenario>_<expected_result>`
- **Fixtures**: Use pytest fixtures, avoid test interdependencies

### Documentation
- **Code Comments**: Explain "why", not "what"
- **Docstrings**: Include Args, Returns, Raises sections
- **README**: Keep examples up-to-date and runnable
- **Changelog**: Follow Keep a Changelog format

## Recent Changes

### SPEC-001: Remove drf-flex-fields Dependency (In Progress)
**Status**: Completed
**Target**: v2.0.0  
**Impact**: Major architectural change

**What's Being Added**:
- Native field selection implementation (`NativeFieldSelectionMixin`)
- Native field expansion implementation (`NativeFieldExpansionMixin`)
- Performance improvements (10-20% target)
- Simplified codebase with zero external dependencies

**What's Being Removed**:
- `drf-flex-fields` dependency
- FlexFields-specific code in mixins and serializers

**Migration Path**: Backward compatible - no user code changes required

### v0.1.0: Initial Release (2025-08-30)
**What Was Added**:
- Full OData v4 query support ($filter, $orderby, $top, $skip, $select, $expand, $count)
- Dynamic field selection and expansion via drf-flex-fields
- Metadata endpoints ($metadata, service document)
- Comprehensive test suite with >90% coverage
- Example blog application
- Support for Django 4.2 LTS and Python 3.8+

## Governance

This project follows the principles defined in [`.specify/memory/constitution.md`](.specify/memory/constitution.md):

1. **OData Standards Compliance** (NON-NEGOTIABLE)
2. **Zero External Dependencies** for core functionality
3. **Test-First Development** (NON-NEGOTIABLE)
4. **Developer Experience First**
5. **Performance & Simplicity**

### Development Workflow
1. **Specification Phase**: Create spec using `.specify/templates/spec-template.md`
2. **Planning Phase**: Break down into tasks using `.specify/templates/plan-template.md`
3. **Implementation Phase**: TDD approach with small, focused commits
4. **Testing Phase**: 100% test pass rate, ≥90% coverage
5. **Release Phase**: Beta period for major changes, comprehensive changelog

### Quality Gates
- All PRs require maintainer review
- Tests must pass in CI before merge
- Documentation must be updated for user-facing changes
- Performance benchmarks must not regress

## Active Features

### SPEC-001: Remove drf-flex-fields Dependency
**Status**: ✅ Completed
**Branch**: `001-remove-drf-flex-fields`
**Priority**: High
**Complexity**: Medium
**Timeline**: 3 weeks development + 2 weeks beta

**Phases**:
1. ✅ Preparation (1 day) - Performance baseline, audit
2. ✅ Field Selection (3 days) - Native implementation
3. ✅ Field Expansion (4 days) - Native implementation
4. ✅ Update Serializers (2 days) - Integration
5. ✅ Testing (3 days) - Comprehensive validation
6. ✅ Documentation (2 days) - Update all docs
7. ✅ Release (1 day) - Final release

### SPEC-003: Optimize Database Queries with Field Selection
**Status**: 📝 Specification Phase
**Branch**: Not yet created
**Priority**: High
**Complexity**: Medium
**Timeline**: 1-2 weeks development

**Objective**: Optimize database queries to fetch only requested fields in `$select` parameters, using Django's `.only()` method with `select_related()` and `Prefetch` objects with `prefetch_related()`.

**Expected Impact**:
- 20-40% performance improvement for queries with field selection
- Reduced database-to-application data transfer
- Lower memory usage
- Faster query execution for tables with many columns

**Phases**:
1. ⏳ Main Queryset Optimization - Apply `.only()` to base queries
2. ⏳ select_related Optimization - Field selection for forward relations
3. ⏳ prefetch_related Optimization - Field selection with Prefetch objects
4. ⏳ Testing & Validation - Comprehensive testing and benchmarking
5. ⏳ Documentation - Update docs with performance notes

### SPEC-004: Always Include Count in OData Responses
**Status**: ✅ Ready for Implementation
**Branch**: Not yet created
**Priority**: Medium
**Complexity**: Low
**Timeline**: 1.5 days development

**Objective**: Modify OData response format to always include `@odata.count` in collection responses without requiring `$count=true` in the URL parameter. This improves API usability by providing count information by default while maintaining OData v4.0 compliance.

**Current Behavior**:
```json
// Request: GET /odata/posts/
{
  "@odata.context": "...",
  "value": [...]
}

// Request: GET /odata/posts/?$count=true
{
  "@odata.context": "...",
  "@odata.count": 42,
  "value": [...]
}
```

**Desired Behavior**:
```json
// Request: GET /odata/posts/
{
  "@odata.context": "...",
  "@odata.count": 42,
  "value": [...]
}

// Request: GET /odata/posts/?$count=true (backward compatible)
{
  "@odata.context": "...",
  "@odata.count": 42,
  "value": [...]
}
```

**OData v4.0 Compliance**:
According to OData v4.0 specification section 11.2.5.5, the `@odata.count` annotation:
- MUST be included when `$count=true` is specified
- MAY be included in responses even when not explicitly requested
- Represents the total count of items matching the request, ignoring `$top` and `$skip`

**Implementation Requirements**:
1. **Always Calculate Count**: Modify `ODataMixin.list()` in `django_odata/mixins.py` to always compute total count for collection responses
2. **Include in Response**: Always add `@odata.count` to response data structure
3. **Pagination Compatibility**: Ensure count reflects total items, not just current page
4. **Performance Consideration**: Count query executes before pagination, must be optimized
5. **Backward Compatibility**: Support explicit `$count=true` parameter (no-op, count already included)

**Files to Modify**:
- `django_odata/mixins.py`: Update `ODataMixin.list()` method (lines 579-622)
- `django_odata/viewsets.py`: Update `ODataViewSet.list()` method (lines 41-62)
- `tests/test_mixins.py`: Add tests for default count inclusion
- `tests/test_viewsets.py`: Add tests for viewset count behavior
- `tests/integration/test_odata_integration.py`: Add integration tests
- `README.md`: Update documentation with count behavior
- `docs/migration_guide.md`: Document behavior change

**Expected Impact**:
- **Performance**: Minimal impact - one additional `COUNT(*)` query per collection request
- **API Usability**: Improved - clients always know total count without additional parameter
- **Breaking Changes**: None - this is an additive change that enhances responses
- **Standards Compliance**: Maintains OData v4.0 compliance (count is optional, not forbidden)

**Testing Requirements**:
1. Unit tests for count inclusion in all collection responses
2. Integration tests with pagination ($top, $skip) to verify count reflects total
3. Integration tests with filtering ($filter) to verify count reflects filtered total
4. Performance benchmarks to measure count query impact
5. Backward compatibility tests with explicit `$count=true` parameter

**Performance Optimization Notes**:
- Use `queryset.count()` which generates optimized `SELECT COUNT(*)`
- Count executes on filtered queryset (after `$filter` applied)
- Count executes before pagination (reflects total, not page size)
- Consider caching strategies for frequently accessed collections (future enhancement)

**Phases**:
1. ⏳ Update Core Logic - Modify ODataMixin.list() and ODataViewSet.list()
2. ⏳ Update Tests - Add comprehensive test coverage
3. ⏳ Documentation - Update README and migration guide
4. ⏳ Testing & Validation - Run full test suite and performance benchmarks

## Contact & Resources

- **Maintainer**: Alexandre Busquets (@alexandre-fundcraft)
- **Repository**: https://github.com/alexandre-fundcraft/fc-django-odata
- **Issues**: https://github.com/alexandre-fundcraft/fc-django-odata/issues
- **Documentation**: README.md (comprehensive guide)
- **OData Spec**: http://docs.oasis-open.org/odata/odata/v4.0/

---

**Note**: This file is auto-maintained by Speckit. Manual edits should be placed between `<!-- MANUAL ADDITIONS START -->` and `<!-- MANUAL ADDITIONS END -->` markers.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->