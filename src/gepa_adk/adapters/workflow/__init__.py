"""Workflow utilities for ADK workflow agent handling.

Currently contains utilities for detecting, traversing, and cloning ADK
workflow agents (SequentialAgent, LoopAgent, ParallelAgent).

Anticipated growth: workflow validation, workflow visualization,
custom workflow agent types.

Attributes:
    is_workflow_agent: Check if agent is a workflow type.
    find_llm_agents: Find all LlmAgents in a workflow.
    WorkflowAgentType: Type alias for workflow agent types.

Examples:
    Detect and traverse a workflow agent:

    ```python
    from gepa_adk.adapters.workflow import is_workflow_agent, find_llm_agents

    if is_workflow_agent(agent):
        llm_agents = find_llm_agents(agent)
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.adapters.evolution`][gepa_adk.adapters.evolution]: MultiAgentAdapter that
        uses workflow utilities for multi-agent evolution.
"""

from gepa_adk.adapters.workflow.workflow import (
    WorkflowAgentType,
    find_llm_agents,
    is_workflow_agent,
)

__all__ = [
    "is_workflow_agent",
    "find_llm_agents",
    "WorkflowAgentType",
]
