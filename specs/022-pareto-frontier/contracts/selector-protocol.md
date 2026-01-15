# Contract: CandidateSelectorProtocol

**Feature**: 022-pareto-frontier
**Date**: 2026-01-14
**Type**: Python Protocol (PEP 544)

## Overview

Defines the async interface for candidate selection strategies used during evolution to determine which candidate should be mutated next.

---

## Protocol Definition

```python
from typing import Protocol, runtime_checkable
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.exceptions import NoCandidateAvailableError

@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    """Async protocol for candidate selection strategies.

    Implementations determine which candidate from the current evolution
    state should be selected for the next mutation proposal.

    Examples:
        Using a Pareto selector:

        ```python
        from gepa_adk.adapters import ParetoCandidateSelector
        import random

        selector = ParetoCandidateSelector(rng=random.Random(42))

        async def run_selection(state: ParetoState) -> int:
            return await selector.select_candidate(state)
        ```

    Note:
        All implementations must handle the edge case where state has
        only one candidate (return index 0).
    """

    async def select_candidate(self, state: ParetoState) -> int:
        """Select a candidate index for mutation.

        Args:
            state: Current evolution state containing candidates,
                   per-example scores, and Pareto frontier.

        Returns:
            Index of the selected candidate in state.candidates.

        Raises:
            NoCandidateAvailableError: If state has no candidates.

        Note:
            The returned index must be valid for state.candidates.
            Implementations should be deterministic given the same
            state and RNG seed.
        """
        ...
```

---

## Contract Guarantees

### Preconditions
| Condition | Description |
|-----------|-------------|
| `len(state.candidates) >= 1` | State must have at least one candidate |
| `state.frontier is not None` | Frontier must be initialized |

### Postconditions
| Condition | Description |
|-----------|-------------|
| `0 <= result < len(state.candidates)` | Returned index is valid |
| Deterministic | Same state + RNG seed → same result |

### Invariants
| Invariant | Description |
|-----------|-------------|
| No state mutation | select_candidate() must not modify state |
| Finite execution | select_candidate() must complete in bounded time |

---

## Implementation Requirements

### ParetoCandidateSelector
```python
class ParetoCandidateSelector:
    """Samples from Pareto front proportional to example leadership.

    Candidates that lead on more validation examples have higher
    selection probability, promoting diversity.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        """Initialize with optional RNG for reproducibility."""
        ...

    async def select_candidate(self, state: ParetoState) -> int:
        """Select from Pareto front with weighted sampling."""
        ...
```

### CurrentBestCandidateSelector
```python
class CurrentBestCandidateSelector:
    """Always returns candidate with highest average score.

    This is the greedy baseline selector, equivalent to current
    gepa-adk behavior before Pareto integration.
    """

    async def select_candidate(self, state: ParetoState) -> int:
        """Return best_average_idx from state."""
        ...
```

### EpsilonGreedyCandidateSelector
```python
class EpsilonGreedyCandidateSelector:
    """Explores with probability epsilon, otherwise greedy.

    Args:
        epsilon: Probability of random exploration (0.0 to 1.0).
        rng: Random number generator for reproducibility.
    """

    def __init__(
        self,
        epsilon: float,
        rng: random.Random | None = None,
    ) -> None:
        """Initialize with exploration rate."""
        ...

    async def select_candidate(self, state: ParetoState) -> int:
        """With probability epsilon, return random; else best."""
        ...
```

---

## Test Contract

```python
# tests/contracts/test_candidate_selector_protocol.py

import pytest
from typing import Protocol
from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.ports.selector import CandidateSelectorProtocol
from gepa_adk.adapters.candidate_selector import (
    ParetoCandidateSelector,
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
)

class TestCandidateSelectorContract:
    """Verify all implementations satisfy protocol contract."""

    @pytest.fixture(params=[
        ParetoCandidateSelector,
        CurrentBestCandidateSelector,
        lambda: EpsilonGreedyCandidateSelector(epsilon=0.1),
    ])
    def selector(self, request):
        """Parametrized fixture for all selector types."""
        factory = request.param
        if callable(factory) and not isinstance(factory, type):
            return factory()
        return factory()

    def test_is_protocol_compliant(self, selector):
        """Selector implements CandidateSelectorProtocol."""
        assert isinstance(selector, CandidateSelectorProtocol)

    @pytest.mark.asyncio
    async def test_select_returns_valid_index(self, selector, pareto_state):
        """select_candidate() returns valid candidate index."""
        result = await selector.select_candidate(pareto_state)
        assert 0 <= result < len(pareto_state.candidates)

    @pytest.mark.asyncio
    async def test_select_raises_on_empty_state(self, selector, empty_state):
        """select_candidate() raises NoCandidateAvailableError for empty state."""
        with pytest.raises(NoCandidateAvailableError):
            await selector.select_candidate(empty_state)

    @pytest.mark.asyncio
    async def test_select_is_deterministic(self, selector, pareto_state):
        """Same state produces same result (with fixed RNG)."""
        result1 = await selector.select_candidate(pareto_state)
        result2 = await selector.select_candidate(pareto_state)
        # Note: Only deterministic if selector uses seeded RNG
        # For Pareto/Epsilon, this requires same RNG state
```

---

## Usage Examples

### Basic Usage
```python
from gepa_adk.adapters.candidate_selector import ParetoCandidateSelector
from gepa_adk.engine import AsyncGEPAEngine
import random

# Create selector with fixed seed for reproducibility
selector = ParetoCandidateSelector(rng=random.Random(42))

# Pass to engine
engine = AsyncGEPAEngine(
    adapter=my_adapter,
    config=config,
    initial_candidate=candidate,
    batch=training_data,
    candidate_selector=selector,  # New parameter
)

result = await engine.run()
```

### Custom Selector
```python
from gepa_adk.ports.selector import CandidateSelectorProtocol
from gepa_adk.domain.state import ParetoState

class TournamentSelector:
    """Custom tournament selection."""

    def __init__(self, tournament_size: int = 3):
        self.tournament_size = tournament_size

    async def select_candidate(self, state: ParetoState) -> int:
        # Custom selection logic
        ...

# Verify protocol compliance
assert isinstance(TournamentSelector(), CandidateSelectorProtocol)
```
