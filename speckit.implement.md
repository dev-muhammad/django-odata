# Speckit Implementation Guide - Django OData

**Purpose**: Step-by-step guide for implementing and using Speckit in the Django OData project  
**Audience**: Contributors, maintainers, and AI agents  
**Last Updated**: 2025-10-29

## Quick Start

### For New Contributors

```bash
# 1. Clone and setup
git clone https://github.com/alexandre-fundcraft/fc-django-odata.git
cd fc-django-odata

# Option A: Using uv (recommended - much faster)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .[dev]

# Option B: Using traditional pip
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .[dev]

# 2. Read the constitution
cat .specify/memory/constitution.md

# 3. Check project configuration
cat speckit.specify.md

# 4. Review workflow
cat speckit.plan.md

# 5. Start contributing!
```

### For AI Agents

**Context Files to Read** (in order):
1. [`speckit.specify.md`](speckit.specify.md) - Project overview and guidelines
2. [`.specify/memory/constitution.md`](.specify/memory/constitution.md) - Governance and principles
3. [`speckit.plan.md`](speckit.plan.md) - Workflow implementation
4. Current feature spec (if working on a feature)
5. Current feature plan (if implementing)

**Key Constraints**:
- MUST follow TDD (tests before implementation)
- MUST maintain ≥90% code coverage
- MUST adhere to OData v4.0 specification
- MUST use native implementations (no new dependencies)
- MUST update documentation with code changes

## Implementation Workflows

### Workflow 1: Creating a New Feature

**When to Use**: Starting work on a new feature or enhancement

**Prerequisites**:
- [ ] Feature idea is clear and valuable
- [ ] No duplicate feature exists
- [ ] Aligns with project constitution

**Steps**:

#### Step 1: Create Feature Branch and Spec

```bash
# Run the feature creation script
.specify/scripts/bash/create-new-feature.sh "Your feature description here"

# Example:
.specify/scripts/bash/create-new-feature.sh "Add support for OData batch requests"

# Output will show:
# BRANCH_NAME: 002-batch-requests
# SPEC_FILE: .specify/specs/002-batch-requests/spec.md
# FEATURE_NUM: 002
```

**What Happens**:
- New git branch created: `NNN-feature-name`
- Spec directory created: `.specify/specs/NNN-feature-name/`
- Spec template copied to: `.specify/specs/NNN-feature-name/spec.md`
- Environment variable set: `SPECIFY_FEATURE=NNN-feature-name`

#### Step 2: Write the Specification

Open the generated spec file and fill in all sections:

```markdown
# Feature Specification: [Your Feature Name]

## User Scenarios & Testing (mandatory)

### User Story 1 - [Title] (Priority: P1)
[Describe the user journey]

**Why this priority**: [Explain value]

**Independent Test**: [How to test independently]

**Acceptance Scenarios**:
1. **Given** [state], **When** [action], **Then** [outcome]
2. **Given** [state], **When** [action], **Then** [outcome]

### User Story 2 - [Title] (Priority: P2)
[Continue with more stories...]

## Requirements (mandatory)

### Functional Requirements
- **FR-001**: System MUST [specific capability]
- **FR-002**: System MUST [specific capability]
- **FR-003**: Users MUST be able to [key interaction]

### Key Entities (if applicable)
- **[Entity 1]**: [Description and key attributes]
- **[Entity 2]**: [Description and relationships]

## Success Criteria (mandatory)

### Measurable Outcomes
- **SC-001**: [Measurable metric]
- **SC-002**: [Measurable metric]
- **SC-003**: [User satisfaction metric]
```

**Validation Checklist**:
- [ ] All user stories are prioritized (P1, P2, P3)
- [ ] Each story is independently testable
- [ ] Functional requirements are clear and specific
- [ ] Success criteria are measurable
- [ ] Edge cases are identified
- [ ] No placeholders remain (all [BRACKETS] filled)

#### Step 3: Get Spec Approval

```bash
# Commit the spec
git add .specify/specs/NNN-feature-name/spec.md
git commit -m "[SPEC-NNN] Add specification for [feature name]"
git push origin NNN-feature-name

# Create PR for spec review
# Title: "[SPEC-NNN] Specification: [Feature Name]"
# Description: Link to spec file, summarize key points
```

**Review Criteria**:
- Spec follows template structure
- All mandatory sections complete
- Requirements are clear and testable
- Success criteria are measurable
- Maintainer approval obtained

#### Step 4: Create Implementation Plan

```bash
# Run the plan setup script
.specify/scripts/bash/setup-plan.sh

# Output will show:
# FEATURE_SPEC: .specify/specs/NNN-feature-name/spec.md
# IMPL_PLAN: .specify/plans/NNN-feature-name.md
```

Open the plan file and break down the work:

```markdown
# PLAN-NNN: [Feature Name]

**Related Spec**: SPEC-NNN  
**Status**: Ready for Implementation  
**Created**: YYYY-MM-DD

## Overview
[Brief summary of implementation approach]

## Implementation Phases

### Phase 1: [Phase Name] (X days)

#### 1.1 [Task Name]
**File**: `path/to/file.py`
**Task**: Detailed description of what to do
**Code Example**:
```python
# Example of what to implement
```
**Acceptance**: How to verify completion

#### 1.2 [Next Task]
[Continue...]

### Phase 2: [Next Phase] (Y days)
[Continue...]

## Task Dependencies
```
Phase 1 → Phase 2 → Phase 3
  1.1      2.1      3.1
  1.2      2.2      3.2
```

## Timeline Estimate
- Phase 1: X days
- Phase 2: Y days
- Total: Z days

## Risk Mitigation
### Risk 1: [Description]
**Mitigation**: [How to address]
```

**Validation Checklist**:
- [ ] All tasks are concrete and actionable
- [ ] Dependencies are clearly identified
- [ ] Timeline is realistic
- [ ] Risks are documented with mitigations
- [ ] Each task has clear acceptance criteria

#### Step 5: Get Plan Approval

```bash
# Commit the plan
git add .specify/plans/NNN-feature-name.md
git commit -m "[SPEC-NNN] Add implementation plan"
git push origin NNN-feature-name

# Update PR or create new one for plan review
```

### Workflow 2: Implementing a Feature

**When to Use**: After spec and plan are approved

**Prerequisites**:
- [ ] Spec approved by maintainer
- [ ] Plan approved by maintainer
- [ ] Development environment set up
- [ ] All tests currently passing

**Steps**:

#### Step 1: Set Up Development Environment

```bash
# Ensure you're on the feature branch
git checkout NNN-feature-name

# Pull latest changes
git pull origin NNN-feature-name

# Install dependencies
# Using uv (recommended):
uv pip install -e .[dev]

# Or using pip:
pip install -e .[dev]

# Run tests to ensure clean baseline
pytest --cov=django_odata
```

#### Step 2: Implement Using TDD

For each task in the plan:

**2.1 Write Tests First**

```python
# tests/test_new_feature.py

import pytest
from django_odata.new_module import NewFeature

class TestNewFeature:
    """Tests for new feature implementation."""
    
    def test_basic_functionality(self):
        """Test basic feature works as expected."""
        # Arrange
        feature = NewFeature()
        
        # Act
        result = feature.do_something()
        
        # Assert
        assert result == expected_value
    
    def test_edge_case_empty_input(self):
        """Test feature handles empty input correctly."""
        feature = NewFeature()
        result = feature.do_something(input="")
        assert result is None
    
    def test_error_handling(self):
        """Test feature raises appropriate errors."""
        feature = NewFeature()
        with pytest.raises(ValueError):
            feature.do_something(invalid_input)
```

**2.2 Run Tests (Should Fail)**

```bash
pytest tests/test_new_feature.py -v

# Expected: Tests fail because feature not implemented yet
```

**2.3 Implement Feature**

```python
# django_odata/new_module.py

from typing import Optional

class NewFeature:
    """
    Implementation of new feature.
    
    This class provides [description of functionality].
    """
    
    def do_something(self, input: Optional[str] = None) -> Optional[str]:
        """
        Perform the main feature operation.
        
        Args:
            input: Optional input parameter
            
        Returns:
            Processed result or None if input is empty
            
        Raises:
            ValueError: If input is invalid
        """
        if input == "":
            return None
        
        if input is None:
            input = "default"
        
        # Implementation logic here
        return f"processed_{input}"
```

**2.4 Run Tests (Should Pass)**

```bash
pytest tests/test_new_feature.py -v

# Expected: All tests pass
```

**2.5 Check Coverage**

```bash
pytest --cov=django_odata --cov-report=term-missing

# Ensure new module has ≥90% coverage
```

**2.6 Commit Changes**

```bash
git add django_odata/new_module.py tests/test_new_feature.py
git commit -m "[SPEC-NNN] Implement [task name]

- Add NewFeature class with do_something method
- Handle edge cases (empty input, None)
- Add comprehensive test coverage

Relates to: .specify/specs/NNN-feature-name/spec.md
Task: Phase 1, Task 1.1"
```

#### Step 3: Update Documentation

**3.1 Update README.md**

Add usage examples:

```markdown
### New Feature Name

Description of the feature and when to use it.

```python
from django_odata.new_module import NewFeature

# Example usage
feature = NewFeature()
result = feature.do_something("input")
```

**3.2 Update API Documentation**

Add docstrings to all public classes and methods (already done in implementation).

**3.3 Update CHANGELOG.md**

```markdown
## [Unreleased]

### Added
- New feature: [Brief description] (#NNN)
  - Capability 1
  - Capability 2
```

**3.4 Commit Documentation**

```bash
git add README.md CHANGELOG.md
git commit -m "[SPEC-NNN] Update documentation for new feature"
```

#### Step 4: Run Full Test Suite

```bash
# Run all tests
pytest -v

# Check coverage
pytest --cov=django_odata --cov-report=html

# Run linting and formatting
ruff format django_odata/ tests/
ruff check django_odata/ tests/

# Type checking
mypy django_odata/
```

**Quality Gates** (all must pass):
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥90%
- [ ] Ruff formatting passes
- [ ] Ruff linting passes
- [ ] mypy passes (no type errors)

#### Step 5: Test with Example Project

```bash
cd example/
python manage.py migrate
python manage.py runserver

# In another terminal, test the endpoints
curl "http://localhost:8000/odata/posts/"
curl "http://localhost:8000/odata/posts/?[new_feature_params]"
```

**Validation**:
- [ ] Example project runs without errors
- [ ] New feature works as expected
- [ ] No regressions in existing functionality

#### Step 6: Create Pull Request

```bash
# Push all changes
git push origin NNN-feature-name

# Create PR with:
# Title: "[SPEC-NNN] Implement [Feature Name]"
# Description:
# - Link to spec and plan
# - Summary of changes
# - Test results
# - Screenshots/examples if applicable
```

**PR Checklist**:
- [ ] All commits reference SPEC-NNN
- [ ] Tests pass in CI
- [ ] Coverage ≥90%
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] Maintainer review requested

### Workflow 3: Reviewing a Feature

**When to Use**: Reviewing a PR for a new feature

**Prerequisites**:
- [ ] PR created with spec and plan references
- [ ] CI checks passing
- [ ] All required files updated

**Review Checklist**:

#### Code Quality
- [ ] Follows project code style (ruff)
- [ ] Type hints on all public APIs
- [ ] Clear, descriptive variable names
- [ ] No unnecessary complexity
- [ ] Follows DRY principle

#### Testing
- [ ] Tests cover all acceptance criteria from spec
- [ ] Edge cases tested
- [ ] Error handling tested
- [ ] Coverage ≥90%
- [ ] Tests are clear and maintainable

#### Documentation
- [ ] README.md updated with examples
- [ ] Docstrings on all public APIs
- [ ] CHANGELOG.md updated
- [ ] Migration guide if breaking changes

#### Specification Compliance
- [ ] Implements all functional requirements
- [ ] Meets all success criteria
- [ ] Handles all identified edge cases
- [ ] Follows OData v4.0 spec (if applicable)

#### Constitution Compliance
- [ ] No new external dependencies (or justified)
- [ ] TDD approach followed
- [ ] Maintains backward compatibility
- [ ] Performance not regressed

**Review Process**:

1. **Read the Spec and Plan**
   ```bash
   cat .specify/specs/NNN-feature-name/spec.md
   cat .specify/plans/NNN-feature-name.md
   ```

2. **Check Out the Branch**
   ```bash
   git checkout NNN-feature-name
   git pull origin NNN-feature-name
   ```

3. **Run Tests Locally**
   ```bash
   pytest --cov=django_odata --cov-report=html
   ```

4. **Review Code Changes**
   - Check each file for quality
   - Verify tests match acceptance criteria
   - Ensure documentation is complete

5. **Test Manually**
   ```bash
   cd example/
   python manage.py runserver
   # Test the feature manually
   ```

6. **Provide Feedback**
   - Approve if all checks pass
   - Request changes with specific, actionable feedback
   - Ask questions if anything is unclear

### Workflow 4: Releasing a Feature

**When to Use**: After feature is merged to main

**Prerequisites**:
- [ ] PR merged to main
- [ ] All tests passing on main
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

**Steps**:

#### For Minor/Patch Releases

```bash
# 1. Update version
# Edit setup.py and pyproject.toml
VERSION = "0.2.0"  # or "0.1.1" for patch

# 2. Commit version bump
git add setup.py pyproject.toml
git commit -m "Bump version to 0.2.0"

# 3. Create tag
git tag -a v0.2.0 -m "Release v0.2.0: [Feature Name]"

# 4. Push
git push origin main --tags

# 5. Build package
python -m build

# 6. Upload to PyPI
twine upload dist/*

# 7. Create GitHub release
# Go to GitHub → Releases → Create new release
# Tag: v0.2.0
# Title: "v0.2.0: [Feature Name]"
# Description: Copy from CHANGELOG.md
```

#### For Major Releases (Breaking Changes)

```bash
# 1. Create beta release first
VERSION = "2.0.0b1"
# ... build and upload to TestPyPI

# 2. Beta testing period (minimum 2 weeks)
# Announce beta, gather feedback

# 3. Fix any issues found

# 4. Final release
VERSION = "2.0.0"
# ... follow normal release process

# 5. Create migration guide
# Document in docs/migration-v2.md
```

## Common Scenarios

### Scenario 1: Fixing a Bug

**Quick Process**:

1. **Create Issue** (if not exists)
   - Describe bug with reproduction steps
   - Include expected vs actual behavior

2. **Create Branch**
   ```bash
   git checkout -b fix/bug-description
   ```

3. **Write Failing Test**
   ```python
   def test_bug_reproduction():
       """Test that reproduces the bug."""
       # This should fail initially
       assert buggy_function() == expected_result
   ```

4. **Fix Bug**
   - Implement fix
   - Ensure test passes

5. **Create PR**
   - Title: "Fix: [Bug description]"
   - Reference issue number

### Scenario 2: Updating Documentation Only

**Quick Process**:

1. **Create Branch**
   ```bash
   git checkout -b docs/update-description
   ```

2. **Make Changes**
   - Update README.md, docstrings, etc.

3. **Verify**
   - Check markdown renders correctly
   - Verify code examples work

4. **Create PR**
   - Title: "Docs: [Description]"
   - No spec/plan needed for docs-only changes

### Scenario 3: Refactoring Code

**Process**:

1. **Ensure Tests Exist**
   - Verify comprehensive test coverage
   - All tests passing

2. **Create Branch**
   ```bash
   git checkout -b refactor/module-name
   ```

3. **Refactor**
   - Make changes
   - Keep tests passing throughout

4. **Verify**
   - All tests still pass
   - Coverage maintained
   - Performance not regressed

5. **Create PR**
   - Title: "Refactor: [Description]"
   - Explain why refactoring improves code

## Troubleshooting

### Tests Failing

```bash
# Run specific test with verbose output
pytest tests/test_file.py::test_name -vv

# Run with debugger
pytest tests/test_file.py::test_name --pdb

# Check coverage for specific file
pytest --cov=django_odata.module --cov-report=term-missing
```

### Coverage Below 90%

```bash
# Generate HTML coverage report
pytest --cov=django_odata --cov-report=html

# Open htmlcov/index.html in browser
# Identify uncovered lines
# Add tests for uncovered code
```

### Linting Errors

```bash
# Auto-fix formatting
ruff format django_odata/ tests/
ruff check --fix django_odata/ tests/

# Check remaining issues
flake8 django_odata/ tests/

# Fix manually or add # noqa comments if justified
```

### Type Checking Errors

```bash
# Run mypy with verbose output
mypy django_odata/ --show-error-codes

# Add type hints or type: ignore comments
# Prefer fixing over ignoring
```

### Merge Conflicts

```bash
# Update from main
git checkout main
git pull origin main
git checkout NNN-feature-name
git merge main

# Resolve conflicts
# Edit conflicted files
git add .
git commit -m "Merge main and resolve conflicts"
```

## Best Practices

### Writing Good Specs

✅ **Do**:
- Start with user value
- Make stories independently testable
- Use measurable success criteria
- Identify edge cases upfront
- Get feedback early

❌ **Don't**:
- Write implementation details in spec
- Leave placeholders unfilled
- Skip edge cases
- Make assumptions without validation

### Writing Good Plans

✅ **Do**:
- Break work into small tasks
- Estimate realistically
- Identify dependencies
- Document risks
- Include acceptance criteria

❌ **Don't**:
- Create tasks too large (>1 day)
- Ignore dependencies
- Skip risk assessment
- Leave tasks vague

### Writing Good Code

✅ **Do**:
- Write tests first (TDD)
- Use descriptive names
- Add type hints
- Document public APIs
- Keep functions small

❌ **Don't**:
- Skip tests
- Use magic numbers
- Leave code uncommented
- Create god classes
- Ignore linting

### Writing Good Commits

✅ **Do**:
```bash
git commit -m "[SPEC-NNN] Add user authentication

- Implement JWT token generation
- Add login/logout endpoints
- Include comprehensive tests

Relates to: .specify/specs/NNN-auth/spec.md"
```

❌ **Don't**:
```bash
git commit -m "fix stuff"
git commit -m "wip"
git commit -m "more changes"
```

## Quick Reference

### Essential Commands

```bash
# Create feature
.specify/scripts/bash/create-new-feature.sh "Description"

# Create plan
.specify/scripts/bash/setup-plan.sh

# Run tests
pytest --cov=django_odata

# Format code
ruff format django_odata/ tests/

# Lint
flake8 django_odata/ tests/

# Type check
mypy django_odata/
```

### File Locations

- **Constitution**: `.specify/memory/constitution.md`
- **Project Config**: `speckit.specify.md`
- **Workflow Plan**: `speckit.plan.md`
- **Specs**: `.specify/specs/NNN-feature-name/spec.md`
- **Plans**: `.specify/plans/NNN-feature-name.md`
- **Templates**: `.specify/templates/*.md`

### Quality Gates

- ✅ All tests pass (100%)
- ✅ Coverage ≥90%
- ✅ Ruff formatting
- ✅ Ruff linting
- ✅ mypy type checking
- ✅ Documentation updated

---

**Maintained by**: Alexandre Busquets (@alexandre-fundcraft)  
**Last Updated**: 2025-10-29  
**Questions?**: Create an issue or contact maintainer