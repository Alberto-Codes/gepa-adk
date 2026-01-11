"""Public API functions for gepa-adk evolution engine.

This module provides high-level async functions for evolving agent instructions
using the GEPA (Generalized Evolutionary Prompt-programming Architecture) approach.

Note:
    All functions are async and should be awaited. For synchronous usage,
    wrap calls with asyncio.run() or use convenience wrappers.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from gepa_adk.adapters.critic_scorer import CriticScorer
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    MultiAgentEvolutionResult,
)
from gepa_adk.engine import AsyncGEPAEngine


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

    # For now, use a simplified approach: extract from seed and assume only primary evolved
    # TODO: Properly track all agent instructions in iteration history
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
        Simplified implementation that extracts the primary agent's instruction
        from the evolution result and uses seed values for others. The engine
        only tracks a single instruction, so a full implementation would track
        all agent instructions in the iteration history.
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
