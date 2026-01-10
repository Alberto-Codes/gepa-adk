"""Protocol and interface definitions for external integrations.

This package defines the ports layer of the hexagonal architecture, providing
protocol interfaces that adapters implement to integrate with external systems.
All protocols follow async-first design principles and support runtime checking.

Attributes:
    AsyncGEPAAdapter (protocol): Async adapter contract for evaluations.
    EvaluationBatch (class): Container for evaluation outputs and scores.
    Scorer (protocol): Protocol for scoring agent outputs.
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

See Also:
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: Async adapter protocol and types.
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Scorer protocol for custom scoring logic.

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
from gepa_adk.ports.scorer import Scorer

__all__ = [
    "AsyncGEPAAdapter",
    "EvaluationBatch",
    "DataInst",
    "Trajectory",
    "RolloutOutput",
    "Scorer",
]
