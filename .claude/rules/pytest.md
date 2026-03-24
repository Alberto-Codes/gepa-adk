---
globs: ["**/*test*.py", "**/test_*.py", "**/tests/**/*.py", "**/conftest.py"]
---

# Pytest Best Practices

## Test File and Function Naming

### File Naming Conventions
- **MUST** use `test_*.py` or `*_test.py` pattern for pytest to discover tests
- Place test files in dedicated `tests/` directory at project root
- Mirror application structure in test directory
- Example: Testing `src/gepa_adk/adapters/stoppers/signal.py` -> `tests/unit/adapters/stoppers/test_signal.py`

### Test Function Naming
- **MUST** prefix test functions with `test_`
- Use descriptive names following pattern: `test_<what>_<condition>_<expected_result>`
- Examples:
  - `test_evolution_engine_stops_at_max_generations()`
  - `test_pareto_frontier_rejects_dominated_candidates()`
  - `test_reflection_agent_extracts_feedback()`
- Avoid generic names like `test1()` or `test_function()`

### Test Class Naming
- **MUST** prefix test classes with `Test` (capital T)
- Class methods **MUST** start with `test_`
- No `__init__` method in test classes
- Use classes to group related tests for a specific feature or module

## Test Organization and Structure

### Testing Pyramid
- **MOST tests**: Unit tests (fast, isolated — test domain logic, ports, adapters in isolation)
- **FEWER tests**: Integration tests (cross-layer wiring with real domain + engine)
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.contract`, `@pytest.mark.integration`, `@pytest.mark.api`

### Organization Principles
- Mirror application code structure in test directories
- Separate tests by type (unit/contract/integration) using subdirectories
- Each test should verify ONE specific aspect of code
- Keep tests independent - no execution order dependencies
- Tests should be fast, deterministic, and readable

## Fixtures Best Practices

### Fixture Scopes
- **function** (default): Created/destroyed for each test - maximum isolation
- **class**: Shared across all methods in a test class
- **module**: Shared across all tests in a module - for expensive setup
- **session**: Shared across entire test session - for very expensive operations (never for mutable fixtures)

### conftest.py Usage
- Place shared fixtures in `conftest.py` for automatic discovery (no imports needed)
- Root-level `tests/conftest.py` for global fixtures
- Tier-specific `conftest.py` for tier-specific fixtures

### Fixture Anti-Patterns to Avoid
- Overloaded fixtures with too many responsibilities
- Hardcoded values (use factory pattern instead)
- Global state leakage without proper cleanup
- Deep fixture dependency chains
- Duplicating fixtures across test files (use conftest.py)

## Assertions and Testing Patterns

### Assertion Principles
- Use plain `assert` statements - pytest provides detailed introspection
- Test public interfaces, not private methods or implementation details

### Mocking and Patching
- **Key Rule**: Patch where the object is USED, not where it's DEFINED
- Use `autospec=True` to respect method signatures
- Mock external dependencies (LLM adapters, file I/O), not internal logic
- Prefer real objects with in-memory adapters over mocks when testing hex architecture

## Quick Reference

```bash
uv run pytest                     # All tests (excludes api by default)
uv run pytest tests/unit          # Unit tests only
uv run pytest tests/contracts     # Contract tests only
uv run pytest -k "pareto"        # Tests matching keyword
uv run pytest -m "not slow"      # Exclude slow tests
uv run pytest -m api              # Run API tests (real LLM calls)
uv run pytest --lf                # Run last failed tests
uv run pytest -x                  # Stop on first failure
```
