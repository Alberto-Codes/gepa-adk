# Contributing to GEPA-ADK

Thank you for your interest in contributing to GEPA-ADK! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Issue Reporting](#issue-reporting)
- [Release Process](#release-process)

## Code of Conduct

This project follows standard open-source community guidelines. Be respectful, constructive, and collaborative in all interactions.

## Getting Started

### Prerequisites

- **Python 3.12** (strictly required, no other versions supported)
- **uv** package manager (recommended)
- **Git** for version control

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   # Fork via GitHub UI, then clone your fork
   git clone https://github.com/YOUR-USERNAME/gepa-adk.git
   cd gepa-adk
   git remote add upstream https://github.com/Alberto-Codes/gepa-adk.git
   ```

2. **Install dependencies with uv**:
   ```bash
   uv sync --all-extras
   ```

3. **Verify the setup**:
   ```bash
   uv run pytest -m "not api"  # Run tests (excluding API tests)
   uv run ruff check .          # Check code style
   ```

### Project Structure

```
gepa-adk/
├── src/gepa_adk/          # Source code (hexagonal architecture)
│   ├── domain/            # Core domain models and types
│   ├── ports/             # Protocol interfaces
│   ├── adapters/          # External integrations (ADK, LiteLLM)
│   ├── engine/            # Evolution engine logic
│   └── utils/             # Shared utilities
├── tests/                 # Test suite
│   ├── unit/              # Unit tests (fast, isolated)
│   ├── contracts/         # Protocol compliance tests
│   └── integration/       # Integration tests (real ADK/LLM)
├── docs/                  # Documentation source
├── scripts/               # Development and CI scripts
└── examples/              # Usage examples
```

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions/improvements

### Making Changes

1. Sync your fork and create a branch:
   ```bash
   git fetch upstream
   git checkout -b feat/your-feature-name upstream/main
   ```

2. Make your changes, following the code style guidelines below.

3. Run quality checks before committing:
   ```bash
   ./scripts/code_quality_check.sh --all
   ```

4. Commit with conventional commit messages (see [Commit Messages](#commit-messages)).

5. Push to your fork and create a pull request to `upstream/main`:
   ```bash
   git push origin feat/your-feature-name
   # Then open PR via GitHub UI targeting Alberto-Codes/gepa-adk:main
   ```

## Code Style

### Python Guidelines

- **Python 3.12** features are encouraged
- **Line length**: 88 characters (formatter), 100 (linter threshold)
- **Quotes**: Double quotes for strings
- **Imports**: Sorted automatically via ruff/isort

### Linting and Formatting

We use **ruff** for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Type Hints

All public functions and methods must have type annotations:

```python
def process_batch(
    batch: list[dict[str, Any]],
    candidate: dict[str, str],
    *,
    capture_traces: bool = False,
) -> EvaluationBatch:
    """Process a batch of examples."""
    ...
```

### Docstrings

We follow **Google-style docstrings** with strict quality standards:

```python
def evaluate(
    self,
    batch: list[dict[str, Any]],
    candidate: dict[str, str],
) -> EvaluationBatch:
    """Evaluate a batch of examples against a candidate.

    Processes each example through the agent and scores outputs.

    Args:
        batch: List of example dictionaries with 'input' and optional 'expected' keys.
        candidate: Dictionary of prompt components to evaluate.

    Returns:
        EvaluationBatch containing outputs, scores, and optional trajectories.

    Raises:
        ValidationError: If batch format is invalid.

    Examples:
        ```python
        result = await adapter.evaluate(
            batch=[{"input": "Hello", "expected": "Hi"}],
            candidate={"instruction": "Be friendly"},
        )
        ```
    """
```

See [docs/contributing/docstring-templates.md](docs/contributing/docstring-templates.md) for comprehensive templates.

### Architecture Decisions

Follow the architectural patterns defined in our ADRs:

- **ADR-000**: Hexagonal architecture (domain → ports → adapters)
- **ADR-001**: Async-first (all core APIs are `async def`)
- **ADR-002**: Protocol-based interfaces (use `typing.Protocol`)
- **ADR-008**: Structured logging with structlog
- **ADR-009**: Custom exception hierarchy

## Testing

### Test Structure

We follow a **three-layer testing strategy** (ADR-005):

| Layer | Location | Purpose | Speed |
|-------|----------|---------|-------|
| Unit | `tests/unit/` | Isolated logic with mocks | Fast |
| Contract | `tests/contracts/` | Protocol compliance | Fast |
| Integration | `tests/integration/` | Real ADK/LLM calls | Slow |

### Running Tests

```bash
# Default: unit + contract tests (fast)
uv run pytest

# All tests including integration
uv run pytest -m ""

# With coverage
uv run pytest --cov=src --cov-report=term-missing

# Parallel execution
uv run pytest -n auto

# Specific markers
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m slow
```

### Test Markers

Use appropriate markers for your tests:

```python
import pytest

@pytest.mark.unit
def test_simple_logic():
    """Unit test for isolated logic."""
    ...

@pytest.mark.contract
async def test_protocol_compliance():
    """Contract test for interface compliance."""
    ...

@pytest.mark.integration
@pytest.mark.requires_gemini
async def test_with_real_api():
    """Integration test requiring API credentials."""
    ...
```

### Writing Tests

- Use `pytest-asyncio` for async tests (auto mode enabled)
- Use `pytest-mock` for mocking (inject `mocker` fixture)
- Follow existing patterns in the test suite
- Aim for high coverage but prioritize meaningful tests

### Deprecation Warning Handling

We treat all warnings as errors to catch deprecations early. The strategy is configured in `pyproject.toml`:

```toml
filterwarnings = [
    "error",  # Treat all warnings as errors
    # Explicit ignores for third-party issues (each with tracking issue)
    "ignore:...:DeprecationWarning",  # Issue #NNN
]
```

**When CI fails due to a warning:**

1. **Your code?** Fix it immediately - PR cannot merge with warnings.

2. **Third-party dependency?** Add an ignore with a tracking issue:
   ```toml
   # Description of the issue - Issue #NNN
   # Remove when dependency-name >= X.Y.Z
   "ignore:warning message pattern:WarningType",
   ```

3. **Create a tracking issue** using the Tech Debt template:
   - Link to upstream issue if exists
   - Document when it can be removed (version threshold)
   - Add `tech-debt` and `priority:low` labels

**Current tracked warnings:** See `pyproject.toml` filterwarnings section for the full list with issue references.

## Documentation

### Building Documentation

```bash
# Build locally
uv run mkdocs build

# Serve locally with live reload
uv run mkdocs serve
```

### Documentation Standards

- All public APIs must have docstrings
- Use cross-references: `[ClassName][gepa_adk.module.ClassName]`
- Include code examples in docstrings
- Update relevant docs when changing behavior

## Submitting Changes

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

**Examples**:
```
feat(adapter): add support for parallel batch evaluation
fix(engine): handle empty batch gracefully
docs(readme): update installation instructions
refactor(domain): simplify trajectory model
test(adapter): add contract tests for Scorer protocol
```

**Breaking changes**: Add `!` after type and include `BREAKING CHANGE:` in footer:
```
feat(engine)!: remove deprecated evaluate_sync method

BREAKING CHANGE: The synchronous evaluate_sync method has been removed.
Use the async evaluate method instead.
```

### Pull Request Process

1. **Ensure all checks pass**:
   ```bash
   ./scripts/code_quality_check.sh --all
   uv run pytest
   ```

2. **Fill out the [PR template](.github/PULL_REQUEST_TEMPLATE.md)** with:
   - Clear description of changes (why + what)
   - Link to related issues (`Closes #123`)
   - Test command to verify
   - Breaking change notes (if applicable)

3. **PR Checklist**:
   - [ ] Code follows style guidelines
   - [ ] Tests added/updated for changes
   - [ ] Documentation updated
   - [ ] Commit messages follow conventions
   - [ ] All CI checks pass

4. **Review process**:
   - PRs require review before merging
   - Address review feedback promptly
   - Keep PRs focused and reasonably sized

## Issue Reporting

### Choosing the Right Template

We provide several issue templates:

| Template | Use When |
|----------|----------|
| Bug Report | Something isn't working as expected |
| Tech Debt | Code quality, ADR violations, refactoring needs |
| Feature Idea | Quick feature suggestion for triage |
| Feature Request | Detailed feature proposal with implementation |

### Bug Reports

Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Error messages/stack traces

### Feature Requests

Include:
- Problem statement (what are you trying to solve?)
- Proposed solution
- Alternatives considered
- Impact on existing functionality

## Release Process

Releases are automated via [release-please](https://github.com/googleapis/release-please):

1. **Conventional commits** on `main` trigger changelog updates
2. **Release PR** is automatically created/updated
3. **Merging the release PR** creates a GitHub release
4. **CI publishes** to PyPI automatically

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Breaking API changes
- **MINOR** (0.2.0): New features, backwards-compatible
- **PATCH** (0.1.1): Bug fixes, backwards-compatible

Pre-release versions:
- `0.1.0a1` - Alpha (TestPyPI)
- `0.1.0b1` - Beta (TestPyPI)
- `0.1.0rc1` - Release candidate (TestPyPI)

For detailed release instructions, see [docs/contributing/releasing.md](docs/contributing/releasing.md).

## Getting Help

- **Documentation**: https://alberto-codes.github.io/gepa-adk/
- **Issues**: https://github.com/Alberto-Codes/gepa-adk/issues
- **Discussions**: Use GitHub Issues for questions

Thank you for contributing to GEPA-ADK!
