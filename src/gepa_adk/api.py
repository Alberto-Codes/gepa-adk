"""Public API functions for gepa-adk evolution engine.

This module provides high-level async functions for evolving agent instructions
using the GEPA (Generalized Evolutionary Prompt-programming Architecture) approach.

Note:
    The public API exposes evolve() and evolve_sync() as primary entry points.
    All async functions should be awaited. For synchronous usage in scripts or
    notebooks, use evolve_sync() which handles event loop management internally.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from pydantic import BaseModel, ValidationError

from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.adapters.critic_scorer import CriticScorer
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.adapters.workflow import find_llm_agents
from gepa_adk.domain.exceptions import (
    ConfigurationError,
    MissingScoreFieldError,
    OutputParseError,
    SchemaValidationError,
    WorkflowEvolutionError,
)
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    MultiAgentEvolutionResult,
)
from gepa_adk.domain.types import TrajectoryConfig
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.scorer import Scorer

logger = structlog.get_logger()


class SchemaBasedScorer:
    """Scorer that extracts scores from agent's structured output_schema.

    When an agent has an output_schema, its output is structured JSON.
    This scorer parses that JSON and extracts a "score" field.

    Attributes:
        output_schema (type[BaseModel]): The Pydantic BaseModel schema class
            from agent.output_schema. Must contain a "score" field.

    Examples:
        Basic usage:

        ```python
        from pydantic import BaseModel, Field
        from google.adk.agents import LlmAgent
        from gepa_adk.api import SchemaBasedScorer


        class OutputSchema(BaseModel):
            score: float = Field(ge=0.0, le=1.0)
            result: str


        agent = LlmAgent(
            name="agent",
            model="gemini-2.0-flash",
            output_schema=OutputSchema,
        )

        scorer = SchemaBasedScorer(output_schema=OutputSchema)
        score, metadata = await scorer.async_score(
            input_text="test",
            output='{"score": 0.8, "result": "good"}',
        )
        ```

    Note:
        Implements Scorer protocol. Requires output_schema to have a "score"
        field. If score field is missing, raises MissingScoreFieldError.
    """

    def __init__(self, output_schema: type[BaseModel]) -> None:
        """Initialize schema-based scorer.

        Args:
            output_schema: Pydantic BaseModel class from agent.output_schema.

        Raises:
            ConfigurationError: If output_schema doesn't have a "score" field.
        """
        self.output_schema = output_schema

        # Verify schema has score field
        if (
            not hasattr(output_schema, "model_fields")
            or "score" not in output_schema.model_fields
        ):
            raise ConfigurationError(
                f"output_schema {output_schema.__name__} must have a 'score' field",
                field="output_schema",
                value=output_schema.__name__,
                constraint="must have 'score' field",
            )

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output synchronously.

        Args:
            input_text: The input provided to the agent.
            output: The agent's structured JSON output.
            expected: Optional expected output (not used for schema-based scoring).

        Returns:
            Tuple of (score, metadata) where score is extracted from output JSON
            and metadata contains all other fields from the schema.

        Raises:
            OutputParseError: If output cannot be parsed as JSON.
            SchemaValidationError: If output doesn't match the schema.
            MissingScoreFieldError: If score field is null in parsed output.

        Examples:
            Basic scoring with JSON output:

            ```python
            scorer = SchemaBasedScorer(output_schema=MySchema)
            score, metadata = scorer.score(
                input_text="What is 2+2?",
                output='{"score": 0.9, "result": "4"}',
            )
            # score == 0.9, metadata == {"result": "4"}
            ```

        Note:
            Operates synchronously by parsing JSON and extracting the score field.
            The expected parameter is ignored for schema-based scoring.
        """
        try:
            # Parse JSON output
            parsed = json.loads(output)
            # Parse with Pydantic schema for validation
            schema_instance = self.output_schema.model_validate(parsed)

            # Extract score - schema validated in __init__ has "score" field,
            # and model_validate succeeded, so score attribute exists.
            # The value could still be None if schema allows nullable scores.
            score_value = schema_instance.score
            if score_value is None:
                raise MissingScoreFieldError(
                    f"output_schema {self.output_schema.__name__} has score=None; "
                    "score must be a numeric value",
                    parsed_output=parsed,
                )

            score = float(score_value)

            # Build metadata from all other fields
            metadata = schema_instance.model_dump(exclude={"score"})

            return score, metadata

        except json.JSONDecodeError as e:
            raise OutputParseError(
                f"Failed to parse output as JSON: {e}",
                raw_output=output,
                parse_error=str(e),
                cause=e,
            ) from e
        except ValidationError as e:
            raise SchemaValidationError(
                f"Output does not match schema {self.output_schema.__name__}: {e}",
                raw_output=output,
                validation_error=str(e),
                cause=e,
            ) from e

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output asynchronously.

        Args:
            input_text: The input provided to the agent.
            output: The agent's structured JSON output.
            expected: Optional expected output (not used for schema-based scoring).

        Returns:
            Tuple of (score, metadata) where score is extracted from output JSON
            and metadata contains all other fields from the schema.

        Raises:
            OutputParseError: If output cannot be parsed as JSON.
            SchemaValidationError: If output doesn't match the schema.
            MissingScoreFieldError: If score field is null in parsed output.

        Examples:
            Async scoring with JSON output:

            ```python
            scorer = SchemaBasedScorer(output_schema=MySchema)
            score, metadata = await scorer.async_score(
                input_text="What is 2+2?",
                output='{"score": 0.9, "result": "4"}',
            )
            # score == 0.9, metadata == {"result": "4"}
            ```

        Note:
            Operates by delegating to synchronous score() since JSON parsing
            does not require async I/O operations.
        """
        # Schema-based scoring is synchronous (just JSON parsing)
        return self.score(input_text, output, expected)


def _validate_dataset(
    dataset: list[dict[str, Any]],
    name: str,
    *,
    allow_empty: bool = False,
) -> None:
    """Validate a dataset has proper structure.

    Args:
        dataset: The dataset to validate.
        name: Name of the dataset for error messages (e.g., "trainset", "valset").
        allow_empty: If True, allows empty datasets. Defaults to False.

    Raises:
        ConfigurationError: If dataset is invalid (empty when not allowed,
            contains non-dict items, or items missing 'input' key).

    Note:
        Shared validation logic for trainset and valset to avoid duplication.
    """
    if not allow_empty and not dataset:
        raise ConfigurationError(
            f"{name} cannot be empty",
            field=name,
            value=len(dataset),
            constraint="must be non-empty list",
        )

    for i, example in enumerate(dataset):
        if not isinstance(example, dict):
            raise ConfigurationError(
                f"{name}[{i}] must be a dict, got {type(example).__name__}",
                field=f"{name}[{i}]",
                value=type(example).__name__,
                constraint="must be dict",
            )
        if "input" not in example:
            raise ConfigurationError(
                f"{name}[{i}] must have 'input' key",
                field=f"{name}[{i}]",
                value=list(example.keys()),
                constraint="must contain 'input' key",
            )


def _validate_evolve_inputs(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
) -> None:
    """Validate inputs for evolve() function.

    Args:
        agent: The ADK agent to validate.
        trainset: The training set to validate.

    Raises:
        ConfigurationError: If agent is not a valid LlmAgent instance or
            trainset is empty or missing required keys.

    Note:
        Validates that agent is an LlmAgent instance and trainset is
        non-empty with each example having an "input" key.
    """
    # Validate agent type
    if not isinstance(agent, LlmAgent):
        raise ConfigurationError(
            f"agent must be an LlmAgent instance, got {type(agent).__name__}",
            field="agent",
            value=type(agent).__name__,
            constraint="must be LlmAgent",
        )

    # Validate trainset format
    _validate_dataset(trainset, "trainset", allow_empty=False)


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

    # Find all LlmAgents in the workflow recursively up to max_depth (US3)
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


async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: Any | None = None,
) -> EvolutionResult:
    """Evolve an ADK agent's instruction.

    Optimizes the instruction for a single ADK agent using evolutionary
    optimization. The agent's instruction is iteratively improved based on
    performance on the training set.

    Args:
        agent: The ADK LlmAgent to evolve.
        trainset: Training examples [{"input": "...", "expected": "..."}].
        valset: Optional validation examples for held-out evaluation.
        critic: Optional ADK agent for scoring (uses schema scoring if None).
        reflection_agent: Optional ADK agent for proposals (uses LiteLLM if None).
        config: Evolution configuration (uses defaults if None).
        trajectory_config: Trajectory capture settings (uses defaults if None).
        state_guard: Optional state token preservation settings.

    Returns:
        EvolutionResult with evolved_instruction and metrics.

    Raises:
        ConfigurationError: If invalid parameters provided.
        EvolutionError: If evolution fails during execution.

    Examples:
        Basic usage with output_schema:

        ```python
        from pydantic import BaseModel, Field
        from google.adk.agents import LlmAgent
        from gepa_adk import evolve


        class OutputSchema(BaseModel):
            answer: str
            score: float = Field(ge=0.0, le=1.0)


        agent = LlmAgent(
            name="assistant",
            model="gemini-2.0-flash",
            instruction="You are a helpful assistant.",
            output_schema=OutputSchema,
        )

        trainset = [
            {"input": "What is 2+2?", "expected": "4"},
            {"input": "What is the capital of France?", "expected": "Paris"},
        ]

        result = await evolve(agent, trainset)
        print(f"Evolved instruction: {result.evolved_instruction}")
        ```

        With critic agent:

        ```python
        from pydantic import BaseModel, Field
        from google.adk.agents import LlmAgent
        from gepa_adk import evolve


        class CriticOutput(BaseModel):
            score: float = Field(ge=0.0, le=1.0)


        critic = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Score the response quality.",
            output_schema=CriticOutput,
        )

        result = await evolve(agent, trainset, critic=critic)
        ```
    """
    # Validate inputs
    _validate_evolve_inputs(agent, trainset)

    # Warn if reflection_agent is provided (not yet implemented)
    if reflection_agent is not None:
        logger.warning(
            "evolve.reflection_agent.not_implemented",
            agent_name=agent.name,
            message="reflection_agent not yet implemented, using default proposer",
        )

    # Log evolution start
    logger.info(
        "evolve.start",
        agent_name=agent.name,
        trainset_size=len(trainset),
        valset_size=len(valset) if valset else 0,
        has_critic=critic is not None,
        has_reflection_agent=reflection_agent is not None,
        has_state_guard=state_guard is not None,
    )

    # Build scorer
    scorer: Scorer
    if critic:
        scorer = CriticScorer(critic_agent=critic)
    elif hasattr(agent, "output_schema") and agent.output_schema is not None:
        # Use schema-based scorer when agent has output_schema
        scorer = SchemaBasedScorer(output_schema=agent.output_schema)
    else:
        raise ConfigurationError(
            "Either critic must be provided or agent must have output_schema",
            field="critic",
            value=None,
            constraint="must provide critic or agent.output_schema",
        )

    # Create adapter
    adapter = ADKAdapter(
        agent=agent,
        scorer=scorer,
        trajectory_config=trajectory_config,
    )

    # Create initial candidate from agent instruction
    initial_candidate = Candidate(components={"instruction": str(agent.instruction)})

    # Create engine
    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=config or EvolutionConfig(),
        initial_candidate=initial_candidate,
        batch=trainset,
    )

    # Run evolution
    result = await engine.run()

    # Evaluate on validation set if provided (MVP: separate evaluation, doesn't affect evolution)
    valset_score: float | None = None
    if valset:
        # Validate valset format using shared helper
        _validate_dataset(valset, "valset", allow_empty=False)

        # Create final candidate from evolved instruction
        final_candidate = Candidate(
            components={"instruction": result.evolved_instruction}
        )

        # Evaluate final candidate on validation set
        valset_eval_batch = await adapter.evaluate(
            valset,
            final_candidate.components,
            capture_traces=False,
        )
        valset_score = sum(valset_eval_batch.scores) / len(valset_eval_batch.scores)

        logger.info(
            "evolve.valset.evaluated",
            agent_name=agent.name,
            valset_size=len(valset),
            valset_score=valset_score,
        )

    # Apply state guard if provided (for token preservation)
    if state_guard is not None:
        # TODO: Implement state guard validation when StateGuard is available
        # For now, just log that it was provided
        logger.debug(
            "evolve.state_guard.provided",
            agent_name=agent.name,
            message="state_guard parameter provided but validation not yet implemented",
        )

    # Log evolution completion
    logger.info(
        "evolve.complete",
        agent_name=agent.name,
        original_score=result.original_score,
        final_score=result.final_score,
        improvement=result.improvement,
        total_iterations=result.total_iterations,
        valset_score=valset_score,
    )

    # Return result with valset_score (creates new instance since frozen)
    return EvolutionResult(
        original_score=result.original_score,
        final_score=result.final_score,
        evolved_instruction=result.evolved_instruction,
        iteration_history=result.iteration_history,
        total_iterations=result.total_iterations,
        valset_score=valset_score,
    )


def evolve_sync(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    **kwargs: Any,
) -> EvolutionResult:
    """Synchronous wrapper for evolve().

    Runs the async evolve() function in a blocking manner.
    Handles nested event loops automatically (Jupyter compatible).

    Args:
        agent: The ADK LlmAgent to evolve.
        trainset: Training examples.
        **kwargs: Optional keyword arguments passed to evolve().

    Keyword Args:
        valset: Optional validation examples for held-out evaluation.
        critic: Optional ADK agent for scoring.
        reflection_agent: Optional ADK agent for proposals (not yet implemented).
        config: EvolutionConfig for customizing evolution parameters.
        trajectory_config: TrajectoryConfig for trace capture settings.
        state_guard: Optional state token preservation settings.

    Returns:
        EvolutionResult with evolved_instruction and metrics.

    Raises:
        ConfigurationError: If invalid parameters provided.
        EvolutionError: If evolution fails during execution.

    Examples:
        Basic usage in a script:

        ```python
        from pydantic import BaseModel, Field
        from google.adk.agents import LlmAgent
        from gepa_adk import evolve_sync


        class OutputSchema(BaseModel):
            answer: str
            score: float = Field(ge=0.0, le=1.0)


        agent = LlmAgent(
            name="assistant",
            model="gemini-2.0-flash",
            instruction="You are a helpful assistant.",
            output_schema=OutputSchema,
        )

        trainset = [
            {"input": "What is 2+2?", "expected": "4"},
        ]

        result = evolve_sync(agent, trainset)
        print(f"Evolved: {result.evolved_instruction}")
        ```

        With configuration:

        ```python
        from gepa_adk import evolve_sync, EvolutionConfig

        config = EvolutionConfig(max_iterations=50)
        result = evolve_sync(agent, trainset, config=config)
        ```

    Note:
        Works in both scripts and Jupyter notebooks. Automatically handles
        nested event loops using nest_asyncio when needed.
    """
    import asyncio

    try:
        # Try standard asyncio.run() first
        return asyncio.run(evolve(agent, trainset, **kwargs))
    except RuntimeError as e:
        # Handle nested event loop case (e.g., Jupyter notebooks)
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            # Use nest_asyncio for nested event loops
            try:
                import nest_asyncio

                nest_asyncio.apply()
                # Now we can use asyncio.run() even in nested context
                return asyncio.run(evolve(agent, trainset, **kwargs))
            except ImportError:
                # We're here because asyncio.run() failed due to running event loop.
                # Without nest_asyncio, we can't handle nested event loops.
                raise RuntimeError(
                    "nest_asyncio is required for nested event loops. "
                    "Install it with: uv add nest_asyncio"
                ) from e
        raise
