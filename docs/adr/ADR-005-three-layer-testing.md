# ADR-005: Three-Layer Testing Strategy

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

gepa-adk has multiple testing concerns:

1. **Protocol compliance**: Do adapters correctly implement port interfaces?
2. **Business logic**: Does the evolution engine work correctly in isolation?
3. **End-to-end**: Does evolution actually improve agents with real ADK/LLM calls?

We need a testing strategy that balances:
- Fast feedback during development
- Confidence that real integrations work
- Maintainable test suite

## Decision

Adopt a **three-layer testing strategy** aligned with hexagonal architecture:

```
┌─────────────────────────────────────────────────────────┐
│ Contract Tests (tests/contracts/)                       │
│ • Verify protocols are correctly defined                │
│ • Ensure adapters implement ports                       │
│ • Mock ADK for speed                                    │
│ • Run on every commit                                   │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ Integration Tests (tests/integration/)                  │
│ • End-to-end evolution with real ADK agents             │
│ • Real LLM calls (marked @pytest.mark.slow)             │
│ • Verify async concurrency works                        │
│ • Run in CI, skip locally by default                    │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ Unit Tests (tests/unit/)                                │
│ • Engine logic with mock adapter                        │
│ • State guard, parsing utilities                        │
│ • No I/O, fastest execution                             │
│ • Run on every save (watch mode)                        │
└─────────────────────────────────────────────────────────┘
```

### Test Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures and test utilities
├── contracts/
│   ├── test_adapter_protocol.py   # AsyncGEPAAdapter compliance
│   ├── test_scorer_protocol.py    # Scorer compliance
│   └── test_agent_provider_protocol.py
├── integration/
│   ├── conftest.py                # Real ADK fixtures
│   ├── test_adk_evolution.py      # End-to-end evolution
│   ├── test_concurrent_evaluation.py
│   └── test_multi_agent.py
└── unit/
    ├── test_engine.py             # AsyncGEPAEngine
    ├── test_proposer.py           # Mutation proposer
    ├── test_state_guard.py        # State key preservation
    └── test_parsing.py            # JSON/YAML utilities
```

### Layer Details

#### Contract Tests

Verify that adapters implement port protocols correctly:

```python
# tests/contracts/test_adapter_protocol.py
from typing import runtime_checkable
from gepa_adk.ports import AsyncGEPAAdapter
from gepa_adk.adapters import ADKAdapter

def test_adk_adapter_implements_protocol():
    """ADKAdapter must implement AsyncGEPAAdapter protocol."""
    # Note: Actually instantiating requires mocked dependencies
    assert hasattr(ADKAdapter, 'evaluate')
    assert hasattr(ADKAdapter, 'make_reflective_dataset')
    assert hasattr(ADKAdapter, 'propose_new_texts')

def test_protocol_methods_are_async():
    """All adapter methods must be coroutines."""
    import inspect
    assert inspect.iscoroutinefunction(ADKAdapter.evaluate)
    assert inspect.iscoroutinefunction(ADKAdapter.make_reflective_dataset)
    assert inspect.iscoroutinefunction(ADKAdapter.propose_new_texts)
```

#### Unit Tests

Test core logic with mock adapters (no external dependencies):

```python
# tests/unit/test_engine.py
import pytest
from pytest_mock import MockerFixture
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.domain.models import EvaluationBatch

@pytest.fixture
def mock_adapter(mocker: MockerFixture):
    """Mock adapter for unit tests - no ADK dependency."""
    adapter = mocker.AsyncMock()
    adapter.evaluate.return_value = EvaluationBatch(
        outputs=["output1", "output2"],
        scores=[0.8, 0.9],
        trajectories=[{}, {}],
    )
    adapter.propose_new_texts.return_value = {"instruction": "improved"}
    return adapter

@pytest.mark.asyncio
async def test_engine_runs_evolution_loop(mock_adapter):
    """Engine executes evaluation → proposal → acceptance loop."""
    engine = AsyncGEPAEngine(adapter=mock_adapter, max_iterations=3)
    state = await engine.run()

    assert mock_adapter.evaluate.call_count >= 1
    assert state.iterations_completed > 0

@pytest.mark.asyncio
async def test_engine_accepts_improved_candidate(mock_adapter, mocker: MockerFixture):
    """Engine accepts candidates with higher scores."""
    mock_adapter.evaluate.side_effect = [
        EvaluationBatch(outputs=["o"], scores=[0.5], trajectories=[{}]),
        EvaluationBatch(outputs=["o"], scores=[0.8], trajectories=[{}]),
    ]

    engine = AsyncGEPAEngine(adapter=mock_adapter, max_iterations=2)
    state = await engine.run()

    assert state.best_score >= 0.5
```

### Shared Test Utilities (tests/conftest.py)

The root `conftest.py` provides reusable test utilities:

```python
# MockScorer: Implements the Scorer protocol for testing
from tests.conftest import MockScorer

def test_with_scorer():
    scorer = MockScorer(score_value=0.9)  # Custom score value
    score, metadata = scorer.score("input", "output", "expected")
    assert score == 0.9
    assert scorer.score_calls == [("input", "output", "expected")]  # Tracks calls

# MockExecutor: Implements AgentExecutorProtocol for testing
from tests.conftest import MockExecutor

def test_with_executor():
    executor = MockExecutor()
    # executor.execute_count and executor.calls track usage
```

**Fixtures provided:**
- `mock_scorer_factory` - Factory for creating MockScorer with custom scores
- `mock_executor` - Fresh MockExecutor instance per test
- `mock_proposer` - Mock AsyncReflectiveMutationProposer
- `trainset_samples`, `valset_samples` - Standard test datasets
- `deterministic_scores`, `deterministic_score_batch` - Predictable score sequences

#### Integration Tests

Test real evolution with ADK agents (slow, requires API keys):

```python
# tests/integration/test_adk_evolution.py
import pytest
from google.adk.agents import LlmAgent
from gepa_adk import evolve

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.asyncio
async def test_evolve_improves_instruction():
    """End-to-end: evolution improves agent instruction."""
    agent = LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="Answer the question.",
    )
    critic = LlmAgent(
        name="critic",
        model="gemini-2.5-flash",
        instruction="Rate the answer quality from 0 to 1.",
        output_schema={
            "type": "object",
            "properties": {"score": {"type": "number"}}
        }
    )

    result = await evolve(
        agent=agent,
        trainset=[{"input": "What is 2+2?", "expected": "4"}],
        critic=critic,
        max_iterations=5,
    )

    assert result.final_score >= result.original_score
    assert result.evolved_instruction != agent.instruction
```

### Test Markers

Configure pytest markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Fast, isolated unit tests (no I/O)",
    "contract: Interface compliance tests",
    "integration: Real ADK/LLM tests (requires API keys)",
    "slow: Tests taking >10s (LLM calls)",
]
# Skip slow/integration by default for fast local development
addopts = "-m 'not slow and not integration'"
asyncio_mode = "auto"
```

### Running Tests

```bash
# Fast feedback (unit + contract only)
uv run pytest

# All tests including integration
uv run pytest -m ""

# Only integration tests
uv run pytest -m integration

# With coverage
uv run pytest --cov=src --cov-report=term-missing
```

### TDD Approach

Follow Test-Driven Development:

1. **Write failing test** for new feature
2. **Implement minimum code** to pass
3. **Refactor** while keeping tests green

```python
# Example TDD cycle for state guard

# Step 1: Write failing test
def test_state_guard_repairs_missing_token():
    guard = StateGuard(repair_missing=True)
    original = "Use {session_data} in your response"
    mutated = "Use the data in your response"  # Token removed

    repaired = guard.repair(mutated, original)

    assert "{session_data}" in repaired

# Step 2: Implement StateGuard.repair()
# Step 3: Refactor if needed
```

## Consequences

### Positive

- **Fast feedback**: Unit tests run in <1 second
- **Confidence**: Integration tests verify real behavior
- **Clear separation**: Each layer tests different concerns
- **CI-friendly**: Can run fast tests on every PR, slow tests on merge
- **TDD support**: Easy to write tests first with mock adapters

### Negative

- **Mock maintenance**: Mock adapters must stay in sync with real ones
- **Integration test cost**: Real LLM calls cost money and time
- **Complexity**: Three layers require understanding of when to use each

### Neutral

- **Coverage targets**: Aim for >90% on unit tests, lower acceptable for integration
- **API key management**: Integration tests need secure credential handling

## Alternatives Considered

### 1. Single Test Layer

```
tests/
└── test_*.py  # Everything in one place
```

**Rejected**: Mixes fast and slow tests, hard to get quick feedback.

### 2. Two Layers (Unit + Integration)

**Rejected**: Missing contract tests means protocol violations caught late.

### 3. Property-Based Testing (Hypothesis)

```python
@given(st.text(), st.floats(0, 1))
def test_scorer_returns_valid_score(input_text, expected_score): ...
```

**Considered for future**: Good for utility functions, overkill for MVP.

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Test Pyramid (Martin Fowler)](https://martinfowler.com/bliki/TestPyramid.html)
- **ADR-001**: Async-First Architecture (async testing patterns)
- **ADR-002**: Protocol for Interfaces (contract testing)
- **ADR-009**: Exception Hierarchy (exception testing)
- [ADR Index](index.md) - All architectural decisions
