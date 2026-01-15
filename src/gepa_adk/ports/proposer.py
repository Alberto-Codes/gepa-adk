"""Protocol definition for candidate proposal strategies.

This module defines the ProposerProtocol interface that all proposal strategies
must implement, enabling pluggable proposal mechanisms (mutation, merge, etc.)
in the evolution engine.

Attributes:
    ProposerProtocol (protocol): Protocol for candidate proposal strategies.

Examples:
    Implementing a custom proposer:

    ```python
    from gepa_adk.ports.proposer import ProposerProtocol
    from gepa_adk.domain.types import ProposalResult
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

from typing import Protocol, runtime_checkable

from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.types import ProposalResult
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
