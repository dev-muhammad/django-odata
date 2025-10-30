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
- **Code Quality**: black, isort, flake8, mypy
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
# Format code
uv run black django_odata/ tests/

# Sort imports
uv run isort django_odata/ tests/

# Lint code
uv run flake8 django_odata/ tests/

# Type checking
uv run mypy django_odata/

# Or use Makefile shortcuts
make format    # Format code with black and isort
make lint      # Run linters
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
- **Formatter**: Black (line length: 88)
- **Import Order**: isort with black profile
- **Linting**: flake8 with max-line-length=88
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