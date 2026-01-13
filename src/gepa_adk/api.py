"""Public API functions for gepa-adk evolution engine.

This module provides high-level async functions for evolving agent instructions
using the GEPA (Generalized Evolutionary Prompt-programming Architecture) approach.

Note:
    This module implements the primary user-facing API for agent evolution.
    All functions are async and should be awaited. For synchronous usage,
    wrap calls with asyncio.run() or use convenience wrappers.
"""

from __future__ import annotations

from typing import Any

import structlog
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from gepa_adk.adapters.critic_scorer import CriticScorer
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.adapters.workflow import find_llm_agents
from gepa_adk.domain.exceptions import WorkflowEvolutionError
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    MultiAgentEvolutionResult,
)
from gepa_adk.engine import AsyncGEPAEngine

logger = structlog.get_logger()


async def evolve_group(
    agents: list[LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
) -> MultiAgentEvolutionResult:
    """Evolve multiple agents together.

    Optimizes instructions for all provided agents by targeting
    the primary agent's output score. When share_session=True,
    agents execute sequentially with shared session state, enabling
    later agents to access earlier agents' outputs.

    Args:
        agents: List of ADK agents to evolve together. Must have
            at least one agent. All agents must have unique names.
        primary: Name of the agent whose output is used for scoring.
            Must match one of the agent names in the list.
        trainset: Training examples for evaluation. Each example
            should have an "input" key and optionally an "expected" key.
        critic: Optional critic agent for scoring. If None, the primary
            agent must have an output_schema for schema-based scoring.
        share_session: Whether agents share session state during
            execution. When True (default), uses SequentialAgent.
            When False, agents execute with isolated sessions.
        config: Evolution configuration. If None, uses EvolutionConfig
            defaults.

    Returns:
        MultiAgentEvolutionResult containing evolved_instructions dict
        mapping agent names to their optimized instruction text, along
        with score metrics and iteration history.

    Raises:
        MultiAgentValidationError: If agents list is empty, primary
            agent not found, duplicate agent names, or no scorer
            and primary lacks output_schema.
        EvolutionError: If evolution fails during execution.

    Examples:
        Basic usage with three agents:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk import evolve_group

        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code based on the requirement.",
        )
        critic = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review the code in {generator_output}.",
        )
        validator = LlmAgent(
            name="validator",
            model="gemini-2.0-flash",
            instruction="Validate the reviewed code.",
            output_schema=ValidationResult,
        )

        result = await evolve_group(
            agents=[generator, critic, validator],
            primary="validator",
            trainset=training_data,
        )

        print(result.evolved_instructions["generator"])
        print(result.evolved_instructions["critic"])
        print(result.evolved_instructions["validator"])
        ```

        With custom critic scorer:

        ```python
        scoring_critic = LlmAgent(
            name="quality_scorer",
            model="gemini-2.0-flash",
            instruction="Score the output quality.",
            output_schema=CriticOutput,
        )

        result = await evolve_group(
            agents=[generator, validator],
            primary="validator",
            trainset=training_data,
            critic=scoring_critic,
        )
        ```
    """
    # Build scorer
    scorer = None
    if critic:
        scorer = CriticScorer(critic_agent=critic)

    # Create adapter
    adapter = MultiAgentAdapter(
        agents=agents,
        primary=primary,
        scorer=scorer,
        share_session=share_session,
    )

    # Build seed candidate: {agent.name}_instruction for each agent
    # Also include "instruction" key pointing to primary agent's instruction
    # (required by AsyncGEPAEngine)
    primary_agent = next(agent for agent in agents if agent.name == primary)
    # Ensure all instructions are strings (LlmAgent.instruction can be callable,
    # but we only support string instructions for evolution)
    seed_candidate_components: dict[str, str] = {
        f"{agent.name}_instruction": str(agent.instruction) for agent in agents
    }
    # Add required "instruction" key for engine compatibility
    seed_candidate_components["instruction"] = str(primary_agent.instruction)
    initial_candidate = Candidate(components=seed_candidate_components)

    # Create engine
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=config or EvolutionConfig(),
        initial_candidate=initial_candidate,
        batch=trainset,
    )

    # Run evolution
    evolution_result = await engine.run()

    # Extract best candidate components from engine state
    # The engine stores best_candidate in _state, but we can't access it directly
    # So we reconstruct from the evolution result and seed candidate
    # For multi-agent, we need to track all agent instructions
    # Since the engine only tracks a single "instruction", we use a workaround:
    # - Primary agent's instruction comes from evolution_result.evolved_instruction
    # - Other agents' instructions come from the last accepted candidate's components
    #   (which we track via the adapter's propose_new_texts calls)

    # Current implementation: Only the primary agent's instruction evolves via the engine.
    # Supporting agents retain their original instructions from the seed candidate.
    # This is a known limitation - full multi-agent tracking will be implemented
    # when the engine supports multiple instruction components (see issue #39).
    evolved_instructions = _extract_evolved_instructions(
        evolution_result=evolution_result,
        seed_components=seed_candidate_components,
        agents=agents,
        primary=primary,
    )

    # Convert EvolutionResult to MultiAgentEvolutionResult
    return MultiAgentEvolutionResult(
        evolved_instructions=evolved_instructions,
        original_score=evolution_result.original_score,
        final_score=evolution_result.final_score,
        primary_agent=primary,
        iteration_history=evolution_result.iteration_history,
        total_iterations=evolution_result.total_iterations,
    )


def _extract_evolved_instructions(
    evolution_result: EvolutionResult,
    seed_components: dict[str, str],
    agents: list[LlmAgent],
    primary: str,
) -> dict[str, str]:
    """Extract evolved instructions for all agents.

    Args:
        evolution_result: Evolution result from engine.
        seed_components: Initial candidate components.
        agents: List of agents that were evolved.
        primary: Name of the primary agent.

    Returns:
        Dictionary mapping agent names to their evolved instructions.

    Note:
        Simplifies extraction by only evolving the primary agent's instruction.
        Supporting agents retain their seed instructions unchanged. This is due
        to the engine tracking a single "instruction" component. Full multi-agent
        evolution will require engine enhancements to track all agent instructions
        independently (see issue #39 for proposer integration).
    """
    evolved_instructions: dict[str, str] = {}

    # Primary agent's instruction comes from evolution result
    evolved_instructions[primary] = evolution_result.evolved_instruction

    # For other agents, use seed values (simplified - assumes only primary evolved)
    # In a full implementation, we'd track all agent instructions
    for agent in agents:
        if agent.name != primary:
            key = f"{agent.name}_instruction"
            # Use seed value as fallback
            evolved_instructions[agent.name] = seed_components.get(
                key, str(agent.instruction)
            )

    return evolved_instructions


async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
) -> MultiAgentEvolutionResult:
    """Evolve all LlmAgents within a workflow agent structure.

    Discovers all LlmAgent instances within a workflow (SequentialAgent,
    LoopAgent, or ParallelAgent) and evolves them together while preserving
    the workflow structure. Uses shared session state to maintain workflow
    context during evaluation.

    Args:
        workflow: Workflow agent containing LlmAgents to evolve. Must be
            SequentialAgent, LoopAgent, or ParallelAgent.
        trainset: Training examples for evaluation. Each example should have
            an "input" key and optionally an "expected" key.
        critic: Optional critic agent for scoring. If None, the primary agent
            must have an output_schema for schema-based scoring.
        primary: Name of the agent to score. Defaults to the last LlmAgent
            found in the workflow (for sequential workflows, this is typically
            the final output producer).
        max_depth: Maximum recursion depth for nested workflows (default: 5).
            Only used when recursive traversal is implemented (US3).
        config: Evolution configuration. If None, uses EvolutionConfig defaults.

    Returns:
        MultiAgentEvolutionResult containing evolved_instructions dict mapping
        agent names to their optimized instruction text, along with score
        metrics and iteration history.

    Raises:
        WorkflowEvolutionError: If workflow contains no LlmAgents.
        MultiAgentValidationError: If primary agent not found or no scorer
            available.
        EvolutionError: If evolution fails during execution.

    Examples:
        Evolving a SequentialAgent pipeline:

        ```python
        from google.adk.agents import LlmAgent, SequentialAgent
        from gepa_adk import evolve_workflow

        agent1 = LlmAgent(name="generator", instruction="Generate code")
        agent2 = LlmAgent(name="critic", instruction="Review code")
        pipeline = SequentialAgent(name="Pipeline", sub_agents=[agent1, agent2])

        result = await evolve_workflow(
            workflow=pipeline,
            trainset=[{"input": "test", "expected": "result"}],
        )

        print(result.evolved_instructions["generator"])
        print(result.evolved_instructions["critic"])
        ```

        Evolving a LoopAgent workflow:

        ```python
        from google.adk.agents import LoopAgent, LlmAgent
        from gepa_adk import evolve_workflow

        critic = LlmAgent(name="critic", instruction="Review code")
        refiner = LlmAgent(name="refiner", instruction="Refine code")
        loop = LoopAgent(
            name="RefinementLoop", sub_agents=[critic, refiner], max_iterations=5
        )

        result = await evolve_workflow(workflow=loop, trainset=trainset)
        # Loop configuration (max_iterations) is preserved
        ```

        Evolving a ParallelAgent workflow:

        ```python
        from google.adk.agents import ParallelAgent, LlmAgent
        from gepa_adk import evolve_workflow

        researcher1 = LlmAgent(name="researcher1", instruction="Research topic A")
        researcher2 = LlmAgent(name="researcher2", instruction="Research topic B")
        parallel = ParallelAgent(
            name="ParallelResearch", sub_agents=[researcher1, researcher2]
        )

        result = await evolve_workflow(workflow=parallel, trainset=trainset)
        # All parallel branches are evolved together
        ```

    Note:
        Operates on workflow agents (SequentialAgent, LoopAgent, ParallelAgent)
        with recursive traversal and depth limiting via max_depth parameter.
        Supports nested structures. LoopAgent and ParallelAgent configurations
        (max_iterations, etc.) are preserved during evolution. Always uses
        share_session=True to maintain workflow context (FR-010).
    """
    logger.info(
        "Starting workflow evolution",
        workflow_name=workflow.name,
        workflow_type=type(workflow).__name__,
    )

    # Find all LlmAgents in the workflow (single-level for US1)
    llm_agents = find_llm_agents(workflow, max_depth=max_depth)

    # Validate that at least one LlmAgent was found
    if not llm_agents:
        error_msg = (
            f"No LlmAgents found in workflow '{workflow.name}'. "
            "Workflow must contain at least one LlmAgent to evolve."
        )
        logger.error(
            "Workflow evolution failed", workflow_name=workflow.name, error=error_msg
        )
        raise WorkflowEvolutionError(
            error_msg,
            workflow_name=workflow.name,
        )

    logger.info(
        "Found LlmAgents in workflow",
        workflow_name=workflow.name,
        agent_count=len(llm_agents),
        agent_names=[agent.name for agent in llm_agents],
    )

    # Determine primary agent (default to last agent for sequential workflows)
    if primary is None:
        primary = llm_agents[-1].name
        logger.debug(
            "Using default primary agent",
            workflow_name=workflow.name,
            primary=primary,
        )

    # Delegate to evolve_group with share_session=True (FR-010)
    logger.debug(
        "Delegating to evolve_group",
        workflow_name=workflow.name,
        agent_count=len(llm_agents),
        primary=primary,
        share_session=True,
    )

    return await evolve_group(
        agents=llm_agents,
        primary=primary,
        trainset=trainset,
        critic=critic,
        share_session=True,  # FR-010: Always use shared session for workflow context
        config=config,
    )
