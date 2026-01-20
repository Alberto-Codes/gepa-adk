"""Workflow agent utilities for gepa-adk.

This module provides utilities for detecting and traversing ADK workflow
agents (SequentialAgent, LoopAgent, ParallelAgent) to enable workflow-level
evolution of nested LlmAgents.

Examples:
    Detecting workflow agents:

    ```python
    from google.adk.agents import SequentialAgent, LlmAgent
    from gepa_adk.adapters.workflow import is_workflow_agent

    agent = SequentialAgent(name="Pipeline", sub_agents=[])
    assert is_workflow_agent(agent) == True

    llm_agent = LlmAgent(name="Agent", instruction="Be helpful")
    assert is_workflow_agent(llm_agent) == False
    ```

    Finding LlmAgents in a workflow:

    ```python
    from gepa_adk.adapters.workflow import find_llm_agents

    agents = find_llm_agents(workflow, max_depth=5)
    print(f"Found {len(agents)} LlmAgents")
    ```

Note:
    This module isolates ADK-specific imports to the adapters layer,
    following hexagonal architecture principles (ADR-000).
"""

from typing import TYPE_CHECKING

import structlog
from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

logger = structlog.get_logger(__name__)

# Type alias for all workflow agent types
WorkflowAgentType = SequentialAgent | LoopAgent | ParallelAgent


def is_workflow_agent(agent: object) -> bool:
    """Check if an agent is a workflow type.

    Detects whether an agent is a workflow agent (SequentialAgent, LoopAgent,
    or ParallelAgent) versus a regular LlmAgent or other agent type.

    Args:
        agent: Agent instance to check. Can be any object type.

    Returns:
        True if agent is SequentialAgent, LoopAgent, or ParallelAgent.
        False otherwise (including LlmAgent, None, or non-agent objects).

    Examples:
        Detecting workflow agents:

        ```python
        from google.adk.agents import SequentialAgent, LlmAgent
        from gepa_adk.adapters.workflow import is_workflow_agent

        sequential = SequentialAgent(name="Pipeline", sub_agents=[])
        assert is_workflow_agent(sequential) is True

        llm = LlmAgent(name="Agent", instruction="Be helpful")
        assert is_workflow_agent(llm) is False
        ```

    Note:
        Only workflow agent types (SequentialAgent, LoopAgent, ParallelAgent)
        are detected. All workflow agents inherit from BaseAgent and have
        sub_agents, but type detection uses specific class checks for accuracy.
    """
    return isinstance(agent, (SequentialAgent, LoopAgent, ParallelAgent))


def find_llm_agents(
    agent: object,
    max_depth: int = 5,
    current_depth: int = 0,
) -> list["LlmAgent"]:
    """Find all LlmAgents in a workflow (recursive traversal with depth limiting).

    Traverses a workflow agent structure recursively to discover all LlmAgent
    instances at any nesting level, up to the specified maximum depth.

    Args:
        agent: Agent or workflow to search. Can be LlmAgent, workflow agent,
            or any object.
        max_depth: Maximum recursion depth (default: 5). When current_depth
            reaches max_depth, traversal stops. Must be >= 1 for meaningful
            results.
        current_depth: Current recursion level (internal use, default: 0).

    Returns:
        List of LlmAgent instances found. Only includes agents with string
        instructions (skips InstructionProvider callables).

    Examples:
        Finding LlmAgents in a SequentialAgent:

        ```python
        from google.adk.agents import LlmAgent, SequentialAgent
        from gepa_adk.adapters.workflow import find_llm_agents

        agent1 = LlmAgent(name="agent1", instruction="First")
        agent2 = LlmAgent(name="agent2", instruction="Second")
        workflow = SequentialAgent(name="pipeline", sub_agents=[agent1, agent2])

        agents = find_llm_agents(workflow)
        assert len(agents) == 2
        ```

        Finding LlmAgents in nested workflows:

        ```python
        # Sequential -> Parallel -> LlmAgents
        nested_parallel = ParallelAgent(name="parallel", sub_agents=[agent2, agent3])
        workflow = SequentialAgent(
            name="pipeline", sub_agents=[agent1, nested_parallel]
        )

        agents = find_llm_agents(workflow, max_depth=5)
        assert len(agents) == 3  # Finds all agents across levels
        ```

    Note:
        Operates recursively with depth limiting to discover nested LlmAgents.
        Skips LlmAgents with InstructionProvider callables (non-string
        instructions). Respects max_depth to prevent infinite recursion.
    """
    from google.adk.agents import LlmAgent

    # Check depth limit first (before processing)
    # Use > instead of >= to allow processing at max_depth
    # e.g., with max_depth=3, we can process agents at depth 0, 1, 2, 3
    if current_depth > max_depth:
        logger.debug(
            "Max depth exceeded, stopping traversal",
            current_depth=current_depth,
            max_depth=max_depth,
        )
        return []

    # If it's an LlmAgent with string instruction, return it
    if isinstance(agent, LlmAgent):
        # Only include string instructions (skip InstructionProvider callables)
        if isinstance(agent.instruction, str):
            logger.debug(
                "Found LlmAgent",
                agent_name=agent.name,
                depth=current_depth,
            )
            return [agent]
        logger.warning(
            "Skipping LlmAgent with non-string instruction",
            agent_name=agent.name,
            instruction_type=type(agent.instruction).__name__,
            depth=current_depth,
        )
        return []

    # If it's a workflow agent, recursively search sub_agents
    if is_workflow_agent(agent):
        logger.debug(
            "Traversing workflow agent",
            workflow_name=getattr(agent, "name", "unknown"),
            workflow_type=type(agent).__name__,
            depth=current_depth,
            max_depth=max_depth,
        )
        agents: list[LlmAgent] = []
        # Recursive traversal: iterate sub_agents and recurse into nested workflows
        # Type narrowing: is_workflow_agent() ensures agent is SequentialAgent,
        # LoopAgent, or ParallelAgent. All inherit from BaseAgent with sub_agents.
        if isinstance(agent, (SequentialAgent, LoopAgent, ParallelAgent)):
            for sub_agent in agent.sub_agents:
                # Recursively search each sub-agent
                nested_agents = find_llm_agents(
                    sub_agent, max_depth=max_depth, current_depth=current_depth + 1
                )
                agents.extend(nested_agents)
        logger.debug(
            "Completed workflow traversal",
            workflow_name=getattr(agent, "name", "unknown"),
            agents_found=len(agents),
            depth=current_depth,
        )
        return agents

    # Not an agent or workflow - return empty list
    logger.debug(
        "Skipping non-agent object",
        object_type=type(agent).__name__,
        depth=current_depth,
    )
    return []
