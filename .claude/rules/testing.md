---
globs: ["tests/**/*.py", "**/conftest.py"]
---

# Testing Conventions (gepa-adk)

## Test Runner
- `uv run pytest` — never bare `pytest`
- `asyncio_mode = "auto"` — async tests work without `@pytest.mark.asyncio`, but the explicit marker is acceptable for clarity in mixed sync/async test classes
- API tests excluded by default (`-m 'not api'`); run with `uv run pytest -m api`

## Test Tiers (markers)

| Marker | Directory | Purpose |
|---|---|---|
| `unit` | `tests/unit/` | Fast, isolated, no I/O — single class/function in isolation |
| `contract` | `tests/contracts/` | Protocol compliance via `isinstance()` + behavioral checks |
| `integration` | `tests/integration/` | Cross-layer wiring with real domain + real engine + mock externals |
| `api` | anywhere | Real LLM calls — requires `requires_ollama` or `requires_gemini` marker too |

Every test file sets `pytestmark = pytest.mark.<tier>` at module level.

**When to use which tier:**
- Testing one class/function with all dependencies mocked → `unit`
- Testing wiring between two or more real implementations → `integration`
- Testing that an implementation satisfies a Protocol → `contract`
- Hitting a real LLM endpoint → `api`

## Contract Tests
- Required for every `typing.Protocol` in `ports/` — a PR adding a Protocol without a contract test should fail review
- Three-class template per protocol (see `test_stopper_protocol.py`):
  1. `TestXxxProtocolRuntimeCheckable` — positive compliance (`isinstance` checks)
  2. `TestXxxProtocolBehavior` — behavioral expectations (return types, state transitions)
  3. `TestXxxProtocolNonCompliance` — negative cases (missing methods → `not isinstance`)
- Document `runtime_checkable` limitations (signature not checked at runtime)
- One test file per Protocol (not per implementation)

## Integration Test Boundaries
- Use real domain objects + real engine + mock adapters/external services
- Never mock the thing you're integrating — that defeats the purpose
- One test file per feature-slice or cross-cutting concern

## Fixtures

### Location rules
- `tests/conftest.py` (root) and `tests/fixtures/` — shared across tiers
- `tests/<tier>/conftest.py` or `tests/<tier>/<subpackage>/conftest.py` — tier-specific
- If a fixture is used by exactly one test file, keep it in that file — conftest is for shared fixtures only

### Existing mocks — check before creating
- `MockScorer` / `mock_scorer_factory` — root conftest (scoring paths)
- `MockAdapter` / `create_mock_adapter()` — `tests/fixtures/adapters.py` (adapter paths)
- `MockExecutor` — root conftest (execution paths)
- Prefer factory fixtures (`mock_scorer_factory`, `create_mock_adapter()`) over bare class instantiation
- **Never duplicate an existing mock.** Search `tests/conftest.py` and `tests/fixtures/` first.

### Scope
- Default: `scope="function"` — each test gets isolated state
- Use `scope="session"` only for expensive shared setup (e.g., client cleanup, connection pools)
- Never use session scope for mutable fixtures

## Mocking
- `pytest-mock` (`mocker` fixture) for patching — not raw `unittest.mock.patch`
- **Key Rule**: Patch where the object is USED, not where it's DEFINED
- Use `autospec=True` to respect method signatures
- `AsyncMock` for async methods, `MagicMock` for sync
- Mock at the boundary (ports), not deep internals
- Prefer real objects with in-memory adapters over mocks when testing hex architecture
- Accessing private attributes (e.g., `stopper._stop_requested = True`) is a last resort for signal/OS interaction tests — not a general pattern

## Async Tests
- Async tests just need `async def test_...` — auto mode handles the rest
- For concurrent test scenarios use `asyncio.gather()` directly in the test
- Scope: `asyncio_default_fixture_loop_scope = "function"` — each test gets its own loop
- Never share mutable state between async test cases — each test creates its own adapter/engine/config

## Test Data
- All test data must be deterministic and predictable — use fixed values, not random generators
- Use existing fixtures (`trainset_samples`, `valset_samples`, `deterministic_scores`) for evolution test data
- For file I/O tests, use `tmp_path` — never write to the repo tree

## API Test Resilience
- API-tier tests must have explicit timeouts
- Assert on response structure, not exact LLM content (LLM output is non-deterministic)
- If an API test starts flaking, triage immediately — flakiness is critical tech debt

## Naming Conventions
- Test classes: `class TestXxx<Aspect>:` — e.g., `TestSignalStopperBehavior`, `TestSignalStopperEdgeCases`
- Test methods: encode the scenario — `test_<unit>_<scenario>_<expected>` or plain English describing behavior
- Mirror source structure: `src/gepa_adk/adapters/stoppers/` → `tests/unit/adapters/stoppers/`
- One test file per source module (unit), per Protocol (contract), per feature-slice (integration)

## Assertions
- Use `assert` directly — no `self.assertEqual` or custom assert helpers
- `pytest.raises` for exceptions, `pytest.approx` for floats
- Protocol compliance: `assert isinstance(obj, Protocol)` and `assert not isinstance(bad_obj, Protocol)`

## Coverage Philosophy
- Contract tests ensure protocol compliance; unit tests cover business logic; integration tests cover wiring
- Chase behavioral coverage, not line-count percentages
- Don't test: private methods, internal dataclass field ordering, import structure — test behavior through the public API

## Warnings
- `filterwarnings = ["error"]` in pyproject.toml — new warnings break CI
- Third-party warning ignores require a `filterwarnings` entry in pyproject.toml with a tracking issue comment
- When adding a new test dependency, check if it emits warnings and add entries proactively
