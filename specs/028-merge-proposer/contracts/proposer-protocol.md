# ProposerProtocol Contract

## Protocol Definition

```python
from typing import Protocol, runtime_checkable
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.adapter import EvaluationBatch

@runtime_checkable
class ProposerProtocol(Protocol):
    """Protocol for candidate proposal strategies.

    Proposers generate new candidates for evolution. The two main implementations
    are mutation-based (reflective improvement) and merge-based (genetic crossover).

    Attributes:
        None required - implementations may have configuration attributes.

    Examples:
        ```python
        class MyProposer:
            async def propose(
                self,
                state: ParetoState,
                eval_batch: EvaluationBatch | None = None,
            ) -> ProposalResult | None:
                # Generate proposal
                return ProposalResult(candidate=..., parent_indices=[...], tag="custom")
        ```

    Note:
        All proposers return None when no valid proposal can be generated.
    """

    async def propose(
        self,
        state: ParetoState,
        eval_batch: EvaluationBatch | None = None,
    ) -> "ProposalResult | None":
        """Propose a new candidate based on current evolution state.

        Args:
            state: Current Pareto state with candidates and frontier.
            eval_batch: Optional evaluation batch for reflective proposals.

        Returns:
            ProposalResult containing the proposed candidate and metadata,
            or None if no proposal is possible.

        Note:
            Implementations should be idempotent and not modify state.
        """
        ...
```

## ProposalResult Definition

```python
from dataclasses import dataclass, field
from typing import Any
from gepa_adk.domain.models import Candidate

@dataclass(frozen=True)
class ProposalResult:
    """Result of a successful proposal operation.

    Attributes:
        candidate: The proposed candidate with components.
        parent_indices: Indices of parent candidate(s) in ParetoState.
        tag: Type of proposal ("mutation" or "merge").
        metadata: Additional proposal-specific metadata.

    Examples:
        ```python
        result = ProposalResult(
            candidate=Candidate(components={"instruction": "..."}),
            parent_indices=[5, 8],
            tag="merge",
            metadata={"ancestor_idx": 2},
        )
        ```
    """

    candidate: Candidate
    parent_indices: list[int]
    tag: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

## Contract Requirements

### CR-001: Async Proposal Method
- `propose()` MUST be an async method
- MUST NOT block the event loop

### CR-002: State Immutability
- `propose()` MUST NOT modify the input `state`
- MUST NOT modify `eval_batch` if provided

### CR-003: Return Contract
- MUST return `ProposalResult` on successful proposal
- MUST return `None` when no valid proposal possible
- MUST NOT raise exceptions for normal failure cases (no candidates, etc.)

### CR-004: Parent Tracking
- `parent_indices` MUST contain valid indices into `state.candidates`
- For mutation: exactly 1 parent index
- For merge: exactly 2 parent indices

### CR-005: Tag Values
- `tag` MUST be one of: "mutation", "merge"
- Tag MUST match parent_indices length expectation

## Implementation Checklist

- [ ] Implement `async def propose()` method
- [ ] Return `ProposalResult` or `None`
- [ ] Never modify input state
- [ ] Include valid parent_indices
- [ ] Set appropriate tag value
- [ ] Log failures via structlog (not exceptions)
