"""Protocol and interface definitions for external integrations.

This package defines the ports layer of the hexagonal architecture, providing
protocol interfaces that adapters implement to integrate with external systems.
All protocols follow async-first design principles and support runtime checking.

Attributes:
    AgentProvider (protocol): Protocol for loading and persisting agents.
    AsyncGEPAAdapter (protocol): Async adapter contract for evaluations.
    EvaluationBatch (class): Container for evaluation outputs and scores.
    Scorer (protocol): Protocol for scoring agent outputs.
    ProposerProtocol (protocol): Protocol for candidate proposal strategies.
    AgentExecutorProtocol (protocol): Protocol for unified agent execution.
    ExecutionResult (dataclass): Result of an agent execution.
    ExecutionStatus (enum): Status of agent execution.
    DataInst (type): Type variable for input instances.
    Trajectory (type): Type variable for execution traces.
    RolloutOutput (type): Type variable for evaluation outputs.

Examples:
    Import the agent provider protocol:

    ```python
    from gepa_adk.ports import AgentProvider
    ```

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
    from gepa_adk.ports import ProposerProtocol
    from gepa_adk.domain.types import ProposalResult
    ```

    Import the agent executor protocol:

    ```python
    from gepa_adk.ports import (
        AgentExecutorProtocol,
        ExecutionResult,
        ExecutionStatus,
    )
    ```

See Also:
    - [`gepa_adk.ports.agent_provider`][gepa_adk.ports.agent_provider]: Agent provider protocol
        for loading and persisting agents.
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: Async adapter protocol and types.
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Scorer protocol for custom scoring logic.
    - [`gepa_adk.ports.proposer`][gepa_adk.ports.proposer]: Proposer protocol for
        candidate generation.
    - [`gepa_adk.ports.agent_executor`][gepa_adk.ports.agent_executor]: Agent executor protocol
        for unified agent execution.

Note:
    This layer follows hexagonal architecture principles, defining
    ports that adapters implement to integrate with external systems.
"""

from gepa_adk.domain.types import ProposalResult
from gepa_adk.ports.adapter import (
    AsyncGEPAAdapter,
    DataInst,
    EvaluationBatch,
    RolloutOutput,
    Trajectory,
)
from gepa_adk.ports.agent_executor import (
    AgentExecutorProtocol,
    ExecutionResult,
    ExecutionStatus,
)
from gepa_adk.ports.agent_provider import AgentProvider
from gepa_adk.ports.component_handler import ComponentHandler
from gepa_adk.ports.proposer import ProposerProtocol
from gepa_adk.ports.scorer import Scorer
from gepa_adk.ports.selector import (
    CandidateSelectorProtocol,
    ComponentSelectorProtocol,
    EvaluationPolicyProtocol,
)
from gepa_adk.ports.stopper import StopperProtocol
from gepa_adk.ports.video_blob_service import VideoBlobServiceProtocol

__all__ = [
    "AgentProvider",
    "AsyncGEPAAdapter",
    "EvaluationBatch",
    "DataInst",
    "Trajectory",
    "RolloutOutput",
    "Scorer",
    "ProposerProtocol",
    "ProposalResult",
    "CandidateSelectorProtocol",
    "ComponentHandler",
    "ComponentSelectorProtocol",
    "EvaluationPolicyProtocol",
    "AgentExecutorProtocol",
    "ExecutionResult",
    "ExecutionStatus",
    "StopperProtocol",
    "VideoBlobServiceProtocol",
]
