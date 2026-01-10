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
    gepa_adk.ports.adapter: Async adapter protocol and types.
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
