"""Example: Nested workflow evolution with structure preservation.

This example demonstrates evolving agents within a complex nested workflow where:
1. Multiple workflow types are combined (Sequential, Parallel, Loop)
2. The entire structure is preserved during evolution (not flattened)
3. Each agent type maintains its execution semantics
4. Data flows correctly between nested stages

Key Concepts:
    - Nested workflow structure preservation during evolution
    - Combining SequentialAgent, ParallelAgent, and LoopAgent
    - Recursive cloning preserves all properties at every level
    - Template strings enable data flow between nested agents

Prerequisites:
    - Python 3.12+
    - gepa-adk installed
    - OLLAMA_API_BASE environment variable set (e.g., http://localhost:11434)

Usage:
    python examples/nested_workflow_evolution.py
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import structlog
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm

from gepa_adk import (
    CriticOutput,
    EvolutionConfig,
    MultiAgentEvolutionResult,
    evolve_workflow,
)
from gepa_adk.utils import EncodingSafeProcessor

# -----------------------------------------------------------------------------
# Console Output Encoding
# -----------------------------------------------------------------------------
_encoding_processor = EncodingSafeProcessor()


def safe_print(text: str) -> None:
    """Print text safely on Windows consoles with cp1252 encoding."""
    print(_encoding_processor.sanitize_string(text))


# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        EncodingSafeProcessor(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# -----------------------------------------------------------------------------
# Nested Workflow Construction
# -----------------------------------------------------------------------------
def create_refinement_loop() -> LoopAgent:
    """Create a LoopAgent for iterative content refinement.

    The refiner agent runs multiple times to improve content quality.
    The max_iterations is preserved during evolution.

    Returns:
        LoopAgent that refines content through multiple passes.
    """
    refiner = LlmAgent(
        name="refiner",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Review and improve the current content.\n"
            "Focus on clarity, structure, and completeness.\n"
            "Provide an improved version."
        ),
        output_key="refined_content",
    )

    return LoopAgent(
        name="RefinementLoop",
        sub_agents=[refiner],
        max_iterations=2,  # Preserved during evolution!
    )


def create_parallel_research() -> ParallelAgent:
    """Create parallel research agents that execute concurrently.

    Two researchers gather different perspectives simultaneously.
    The ParallelAgent type is preserved during evolution.

    Returns:
        ParallelAgent with two concurrent research branches.
    """
    researcher1 = LlmAgent(
        name="researcher1",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Research supporting arguments and evidence.\n"
            "Focus on facts, data, and expert opinions.\n"
            "Provide a clear summary of your findings."
        ),
        output_key="supporting_research",
    )

    researcher2 = LlmAgent(
        name="researcher2",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Research counterarguments and challenges.\n"
            "Focus on limitations, criticisms, and alternative views.\n"
            "Provide a clear summary of your findings."
        ),
        output_key="counter_research",
    )

    return ParallelAgent(
        name="ParallelResearch",
        sub_agents=[researcher1, researcher2],
    )


def create_nested_workflow() -> SequentialAgent:
    """Create the complete nested workflow.

    Structure:
    Sequential([
        Parallel([
            Loop([Refiner]),
            Loop([Refiner])  # Could be different, using same pattern for simplicity
        ]),
        ParallelResearch,
        Synthesizer
    ])

    This demonstrates a complex workflow that:
    1. First refines two parallel streams through loops
    2. Then conducts parallel research
    3. Finally synthesizes all outputs

    Returns:
        SequentialAgent containing the nested workflow structure.
    """
    # Stage 1: Refinement loop for initial content
    refinement_loop = create_refinement_loop()

    # Stage 2: Parallel research gathering
    parallel_research = create_parallel_research()

    # Stage 3: Final synthesizer that combines all outputs
    synthesizer = LlmAgent(
        name="synthesizer",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "Synthesize the following into a comprehensive analysis:\n\n"
            "## Refined Content\n"
            "{refined_content}\n\n"
            "## Supporting Research\n"
            "{supporting_research}\n\n"
            "## Counter Research\n"
            "{counter_research}\n\n"
            "Create a balanced, well-structured synthesis."
        ),
        output_key="final_synthesis",
    )

    return SequentialAgent(
        name="NestedPipeline",
        sub_agents=[refinement_loop, parallel_research, synthesizer],
    )


# -----------------------------------------------------------------------------
# Critic Agent (Scores the synthesis - NOT evolved)
# -----------------------------------------------------------------------------
def create_critic() -> LlmAgent:
    """Create a critic agent for scoring the final synthesis.

    The critic evaluates how well the nested workflow produced
    a comprehensive, balanced analysis.

    Returns:
        LlmAgent configured as a synthesis quality critic.
    """
    return LlmAgent(
        name="synthesis_critic",
        description=(
            "A synthesis quality critic who evaluates how well "
            "multiple perspectives are integrated into a balanced analysis."
        ),
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
        instruction=(
            "You are a synthesis quality critic. Evaluate the final synthesis:\n\n"
            "## Dimension Scores (0.0-1.0 each):\n"
            "- refinement: Does it show evidence of iterative improvement?\n"
            "- balance: Are supporting and counter arguments both represented?\n"
            "- integration: Are all perspectives woven together coherently?\n"
            "- depth: Does it go beyond surface-level combination?\n\n"
            "## Scoring Guide:\n"
            "- 0.0-0.2: Poor synthesis. Missing perspectives, disjointed.\n"
            "- 0.3-0.4: Basic synthesis. Perspectives mentioned but not integrated.\n"
            "- 0.5-0.6: Average synthesis. Some integration attempted.\n"
            "- 0.7-0.8: Good synthesis. Clear integration of all perspectives.\n"
            "- 0.9-1.0: Excellent synthesis. Deep integration, insightful analysis.\n\n"
            "## In Your Feedback:\n"
            "- Note which perspectives are well-represented or missing\n"
            "- Suggest how to better integrate the different viewpoints\n"
        ),
        output_schema=CriticOutput,
    )


# -----------------------------------------------------------------------------
# Training Data
# -----------------------------------------------------------------------------
def create_trainset() -> list[dict[str, Any]]:
    """Create training examples for evolution.

    Each example is a topic that benefits from the full nested workflow:
    - Iterative refinement improves initial analysis
    - Parallel research gathers multiple perspectives
    - Synthesis combines everything into a cohesive result
    """
    return [
        {"input": "Analyze the impact of remote work on productivity."},
        {"input": "Evaluate the benefits and drawbacks of electric vehicles."},
        {"input": "Assess the role of AI in modern education."},
    ]


# -----------------------------------------------------------------------------
# Evolution Runner
# -----------------------------------------------------------------------------
async def run_nested_workflow_evolution(
    workflow: SequentialAgent,
    critic: LlmAgent,
    trainset: list[dict[str, Any]],
) -> MultiAgentEvolutionResult:
    """Run evolutionary optimization on the nested workflow.

    The evolution process preserves the entire nested structure:
    1. LoopAgent iterations are maintained
    2. ParallelAgent branches execute concurrently
    3. SequentialAgent order is preserved
    4. All LlmAgents can be evolved with round-robin

    Args:
        workflow: The nested SequentialAgent workflow.
        critic: Separate critic agent for scoring (not evolved).
        trainset: Training examples for evolution.

    Returns:
        MultiAgentEvolutionResult with evolved instructions for all agents.
    """
    config = EvolutionConfig(
        max_iterations=4,
        patience=2,
    )

    # Count workflow structure
    def count_structure(agent: Any, depth: int = 0) -> dict[str, int]:
        counts = {"depth": depth, "llm_agents": 0, "workflow_agents": 0}
        if isinstance(agent, LlmAgent):
            counts["llm_agents"] = 1
        elif isinstance(agent, (SequentialAgent, LoopAgent, ParallelAgent)):
            counts["workflow_agents"] = 1
            for sub in agent.sub_agents:
                sub_counts = count_structure(sub, depth + 1)
                counts["depth"] = max(counts["depth"], sub_counts["depth"])
                counts["llm_agents"] += sub_counts["llm_agents"]
                counts["workflow_agents"] += sub_counts["workflow_agents"]
        return counts

    structure_info = count_structure(workflow)

    logger.info(
        "nested_workflow_evolution.starting",
        workflow_name=workflow.name,
        max_depth=structure_info["depth"],
        llm_agent_count=structure_info["llm_agents"],
        workflow_agent_count=structure_info["workflow_agents"],
        trainset_size=len(trainset),
        evolution_iterations=config.max_iterations,
    )

    # evolve_workflow() preserves the entire nested structure:
    # - LoopAgent.max_iterations is maintained
    # - ParallelAgent concurrent execution is preserved
    # - SequentialAgent order is maintained
    # - All types are cloned recursively
    result = await evolve_workflow(
        workflow=workflow,
        trainset=trainset,
        critic=critic,
        round_robin=True,  # Evolve all agents in the nested structure
        config=config,
    )

    logger.info(
        "nested_workflow_evolution.complete",
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
    )

    return result


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
async def main() -> None:
    """Run the nested workflow evolution example."""
    if not os.getenv("OLLAMA_API_BASE"):
        raise ValueError("OLLAMA_API_BASE environment variable required")

    logger.info("example.nested_workflow.start")

    try:
        # Create the nested workflow
        workflow = create_nested_workflow()

        # Log workflow structure
        logger.info(
            "nested_workflow.structure",
            root_type=type(workflow).__name__,
            stage_count=len(workflow.sub_agents),
            stages=[
                f"{type(s).__name__}:{s.name}"
                for s in workflow.sub_agents
            ],
        )

        # Create the critic agent (scores output, NOT evolved)
        critic = create_critic()

        # Create training examples
        trainset = create_trainset()

        # Run evolution
        result = await run_nested_workflow_evolution(workflow, critic, trainset)

        # Display results
        print("\n" + "=" * 70)
        print("NESTED WORKFLOW EVOLUTION RESULTS")
        print("=" * 70)
        print(f"Original score: {result.original_score:.3f}")
        print(f"Final score:    {result.final_score:.3f}")
        print(f"Improvement:    {result.improvement:.2%}")
        print(f"Iterations:     {result.total_iterations}")

        print("\n" + "-" * 70)
        print("WORKFLOW STRUCTURE (preserved during evolution):")
        print("-" * 70)
        print(f"Root: {type(workflow).__name__}({workflow.name})")
        for i, stage in enumerate(workflow.sub_agents):
            stage_type = type(stage).__name__
            if hasattr(stage, "max_iterations"):
                iters = stage.max_iterations
                print(f"  Stage {i+1}: {stage_type}({stage.name}, max_iterations={iters})")
            elif hasattr(stage, "sub_agents"):
                sub_names = [s.name for s in stage.sub_agents]
                print(f"  Stage {i+1}: {stage_type}({stage.name}, sub_agents={sub_names})")
            else:
                print(f"  Stage {i+1}: {stage_type}({stage.name})")

        print("\n" + "-" * 70)
        print("EVOLVED AGENT INSTRUCTIONS:")
        print("-" * 70)

        # In evolve_workflow(), evolved_components uses qualified names
        for qualified_name, instruction in result.evolved_components.items():
            print(f"\n>>> {qualified_name.upper()} <<<")
            print("-" * 70)
            safe_print(instruction)

        print("\n" + "=" * 70)
        logger.info("example.nested_workflow.success")

    except Exception as e:
        logger.error("example.nested_workflow.failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
