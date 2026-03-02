"""Agent execution infrastructure for GEPA evolution.

Contains the agent executor for unified ADK agent execution and the trial builder
for constructing reflection dataset records.

Anticipated growth: execution middleware, custom session service adapters,
batch execution strategies.

Attributes:
    AgentExecutor: Unified executor for all ADK agent types.
    SessionNotFoundError: Raised when session lookup fails.
    TrialBuilder: Builder for trial records from evaluation results.

Examples:
    Execute an agent and build a trial record:

    ```python
    from gepa_adk.adapters.execution import AgentExecutor, TrialBuilder

    executor = AgentExecutor(session_service=session_service)
    result = await executor.execute(agent, user_content)
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.ports.agent_executor`][gepa_adk.ports.agent_executor]: AgentExecutorProtocol
        that AgentExecutor implements.
    - [`gepa_adk.adapters.evolution`][gepa_adk.adapters.evolution]: Adapters that depend on
        execution infrastructure.

Note:
    This package encapsulates agent execution and trial-building infrastructure.
"""

from gepa_adk.adapters.execution.agent_executor import (
    AgentExecutor,
    SessionNotFoundError,
)
from gepa_adk.adapters.execution.trial_builder import TrialBuilder

__all__ = [
    "AgentExecutor",
    "SessionNotFoundError",
    "TrialBuilder",
]
