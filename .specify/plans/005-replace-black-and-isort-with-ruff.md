# Plan: Replace Black and Isort with Ruff

This plan outlines the steps to implement **SPECKIT-005**, which involves replacing `black` and `isort` with `ruff` for code formatting and linting.

## 1. Revert Previous Changes

Before applying the new changes, I will revert any previous modifications made to the following files to ensure a clean state:
- `pyproject.toml`
- `requirements-dev.txt`
- `Makefile`

## 2. Update Configuration Files

### `pyproject.toml`
- **Remove `black` and `isort` dependencies**: Delete `black>=21.0` and `isort>=5.0` from the `[project.optional-dependencies]` and `[dependency-groups]` sections.
- **Add `ruff` dependency**: Add `ruff>=0.5.5` to the `[project.optional-dependencies]` and `[dependency-groups]` sections.
- **Remove `black` and `isort` configurations**: Delete the `[tool.black]` and `[tool.isort]` sections.
- **Add `ruff` configuration**: Add a new `[tool.ruff]` section to configure the linter and formatter.

### `requirements-dev.txt`
- **Remove `black` and `isort`**: Delete the lines for `black` and `isort`.
- **Add `ruff`**: Add a line for `ruff>=0.5.5`.

### `Makefile`
- **Update `lint` command**: Modify the `lint` target to replace the `flake8` command with `ruff check`.
- **Update `format` command**: Modify the `format` target to replace the `black` and `isort` commands with `ruff format`.
- **Update help text**: Adjust the descriptions for the `lint` and `format` commands in the `help` target.

## 3. Sync Dependencies

- Run the `make sync` command to update the development environment. This will remove `black` and `isort` and install `ruff`.

## 4. Create a TODO list

- Create a `TODO.md` file to track the implementation of this plan.

I will now ask for your approval before proceeding with the implementation.