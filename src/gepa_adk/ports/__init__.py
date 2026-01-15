"""Protocol and interface definitions for external integrations.

This package defines the ports layer of the hexagonal architecture, providing
protocol interfaces that adapters implement to integrate with external systems.
All protocols follow async-first design principles and support runtime checking.

Attributes:
    AsyncGEPAAdapter (protocol): Async adapter contract for evaluations.
    EvaluationBatch (class): Container for evaluation outputs and scores.
    Scorer (protocol): Protocol for scoring agent outputs.
    ProposerProtocol (protocol): Protocol for candidate proposal strategies.
    ProposalResult (class): Result of a successful proposal operation.
    DataInst (type): Type variable for input instances.
    Trajectory (type): Type variable for execution traces.
    RolloutOutput (type): Type variable for evaluation outputs.

Examples:
    Import the adapter protocol:

    ```python
    from gepa_adk.ports import AsyncGEPAAdapter, EvaluationBatch
    ```

    Import the scorer protocol:

    ```python
    from gepa_adk.ports import Scorer
    ```

    Import the proposer protocol:

    ```python
    from gepa_adk.ports import ProposerProtocol, ProposalResult
    ```

See Also:
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: Async adapter protocol and types.
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Scorer protocol for custom scoring logic.
    - [`gepa_adk.ports.proposer`][gepa_adk.ports.proposer]: Proposer protocol for
        candidate generation.

Note:
    This layer follows hexagonal architecture principles, defining
    ports that adapters implement to integrate with external systems.
"""

from gepa_adk.ports.adapter import (
    AsyncGEPAAdapter,
    DataInst,
    EvaluationBatch,
    RolloutOutput,
    Trajectory,
)
from gepa_adk.ports.proposer import ProposalResult, ProposerProtocol
from gepa_adk.ports.scorer import Scorer
from gepa_adk.ports.selector import (
    CandidateSelectorProtocol,
    ComponentSelectorProtocol,
    EvaluationPolicyProtocol,
)

__all__ = [
    "AsyncGEPAAdapter",
    "EvaluationBatch",
    "DataInst",
    "Trajectory",
    "RolloutOutput",
    "Scorer",
    "ProposerProtocol",
    "ProposalResult",
    "CandidateSelectorProtocol",
    "ComponentSelectorProtocol",
    "EvaluationPolicyProtocol",
]
