"""Protocol and interface definitions for external integrations.

Attributes:
    AsyncGEPAAdapter (protocol): Async adapter contract for evaluations.
    EvaluationBatch (class): Container for evaluation outputs and scores.
    DataInst (type): Type variable for input instances.
    Trajectory (type): Type variable for execution traces.
    RolloutOutput (type): Type variable for evaluation outputs.

Examples:
    Import the adapter protocol:

    ```python
    from gepa_adk.ports import AsyncGEPAAdapter, EvaluationBatch
    ```

See Also:
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: Async adapter protocol and types.

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

__all__ = [
    "AsyncGEPAAdapter",
    "EvaluationBatch",
    "DataInst",
    "Trajectory",
    "RolloutOutput",
]
