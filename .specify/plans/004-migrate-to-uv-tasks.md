# Task Checklist: SPEC-004 - Migrate to UV

**Specification**: `.specify/specs/004-migrate-to-uv.md`  
**Plan**: `.specify/plans/004-migrate-to-uv.md`  
**Status**: Ready to Implement  
**Created**: 2025-10-30

## Phase 1: Configure pyproject.toml ⏱️ 30 min

### Task 1.1: Add [project] Section
- [ ] Add `[project]` section to pyproject.toml
- [ ] Set name = "django-odata"
- [ ] Set version = "2.0.0"
- [ ] Set description
- [ ] Set readme = "README.md"
- [ ] Set requires-python = ">=3.8"
- [ ] Set license = {text = "MIT"}

### Task 1.2: Add Project Metadata
- [ ] Add authors list with name and email
- [ ] Add keywords list (django, odata, rest, api, djangorestframework)
- [ ] Add classifiers for:
  - Development Status
  - Framework (Django 4.2, 5.0)
  - License
  - Python versions (3.8-3.12)

### Task 1.3: Add Dependencies
- [ ] Add `dependencies` list with:
  - django>=4.2
  - djangorestframework>=3.12.0
  - odata-query>=0.9.0

### Task 1.4: Add Optional Dependencies
- [ ] Add `[project.optional-dependencies]` section
- [ ] Add `dev` group with:
  - black>=21.0
  - flake8>=3.8
  - isort>=5.0
  - pytest>=6.0
  - pytest-cov>=2.0
  - pytest-django>=4.0
  - pytest-benchmark>=3.4.0
  - mypy>=0.900

### Task 1.5: Verify Configuration
- [ ] Keep existing `[tool.black]` configuration
- [ ] Keep existing `[tool.isort]` configuration
- [ ] Keep existing `[tool.pytest.ini_options]` configuration
- [ ] Keep existing `[build-system]` configuration
- [ ] Test with `uv sync --group dev`

---

## Phase 2: Update Makefile ⏱️ 30 min

### Task 2.1: Remove Obsolete Targets
- [ ] Remove `venv` target
- [ ] Remove `venv-activate` target
- [ ] Update `.PHONY` declaration

### Task 2.2: Add New Targets
- [ ] Add `sync` target with `uv sync --group dev`
- [ ] Add success message and next steps

### Task 2.3: Update Installation Targets
- [ ] Update `install` to use `uv pip install -e .`
- [ ] Update `install-dev` to use `uv sync --group dev && uv pip install -e .`

### Task 2.4: Update Test Targets
- [ ] Update `test` to use `uv run pytest`
- [ ] Update `test-unit` to use `uv run pytest`
- [ ] Update `test-integration` to use `uv run pytest`
- [ ] Update `test-coverage` to use `uv run pytest`

### Task 2.5: Update Code Quality Targets
- [ ] Update `lint` to use `uv run flake8` and `uv run mypy`
- [ ] Update `format` to use `uv run black` and `uv run isort`

### Task 2.6: Update Example Targets
- [ ] Update `example-setup` to use `uv run python manage.py`
- [ ] Update `example-run` to use `uv run python manage.py`

### Task 2.7: Update Help Text
- [ ] Update "Environment Setup" section in help
- [ ] Remove venv-related instructions
- [ ] Add `sync` command description
- [ ] Update "Quick Start" section
- [ ] Change from 3 steps to 1 step

### Task 2.8: Test Makefile
- [ ] Run `make help` to verify help text
- [ ] Verify all targets are listed correctly

---

## Phase 3: Update Documentation ⏱️ 30 min

### Task 3.1: Update speckit.specify.md - Environment Setup
- [ ] Replace "Create virtual environment" section
- [ ] Remove `python -m venv venv` instructions
- [ ] Remove `source venv/bin/activate` instructions
- [ ] Add `uv sync --group dev` as primary method
- [ ] Add `uv pip install -e .` for package installation

### Task 3.2: Update speckit.specify.md - Testing Section
- [ ] Update all pytest commands to use `uv run pytest`
- [ ] Add Makefile shortcuts (make test, make test-unit, make test-coverage)
- [ ] Keep curl examples unchanged

### Task 3.3: Update speckit.specify.md - Code Quality Section
- [ ] Update black command to use `uv run black`
- [ ] Update isort command to use `uv run isort`
- [ ] Update flake8 command to use `uv run flake8`
- [ ] Update mypy command to use `uv run mypy`
- [ ] Add Makefile shortcuts (make format, make lint)

### Task 3.4: Update speckit.specify.md - Example Project Section
- [ ] Update manage.py commands to use `uv run python manage.py`
- [ ] Add Makefile shortcuts (make example-setup, make example-run)
- [ ] Keep curl examples unchanged

### Task 3.5: Review Documentation
- [ ] Verify all command examples are accurate
- [ ] Ensure Makefile shortcuts are mentioned
- [ ] Check that quick start is simplified

---

## Phase 4: Testing & Validation ⏱️ 30 min

### Task 4.1: Clean Environment Test
- [ ] Remove existing `.venv` directory if present
- [ ] Run `make sync`
- [ ] Verify `.venv` directory is created
- [ ] Verify `uv.lock` file is generated
- [ ] Verify all dependencies are installed

### Task 4.2: Test Makefile Targets
- [ ] Test `make sync` - should sync dependencies
- [ ] Test `make install` - should install package
- [ ] Test `make install-dev` - should install with dev deps
- [ ] Test `make test` - should run all tests
- [ ] Test `make test-unit` - should run unit tests only
- [ ] Test `make test-integration` - should run integration tests
- [ ] Test `make test-coverage` - should generate coverage report
- [ ] Test `make lint` - should run linters
- [ ] Test `make format` - should format code
- [ ] Test `make example-setup` - should setup database
- [ ] Test `make example-run` - should start server (manual stop)
- [ ] Test `make clean` - should clean artifacts

### Task 4.3: Verify Test Results
- [ ] All 257 tests pass
- [ ] No test failures or errors
- [ ] Coverage report generated successfully
- [ ] No regressions in test performance

### Task 4.4: Verify Example Application
- [ ] Example app database created
- [ ] Example app server starts without errors
- [ ] Can access http://localhost:8000/odata/posts/
- [ ] Can access http://localhost:8000/admin/
- [ ] OData queries work correctly

### Task 4.5: Verify Code Quality Tools
- [ ] Black formats code without errors
- [ ] Isort sorts imports without errors
- [ ] Flake8 runs without errors
- [ ] Mypy runs without errors (if configured)

### Task 4.6: Documentation Verification
- [ ] Quick start instructions work as documented
- [ ] All command examples are runnable
- [ ] Makefile help text is clear and accurate
- [ ] No broken links or references

### Task 4.7: Final Validation Checklist
- [ ] `uv.lock` file exists and is valid
- [ ] `.venv` directory exists with correct Python version
- [ ] All dependencies installed correctly
- [ ] All 257 tests pass
- [ ] Example application runs
- [ ] Code formatting works
- [ ] Linting works
- [ ] Documentation is accurate and complete

---

## Completion Criteria

All tasks must be completed and verified before marking SPEC-004 as complete:

- [ ] Phase 1: Configure pyproject.toml (100%)
- [ ] Phase 2: Update Makefile (100%)
- [ ] Phase 3: Update Documentation (100%)
- [ ] Phase 4: Testing & Validation (100%)

## Notes

- Work through phases sequentially
- Test after each phase before proceeding
- Document any issues or deviations
- Update this checklist as tasks are completed
- If any task fails, investigate and resolve before continuing

## Estimated Completion Time

- **Total Tasks**: 60+
- **Estimated Duration**: 2 hours
- **Actual Duration**: _To be filled after completion_

## Status Tracking

- **Started**: _Not started_
- **Phase 1 Complete**: _Pending_
- **Phase 2 Complete**: _Pending_
- **Phase 3 Complete**: _Pending_
- **Phase 4 Complete**: _Pending_
- **Finished**: _Pending_