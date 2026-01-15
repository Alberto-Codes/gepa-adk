"""Protocol definition for candidate proposal strategies.

This module defines the ProposerProtocol interface that all proposal strategies
must implement, enabling pluggable proposal mechanisms (mutation, merge, etc.)
in the evolution engine.

Attributes:
    ProposerProtocol (protocol): Protocol for candidate proposal strategies.
    ProposalResult (class): Result of a successful proposal operation.

Examples:
    Implementing a custom proposer:

    ```python
    from gepa_adk.ports.proposer import ProposerProtocol, ProposalResult
    from gepa_adk.domain.state import ParetoState
    from gepa_adk.domain.models import Candidate


    class MyProposer:
        async def propose(
            self,
            state: ParetoState,
            eval_batch: EvaluationBatch | None = None,
        ) -> ProposalResult | None:
            # Generate proposal
            return ProposalResult(
                candidate=Candidate(components={"instruction": "..."}),
                parent_indices=[5],
                tag="mutation",
            )
    ```

Note:
    All proposers return None when no valid proposal can be generated.
    Implementations should be idempotent and not modify state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from gepa_adk.domain.models import Candidate
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.adapter import EvaluationBatch


@dataclass(frozen=True, slots=True)
class ProposalResult:
    """Result of a successful proposal operation.

    Attributes:
        candidate (Candidate): The proposed candidate with components.
        parent_indices (list[int]): Indices of parent candidate(s) in ParetoState.
        tag (str): Type of proposal ("mutation" or "merge").
        metadata (dict[str, Any]): Additional proposal-specific metadata.

    Examples:
        Creating a mutation proposal result:

        ```python
        from gepa_adk.ports.proposer import ProposalResult
        from gepa_adk.domain.models import Candidate

        result = ProposalResult(
            candidate=Candidate(components={"instruction": "Be helpful"}),
            parent_indices=[5],
            tag="mutation",
        )
        ```

        Creating a merge proposal result:

        ```python
        result = ProposalResult(
            candidate=Candidate(components={"instruction": "..."}),
            parent_indices=[5, 8],
            tag="merge",
            metadata={"ancestor_idx": 2},
        )
        ```

    Note:
        Frozen dataclass ensures immutability of proposal results.
        Parent indices must be valid indices into the ParetoState.candidates list.
    """

    candidate: Candidate
    parent_indices: list[int]
    tag: str
    metadata: dict[str, Any] = field(default_factory=dict)


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
    ) -> ProposalResult | None:
        """Propose a new candidate based on current evolution state.

        Args:
            state (ParetoState): Current Pareto state with candidates and frontier.
                Contains the current evolution state including all discovered candidates,
                their scores, and the Pareto frontier for selection.
            eval_batch (EvaluationBatch | None): Optional evaluation batch for reflective proposals.
                Used by mutation-based proposers to generate reflective datasets. Ignored
                by merge-based proposers which operate on existing candidates.

        Returns:
            ProposalResult | None: ProposalResult containing the proposed candidate and metadata,
            or None if no proposal is possible (e.g., no suitable candidates, insufficient
            frontier, or proposal generation failed).

        Examples:
            Implementing a custom proposer:

            ```python
            class MyProposer:
                async def propose(
                    self,
                    state: ParetoState,
                    eval_batch: EvaluationBatch | None = None,
                ) -> ProposalResult | None:
                    # Generate proposal logic
                    return ProposalResult(
                        candidate=Candidate(components={"instruction": "..."}),
                        parent_indices=[5],
                        tag="mutation",
                    )
            ```

        Note:
            Implementations should be idempotent and not modify state. The method should
            be safe to call multiple times with the same state without side effects.
        """
        ...
