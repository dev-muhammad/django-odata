# SPEC-004: Migrate to UV for Dependency Management

**Status**: Draft  
**Created**: 2025-10-30  
**Author**: Kilo Code  
**Priority**: Medium

## Overview

Migrate the project from manual Python venv creation to using [uv](https://github.com/astral-sh/uv) for dependency management. This will simplify the development setup, improve dependency resolution speed, and provide better reproducibility.

## Motivation

### Current Issues
1. **Manual Setup**: Developers must manually create and activate virtual environments
2. **Slow Installation**: pip can be slow for dependency resolution and installation
3. **Inconsistent Environments**: No lock file ensures exact dependency versions
4. **Complex Makefile**: Multiple steps required for environment setup

### Benefits of UV
1. **Speed**: 10-100x faster than pip for dependency resolution
2. **Automatic venv**: Creates and manages virtual environments automatically
3. **Lock File**: Generates `uv.lock` for reproducible builds
4. **Simplified Workflow**: Single command (`uv sync`) to set up environment
5. **Better UX**: Modern CLI with clear progress indicators

## Goals

1. Replace manual `python -m venv` with `uv sync`
2. Update all Makefile commands to use `uv run`
3. Configure `pyproject.toml` for uv compatibility
4. Update documentation to reflect new workflow
5. Maintain backward compatibility where possible

## Non-Goals

- Changing the package build system (still using setuptools)
- Modifying the package distribution process
- Changing the testing framework or tools

## Specification

### 1. Makefile Changes

#### Remove
- `venv` target (manual venv creation)
- `venv-activate` target (activation instructions)

#### Add
- `sync` target: Run `uv sync --group dev` to sync dependencies

#### Update
- `install`: Use `uv pip install -e .`
- `install-dev`: Use `uv sync --group dev && uv pip install -e .`
- All test commands: Prefix with `uv run`
- All code quality commands: Prefix with `uv run`
- All example commands: Prefix with `uv run`

### 2. pyproject.toml Changes

Add `[project]` section with:
- Project metadata (name, version, description)
- Python version requirement
- Core dependencies
- Optional dependencies (dev group)

Keep existing:
- `[tool.black]` configuration
- `[tool.isort]` configuration
- `[tool.pytest.ini_options]` configuration
- `[build-system]` configuration

### 3. Documentation Updates

Update `speckit.specify.md`:
- Replace venv creation instructions with `uv sync`
- Update all command examples to use `uv run`
- Add Makefile shortcuts for common tasks

### 4. Quick Start Workflow

**Before** (3 steps):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

**After** (1 step):
```bash
uv sync --group dev
```

Or using Makefile:
```bash
make sync
```

## Implementation Plan

### Phase 1: Configuration (30 minutes)
1. Update `pyproject.toml` with `[project]` section
2. Add project metadata and dependencies
3. Configure optional dependencies

### Phase 2: Makefile Updates (30 minutes)
1. Remove venv-related targets
2. Add `sync` target
3. Update all commands to use `uv run`
4. Test all Makefile targets

### Phase 3: Documentation (30 minutes)
1. Update `speckit.specify.md`
2. Update quick start instructions
3. Add troubleshooting section

### Phase 4: Testing (30 minutes)
1. Test `make sync` on clean environment
2. Test all Makefile targets
3. Verify tests still pass
4. Verify example app still works

**Total Estimated Time**: 2 hours

## Testing Strategy

### Manual Testing
1. Remove existing `.venv` directory
2. Run `make sync`
3. Verify dependencies installed correctly
4. Run `make test` - all tests should pass
5. Run `make example-run` - server should start
6. Run `make format` and `make lint` - should work

### Verification Checklist
- [ ] `uv.lock` file generated
- [ ] Virtual environment created in `.venv`
- [ ] All dependencies installed
- [ ] Tests pass (257 tests)
- [ ] Example app runs
- [ ] Code quality tools work
- [ ] Documentation updated

## Migration Guide

### For Developers

**If you have an existing venv:**
```bash
# Remove old venv
rm -rf .venv

# Sync with uv
make sync

# Continue development as normal
make test
```

**For new developers:**
```bash
# Clone repo
git clone <repo-url>
cd fc-django-odata

# One command setup
make sync

# Start developing
make test
make example-run
```

### For CI/CD

Update CI workflows to:
1. Install uv: `pip install uv`
2. Sync dependencies: `uv sync --group dev`
3. Run tests: `uv run pytest`

## Risks and Mitigations

### Risk 1: UV Not Installed
**Mitigation**: Add installation instructions to README and error message in Makefile

### Risk 2: Compatibility Issues
**Mitigation**: Keep `requirements.txt` and `requirements-dev.txt` as fallback

### Risk 3: Lock File Conflicts
**Mitigation**: Add `uv.lock` to `.gitignore` initially, commit later when stable

### Risk 4: CI/CD Breakage
**Mitigation**: Test in CI before merging, provide rollback plan

## Success Criteria

1. ✅ Developers can set up environment with single command
2. ✅ All tests pass with uv-managed environment
3. ✅ Example application runs correctly
4. ✅ Documentation is clear and accurate
5. ✅ CI/CD pipelines work with uv
6. ✅ Development workflow is faster than before

## Future Enhancements

1. Use uv for package building (`uv build`)
2. Use uv for publishing (`uv publish`)
3. Explore uv's workspace features for monorepo support
4. Consider uv's script running features

## References

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV vs pip Benchmarks](https://github.com/astral-sh/uv#benchmarks)
- [pyproject.toml Specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/)