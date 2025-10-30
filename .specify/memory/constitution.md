# Django OData Constitution

## Core Principles

### I. OData Standards Compliance (NON-NEGOTIABLE)
**Every feature MUST adhere to OData v4.0 specification**
- All query options (`$filter`, `$orderby`, `$top`, `$skip`, `$select`, `$expand`, `$count`) must follow OData v4 syntax exactly
- Response formats must include proper `@odata.context` and metadata annotations
- Error responses must follow OData error format specification
- Metadata endpoints (`$metadata`, service document) must be standards-compliant
- **Rationale**: Standards compliance ensures interoperability with OData clients and tools

### II. Zero External Dependencies for Core Functionality
**Core OData features must not depend on third-party libraries**
- Field selection and expansion must be implemented natively
- Query parsing and translation must use only Django ORM and Python stdlib
- External dependencies allowed only for: Django (>=4.2), DRF (>=3.12), Python (>=3.8)
- Any new dependency requires explicit justification and approval
- **Rationale**: Reduces maintenance burden, version conflicts, and improves long-term stability

### III. Test-First Development (NON-NEGOTIABLE)
**All features require tests before implementation**
- TDD mandatory: Write tests → Get approval → Tests fail → Implement → Tests pass
- Minimum 90% code coverage for all modules
- Integration tests required for: OData query combinations, field expansion, metadata generation
- Performance regression tests must pass before release
- **Rationale**: Ensures reliability, prevents regressions, and documents expected behavior

### IV. Developer Experience First
**API must be intuitive and require minimal configuration**
- Transform Django models to OData endpoints with ≤5 lines of code
- Maintain backward compatibility unless major version bump
- Clear error messages with actionable guidance
- Comprehensive documentation with real-world examples
- **Rationale**: Adoption depends on ease of use and clear documentation

### V. Performance & Simplicity
**Optimize for common cases, keep implementation simple**
- Automatic query optimization (select_related/prefetch_related) for expanded relations
- Native implementations preferred over abstraction layers
- YAGNI principle: Don't add features until needed
- Benchmark critical paths, no performance regressions allowed
- **Rationale**: Fast, maintainable code that solves real problems

## Architecture Constraints

### Code Organization
- **Separation of Concerns**: Serializers, ViewSets, Mixins, and Utils must remain distinct
- **Single Responsibility**: Each module/class has one clear purpose
- **No Circular Dependencies**: Import structure must be acyclic
- **Type Hints Required**: All public APIs must have type annotations

### Django/DRF Integration
- **Extend, Don't Replace**: Build on DRF patterns, don't reinvent them
- **Django ORM Only**: No raw SQL unless absolutely necessary and documented
- **Model Agnostic**: Work with any Django model without modification
- **Middleware Free**: No required middleware or global settings

### API Stability
- **Semantic Versioning**: MAJOR.MINOR.PATCH strictly enforced
- **Deprecation Policy**: 6-month warning before removing features
- **Migration Guides**: Required for all breaking changes
- **Beta Period**: Minimum 2 weeks for major versions

## Development Workflow

### Feature Development Process
1. **Specification Phase**
   - Create spec document using `.specify/templates/spec-template.md`
   - Define user scenarios with acceptance criteria
   - Identify functional requirements and success metrics
   - Get spec approval before implementation

2. **Planning Phase**
   - Break spec into actionable tasks using `.specify/templates/plan-template.md`
   - Estimate effort and timeline
   - Identify dependencies and risks
   - Create GitHub project board

3. **Implementation Phase**
   - Write tests first (TDD)
   - Implement in small, focused commits
   - Code review required for all changes
   - Update documentation alongside code

4. **Testing Phase**
   - All tests must pass (100% pass rate)
   - Coverage must be ≥90%
   - Performance benchmarks must not regress
   - Integration tests with example project

5. **Release Phase**
   - Beta release for major changes (minimum 2 weeks)
   - Update CHANGELOG.md
   - Create migration guide if needed
   - Tag release and publish to PyPI

### Code Review Requirements
- **All PRs require review** from at least one maintainer
- **Tests must pass** in CI before merge
- **Documentation updated** for user-facing changes
- **No merge without approval** - no exceptions

### Quality Gates
- **Pre-commit**: Linting (black, isort, flake8) must pass
- **CI Pipeline**: Tests, coverage, type checking must pass
- **Pre-release**: Performance benchmarks, integration tests, example project
- **Post-release**: Monitor issues, respond within 48 hours

## Testing Standards

### Test Coverage Requirements
- **Unit Tests**: Every function/method with business logic
- **Integration Tests**: All OData query combinations
- **Performance Tests**: Baseline and regression tests for critical paths
- **Example Project**: Must work without modifications after changes

### Test Organization
```
tests/
├── unit/              # Fast, isolated tests
├── integration/       # Full request/response cycles
├── performance/       # Benchmarks and regression tests
└── fixtures/          # Shared test data
```

### Test Quality
- **Fast**: Unit tests complete in <1s, integration in <10s
- **Isolated**: No test depends on another test's state
- **Deterministic**: Same input always produces same output
- **Clear**: Test names describe what they verify

## Documentation Standards

### Required Documentation
- **README.md**: Quick start, features, installation
- **API Documentation**: All public classes/functions
- **Migration Guides**: For breaking changes
- **Examples**: Real-world usage patterns
- **Changelog**: All releases with categorized changes

### Documentation Quality
- **Code Examples**: Must be runnable and tested
- **Clear Language**: Technical but accessible
- **Up-to-date**: Updated with every code change
- **Searchable**: Good structure and keywords

## Security & Compliance

### Security Requirements
- **No SQL Injection**: All queries use Django ORM parameterization
- **Input Validation**: All OData parameters validated before use
- **Error Handling**: No sensitive information in error messages
- **Dependency Scanning**: Regular security audits of dependencies

### Data Privacy
- **No Data Logging**: Don't log user data in library code
- **Configurable**: Users control what data is exposed
- **Documentation**: Clear guidance on securing OData endpoints

## Governance

### Constitution Authority
- This constitution supersedes all other development practices
- Amendments require documentation, approval, and migration plan
- All PRs and reviews must verify compliance with constitution
- Complexity must be justified against these principles

### Decision Making
- **Technical Decisions**: Maintainers vote, majority wins
- **Breaking Changes**: Require unanimous maintainer approval
- **New Dependencies**: Require explicit justification and approval
- **Architecture Changes**: Require spec document and review

### Conflict Resolution
- Constitution principles take precedence
- When principles conflict, prioritize in order: Standards Compliance → Zero Dependencies → Test-First → Developer Experience → Performance
- Escalate unresolved conflicts to project owner

### Amendment Process
1. Propose amendment with rationale
2. Discuss with maintainers (minimum 1 week)
3. Vote (requires 2/3 majority)
4. Update constitution and notify community
5. Create migration plan if needed

## Success Metrics

### Project Health
- **Test Coverage**: ≥90% maintained
- **CI Pass Rate**: ≥95% on main branch
- **Issue Response Time**: ≤48 hours
- **Documentation Coverage**: 100% of public API

### Community Health
- **Active Maintainers**: ≥2 people
- **Release Cadence**: Patch releases monthly, minor quarterly
- **Issue Resolution**: 80% closed within 30 days
- **User Satisfaction**: Positive feedback on ease of use

### Technical Health
- **Performance**: No regressions, 10-20% improvement targets
- **Dependencies**: Minimize count, keep updated
- **Code Quality**: Linting passes, type hints complete
- **Security**: Zero known vulnerabilities

---

**Version**: 1.0.0  
**Ratified**: 2025-10-29  
**Last Amended**: 2025-10-29  
**Next Review**: 2026-04-29 (6 months)

**Maintainers**: Alexandre Busquets (@alexandre-fundcraft)  
**Project Repository**: https://github.com/alexandre-fundcraft/fc-django-odata
