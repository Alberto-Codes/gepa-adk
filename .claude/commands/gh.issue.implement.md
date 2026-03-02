---
description: Implement a GitHub issue for gepa-adk
---
Please analyze and implement the GitHub issue: $ARGUMENTS.

## Project Context
- **Architecture**: Hexagonal (domain → ports → adapters)
- **Package Manager**: `uv`
- **Python Version**: 3.12 (strictly required)
- **Main Branch**: `develop`
- **Tasks File**: `$ARGUMENTS_TASKS.md` (at repository root)

## Style Guidelines

Follow project coding standards:
- **Python Style**: `.github/instructions/python.instructions.md` (Google Python Style Guide)
- **Test Style**: `.github/instructions/pytest.instructions.md` (pytest best practices)

Key requirements:
- Google-style docstrings in `src/` files
- Type hints on all public functions using modern syntax (`list[str]` not `List[str]`)
- 88-char line length (formatter), 100-char max (linter)
- Test naming: `test_<what>_<condition>_<expected_result>`
- One assertion per test (recommended)
- Use `mocker` fixture from pytest-mock for mocking

## Implementation Steps

### 1. Get Issue Details
```bash
gh issue view $ARGUMENTS
```
- Understand the problem, feature request, or enhancement
- Note any labels, linked issues, or acceptance criteria

### 2. Create Feature Branch
```bash
git checkout develop && git pull origin develop
git checkout -b <type>/$ARGUMENTS-short-description
```
Branch types: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`

### 3. Analyze the Codebase
Review the hexagonal architecture structure:
- `src/gepa_adk/domain/` - Core domain models and types
- `src/gepa_adk/ports/` - Protocol interfaces (use `typing.Protocol`)
- `src/gepa_adk/adapters/` - External integrations (ADK, LiteLLM)
- `src/gepa_adk/engine/` - Evolution engine logic
- `src/gepa_adk/utils/` - Shared utilities

Check for related tests in:
- `tests/unit/` - Isolated logic with mocks (fast)
- `tests/contracts/` - Protocol compliance tests (fast)
- `tests/integration/` - Real ADK/LLM calls (slow)

### 4. Generate Tasks File

Create `$ARGUMENTS_TASKS.md` at repository root using the template structure from `.specify/templates/tasks-template.md`.

The tasks file should include:
- **Header**: `# Tasks: Issue #$ARGUMENTS - [Issue Title]`
- **Phase 1: Setup** - Any project setup needed
- **Phase 2: Foundational** - Core infrastructure that must be complete first
- **Phase 3+: Implementation** - Actual implementation tasks organized by logical grouping
- **Phase N-1: Testing** - Unit tests, contract tests, integration tests
- **Phase N: Verification** - Code quality checks (see below)

Task format: `- [ ] T001 [P] Description with exact file path`
- `[P]` = Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions (e.g., `src/gepa_adk/adapters/foo.py`)

**Verification Phase Tasks** (always include):
```markdown
## Phase N: Verification

**Purpose**: Ensure all quality checks pass

- [ ] TXXX Run `./scripts/code_quality_check.sh --files <modified_files>` - all 7 checks pass
- [ ] TXXX Verify tests pass with `uv run pytest`
```

### 5. Implement the Changes

Work through each task in `$ARGUMENTS_TASKS.md`:
- **Mark task in progress**: Update the task you're working on
- **Implement**: Follow Python 3.12 conventions and existing patterns
- **Mark task complete**: Change `- [ ]` to `- [x]` when done
- **Commit**: After each task or logical group

Code standards:
- Use structlog for logging, google-adk patterns for agents
- All public functions must have type annotations
- Use Google-style docstrings in `src/` files
- Follow ADRs: async-first (`async def`), Protocol-based interfaces

### 6. Write and Run Tests

Follow pytest best practices from `.github/instructions/pytest.instructions.md`:
- Test file naming: `test_*.py` mirroring source structure
- Test function naming: `test_<what>_<condition>_<expected_result>`
- One assertion per test (recommended)
- Use fixtures for setup/teardown with `yield`
- Use `mocker` fixture for mocking (patch where used, not defined)

```bash
# Run unit + contract tests (default, fast)
uv run pytest

# Run specific test file
uv run pytest tests/unit/path/to/test_file.py

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing
```

Use appropriate markers: `@pytest.mark.unit`, `@pytest.mark.contract`, `@pytest.mark.integration`

Mark test tasks complete in `$ARGUMENTS_TASKS.md` as tests pass.

### 7. Code Quality Checks

Run the comprehensive quality check script (7 checks):
```bash
# Check modified files
./scripts/code_quality_check.sh --files <file1.py> <file2.py>

# Or check all files
./scripts/code_quality_check.sh --all
```

The script runs these checks:
1. **Linting** - `ruff check` (includes import sorting, docstring style)
2. **Formatting** - `ruff format`
3. **Docstring freshness** - Detects stale docstrings via git blame
4. **Docstring enrichment** - Audits for missing sections
5. **Docs coverage** - Detects missing `__init__.py` exports
6. **Griffe warnings** - Missing parameter types in docstrings
7. **Type checking** - `ty check`

Fix any issues before proceeding. Reference:
- ADR: `docs/adr/ADR-017-DOCSTRING-QUALITY.md`
- Templates: `docs/contributing/docstring-templates.md`

