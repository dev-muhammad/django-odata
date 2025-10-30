# Implementation Plan: SPEC-004 - Migrate to UV

**Specification**: `.specify/specs/004-migrate-to-uv.md`  
**Status**: Planning  
**Created**: 2025-10-30  
**Estimated Duration**: 2 hours

## Overview

This plan outlines the step-by-step implementation of migrating from manual Python venv to uv for dependency management. The implementation will be done in 4 phases to ensure a smooth transition.

## Prerequisites

- uv must be installed on development machines
- Understanding of pyproject.toml structure
- Familiarity with Makefile syntax

## Implementation Phases

### Phase 1: Configure pyproject.toml (30 minutes)

**Objective**: Add proper project configuration for uv compatibility

**Tasks**:
1. Add `[project]` section with metadata
   - Project name: "django-odata"
   - Version: "2.0.0"
   - Description
   - Authors
   - License
   - Keywords and classifiers

2. Add `dependencies` list
   - django>=4.2
   - djangorestframework>=3.12.0
   - odata-query>=0.9.0

3. Add `[project.optional-dependencies]`
   - dev group with all development tools
   - black, flake8, isort, pytest, pytest-cov, pytest-django, pytest-benchmark, mypy

4. Keep existing configurations
   - `[tool.black]`
   - `[tool.isort]`
   - `[tool.pytest.ini_options]`
   - `[build-system]`

**Validation**:
- Run `uv sync --group dev` to verify configuration
- Check that `.venv` is created
- Verify all dependencies are installed

### Phase 2: Update Makefile (30 minutes)

**Objective**: Replace manual venv commands with uv commands

**Tasks**:
1. Remove obsolete targets
   - Remove `venv` target
   - Remove `venv-activate` target

2. Add new targets
   - Add `sync` target: `uv sync --group dev`

3. Update installation targets
   - `install`: Change to `uv pip install -e .`
   - `install-dev`: Change to `uv sync --group dev && uv pip install -e .`

4. Update test targets
   - `test`: Prefix with `uv run`
   - `test-unit`: Prefix with `uv run`
   - `test-integration`: Prefix with `uv run`
   - `test-coverage`: Prefix with `uv run`

5. Update code quality targets
   - `lint`: Prefix flake8 and mypy with `uv run`
   - `format`: Prefix black and isort with `uv run`

6. Update example targets
   - `example-setup`: Prefix python commands with `uv run`
   - `example-run`: Prefix python commands with `uv run`

7. Update help text
   - Update quick start instructions
   - Remove venv-related help text
   - Add sync command help

**Validation**:
- Run `make help` to verify help text
- Test each Makefile target individually

### Phase 3: Update Documentation (30 minutes)

**Objective**: Update all documentation to reflect uv usage

**Tasks**:
1. Update `speckit.specify.md`
   - Replace "Environment Setup" section
   - Change from manual venv to `uv sync`
   - Update all command examples to use `uv run`
   - Add Makefile shortcuts

2. Update command examples
   - Testing section: Add `uv run` prefix
   - Code Quality section: Add `uv run` prefix
   - Example Project section: Add `uv run` prefix
   - Add note about Makefile shortcuts

3. Simplify quick start
   - Before: 3 steps (venv, activate, install)
   - After: 1 step (uv sync)

**Validation**:
- Review documentation for accuracy
- Ensure all examples are runnable
- Check that Makefile shortcuts are mentioned

### Phase 4: Testing & Validation (30 minutes)

**Objective**: Verify everything works with uv

**Tasks**:
1. Clean environment test
   - Remove existing `.venv` directory
   - Run `make sync`
   - Verify `.venv` created
   - Verify `uv.lock` generated

2. Test all Makefile targets
   - `make sync` - should sync dependencies
   - `make test` - should run all tests (257 tests pass)
   - `make test-unit` - should run unit tests
   - `make test-coverage` - should generate coverage report
   - `make lint` - should run linters
   - `make format` - should format code
   - `make example-setup` - should setup database
   - `make example-run` - should start server

3. Verify functionality
   - All 257 tests pass
   - Example application runs
   - Code quality tools work
   - No regressions

4. Documentation verification
   - Quick start instructions work
   - All command examples are accurate
   - Makefile help is clear

**Validation Checklist**:
- [ ] `uv.lock` file generated
- [ ] Virtual environment created in `.venv`
- [ ] All dependencies installed correctly
- [ ] All 257 tests pass
- [ ] Example app runs without errors
- [ ] Code formatting works
- [ ] Linting works
- [ ] Documentation is accurate

## Risk Mitigation

### Risk 1: UV Not Installed
**Impact**: Developers cannot run `make sync`  
**Mitigation**: 
- Add clear error message in Makefile
- Add installation instructions to README
- Provide fallback to pip if needed

### Risk 2: Dependency Resolution Issues
**Impact**: Some dependencies might not resolve correctly  
**Mitigation**:
- Test with clean environment first
- Keep `requirements.txt` as reference
- Document any version constraints needed

### Risk 3: CI/CD Compatibility
**Impact**: CI pipelines might break  
**Mitigation**:
- Test locally before committing
- Update CI configuration if needed
- Provide rollback plan

## Rollback Plan

If issues arise:
1. Revert Makefile changes
2. Revert pyproject.toml changes
3. Revert documentation changes
4. Return to manual venv workflow

## Success Criteria

1. ✅ Developers can set up environment with `make sync`
2. ✅ All 257 tests pass with uv-managed environment
3. ✅ Example application runs correctly
4. ✅ Code quality tools work (black, isort, flake8, mypy)
5. ✅ Documentation is clear and accurate
6. ✅ No performance regressions
7. ✅ Development workflow is faster

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Configure pyproject.toml | 30 min | None |
| Phase 2: Update Makefile | 30 min | Phase 1 |
| Phase 3: Update Documentation | 30 min | Phase 1, 2 |
| Phase 4: Testing & Validation | 30 min | Phase 1, 2, 3 |
| **Total** | **2 hours** | |

## Notes

- This is a non-breaking change for end users
- Only affects development workflow
- Can be implemented incrementally
- Easy to rollback if needed
- Improves developer experience significantly

## Next Steps

After implementation:
1. Create pull request with changes
2. Test in CI/CD environment
3. Update team on new workflow
4. Consider adding uv to CI/CD for faster builds
5. Monitor for any issues in first week