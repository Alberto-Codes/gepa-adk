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
import re
from typing import Any, Protocol, cast

import structlog
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.apps.app import App
from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from pydantic import BaseModel, ValidationError

from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.adapters.candidate_selector import create_candidate_selector
from gepa_adk.adapters.component_handlers import get_handler
from gepa_adk.adapters.component_selector import create_component_selector
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
from gepa_adk.domain.types import (
    COMPONENT_OUTPUT_SCHEMA,
    DEFAULT_COMPONENT_NAME,
    SchemaConstraints,
    TrajectoryConfig,
)
from gepa_adk.engine import (
    REFLECTION_INSTRUCTION,
    AsyncGEPAEngine,
    AsyncReflectiveMutationProposer,
    create_adk_reflection_fn,
)
from gepa_adk.ports.agent_executor import AgentExecutorProtocol
from gepa_adk.ports.scorer import Scorer
from gepa_adk.ports.selector import (
    CandidateSelectorProtocol,
    ComponentSelectorProtocol,
)
from gepa_adk.utils import StateGuard
from gepa_adk.utils.schema_utils import serialize_pydantic_schema

logger = structlog.get_logger(__name__)

# Patterns for models natively supported by ADK (from Gemini.supported_models())
_NATIVE_ADK_MODEL_PATTERNS = [
    r"gemini-.*",
    r"model-optimizer-.*",
    r"projects/.+/locations/.+/endpoints/.+",
    r"projects/.+/locations/.+/publishers/google/models/gemini.+",
]


def _resolve_model_for_agent(model_string: str) -> str | BaseLlm:
    """Resolve a model string to the appropriate type for LlmAgent.

    For models natively supported by ADK (Gemini, Vertex AI endpoints),
    returns the string to leverage ADK's optimized native integration.
    For other models (Ollama, OpenAI via LiteLLM, etc.), wraps with LiteLlm
    to bypass ADK's limited registry.

    This function exists because ADK's LLMRegistry only recognizes a subset
    of LiteLLM-supported providers. Without wrapping, models like
    "ollama_chat/gpt-oss:20b" fail with "Model not found" errors.

    Args:
        model_string: Model identifier string (e.g., "gemini-2.5-flash",
            "ollama_chat/gpt-oss:20b", "openai/gpt-4o").

    Returns:
        Either the original string (for native ADK models) or a LiteLlm
        wrapper instance (for LiteLLM-backed providers).

    Examples:
        >>> _resolve_model_for_agent("gemini-2.5-flash")
        "gemini-2.5-flash"  # Native ADK handling

        >>> _resolve_model_for_agent("ollama_chat/gpt-oss:20b")
        LiteLlm(model="ollama_chat/gpt-oss:20b")  # Wrapped

    Note:
        Selectively wraps models to preserve ADK's native Gemini optimizations
        while enabling full LiteLLM provider support for non-native models.
    """
    for pattern in _NATIVE_ADK_MODEL_PATTERNS:
        if re.fullmatch(pattern, model_string):
            return model_string
    return LiteLlm(model=model_string)


class _ScoreSchema(Protocol):
    """Protocol for validated schemas that expose a numeric score attribute.

    Used internally to make score extraction type-safe after schema validation.
    """

    score: float | int | None


def _apply_state_guard_validation(
    state_guard: StateGuard | None,
    original_component_text: str,
    evolved_component_text: str,
    agent_name: str,
) -> str:
    """Apply StateGuard validation to evolved component_text.

    Validates and repairs the evolved component_text using StateGuard if provided.
    Logs the validation result (modified or unchanged).

    Args:
        state_guard: StateGuard instance to apply validation, or None to skip.
        original_component_text: The original component_text before evolution.
        evolved_component_text: The evolved component_text to validate.
        agent_name: Name of the agent (for logging).

    Returns:
        The validated component_text (may be modified if tokens were repaired/escaped).

    Note:
        Shared across evolve(), evolve_group(), and evolve_workflow()
        to ensure consistent StateGuard validation behavior.
    """
    if state_guard is None:
        return evolved_component_text

    validated = state_guard.validate(original_component_text, evolved_component_text)

    if validated != evolved_component_text:
        repaired_tokens, escaped_tokens = state_guard.get_validation_summary(
            original_component_text,
            evolved_component_text,
        )
        logger.info(
            "evolve.state_guard.applied",
            agent_name=agent_name,
            component_text_modified=True,
            repaired_tokens=repaired_tokens,
            escaped_tokens=escaped_tokens,
            repaired=bool(repaired_tokens),
            escaped=bool(escaped_tokens),
        )
    else:
        logger.debug(
            "evolve.state_guard.no_changes",
            agent_name=agent_name,
        )

    return validated


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
            model="gemini-2.5-flash",
            output_schema=OutputSchema,
        )

        scorer = SchemaBasedScorer(output_schema=OutputSchema)
        score, metadata = await scorer.async_score(
            input_text="test",
            output='{"score": 0.8, "result": "good"}',
        )
        ```

    Note:
        Adheres to Scorer protocol. Requires output_schema to have a "score"
        field. If score field is missing, raises MissingScoreFieldError.
    """

    def __init__(self, output_schema: type[BaseModel]) -> None:
        """Initialize schema-based scorer.

        Args:
            output_schema: Pydantic BaseModel class from agent.output_schema.

        Raises:
            ConfigurationError: If output_schema doesn't have a "score" field.

        Note:
            Checks that the schema contains a "score" field during initialization.
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
            score_value = cast(_ScoreSchema, schema_instance).score
            if score_value is None:
                raise MissingScoreFieldError(
                    f"output_schema {self.output_schema.__name__} has score=None; "
                    "score must be a numeric value",
                    parsed_output=parsed,
                )

            # Explicit cast since we've validated it's not None
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


def _resolve_evolution_services(
    runner: Runner | None,
    app: App | None,
    session_service: BaseSessionService | None,
) -> tuple[BaseSessionService, Any]:
    """Extract services from runner/app with precedence: runner > app > session_service > default.

    Implements FR-004 (precedence rules) from spec.md. When multiple configuration
    sources are provided, this function determines which services to use based on
    a clear precedence order.

    Args:
        runner: Optional ADK Runner instance. If provided, its session_service
            and artifact_service are extracted and used.
        app: Optional ADK App instance. Note that App does not hold services
            directly; it's a configuration container. If provided with
            session_service param, uses that; otherwise creates default.
        session_service: Optional session service passed directly. Used when
            neither runner nor app provides a session_service.

    Returns:
        Tuple of (session_service, artifact_service). artifact_service may be
        None if not provided by runner.

    Note:
        - If both runner and app are provided, a warning is logged and runner
          takes precedence (handled by caller via T009).
        - App does not hold services directly per ADK design; it holds
          configuration (name, plugins, etc.). Services are provided to Runner.
        - artifact_service is extracted for future use; current evolution
          operations do not generate artifacts (FR-006/FR-009 in spec.md).
    """
    # Precedence: runner > app > session_service > default
    if runner is not None:
        # Extract services from Runner (FR-002, FR-008, FR-009)
        return runner.session_service, runner.artifact_service

    if app is not None:
        # App doesn't hold services directly (research.md Section 1)
        # Use provided session_service or create default
        resolved_session = session_service or InMemorySessionService()
        return resolved_session, None

    # No runner or app - use session_service param or default (FR-012)
    return session_service or InMemorySessionService(), None


def _validate_component_name(name: str, context: str) -> None:
    """Validate a component name is a valid identifier.

    Component names must be non-empty strings that are valid Python identifiers
    (alphanumeric characters and underscores, not starting with a digit).

    Args:
        name: Component name to validate.
        context: Description of where this name is used (for error messages).

    Raises:
        ConfigurationError: If the component name is invalid.

    Note:
        Safeguards component names for use as dictionary keys and in
        logging/debugging contexts.
    """
    if not name:
        raise ConfigurationError(
            f"{context}: component name cannot be empty",
            field="component_name",
            value=name,
            constraint="must be non-empty string",
        )
    if not name.isidentifier():
        raise ConfigurationError(
            f"{context}: component name '{name}' is not a valid identifier. "
            "Component names must be alphanumeric with underscores, not starting with a digit.",
            field="component_name",
            value=name,
            constraint="must be valid Python identifier",
        )


def _validate_dataset(
    dataset: list[dict[str, Any]],
    name: str,
    *,
    allow_empty: bool = False,
    required_keys: set[str] | None = None,
) -> None:
    """Validate a dataset has proper structure.

    Args:
        dataset: The dataset to validate.
        name: Name of the dataset for error messages (e.g., "trainset", "valset").
        allow_empty: If True, allows empty datasets. Defaults to False.
        required_keys: Required keys each example must include. Defaults to None,
            which means examples must have either 'input' or 'videos' (or both).

    Raises:
        ConfigurationError: If dataset is invalid (empty when not allowed,
            contains non-dict items, or items missing required keys).

    Note:
        Shared validation logic for trainset and valset to avoid duplication.
        Examples can contain 'input' (text), 'videos' (list of paths), or both.
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

        # Validate 'input' OR 'videos' present (at least one required)
        has_input = "input" in example
        has_videos = "videos" in example

        if not has_input and not has_videos:
            raise ConfigurationError(
                f"{name}[{i}] must have 'input' or 'videos' field",
                field=f"{name}[{i}]",
                value=list(example.keys()),
                constraint="must contain 'input' or 'videos' key",
            )

        # Validate 'videos' field structure if present
        if has_videos:
            videos = example["videos"]
            if not isinstance(videos, list):
                raise ConfigurationError(
                    f"{name}[{i}].videos must be a list",
                    field=f"{name}[{i}].videos",
                    value=type(videos).__name__,
                    constraint="must be list",
                )
            if not videos:
                raise ConfigurationError(
                    f"{name}[{i}].videos cannot be empty",
                    field=f"{name}[{i}].videos",
                    value=videos,
                    constraint="must be non-empty list",
                )
            for j, video_path in enumerate(videos):
                if not isinstance(video_path, str):
                    raise ConfigurationError(
                        f"{name}[{i}].videos[{j}] must be a string",
                        field=f"{name}[{i}].videos[{j}]",
                        value=type(video_path).__name__,
                        constraint="must be string",
                    )

        # Validate additional required_keys if specified
        if required_keys:
            missing_keys = required_keys - set(example.keys())
            if missing_keys:
                raise ConfigurationError(
                    f"{name}[{i}] missing required keys: {sorted(missing_keys)}",
                    field=f"{name}[{i}]",
                    value=list(example.keys()),
                    constraint=f"must include keys {sorted(required_keys)}",
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
        Safeguards that agent is an LlmAgent instance and trainset is
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
    agents: dict[str, LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    components: dict[str, list[str]] | None = None,
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,
    reflection_agent: LlmAgent | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    workflow: SequentialAgent | LoopAgent | ParallelAgent | None = None,
    session_service: BaseSessionService | None = None,
    app: App | None = None,
    runner: Runner | None = None,
) -> MultiAgentEvolutionResult:
    """Evolve multiple agents together with per-agent component configuration.

    Optimizes specified components for each agent by targeting the primary
    agent's output score. When share_session=True, agents execute sequentially
    with shared session state, enabling later agents to access earlier
    agents' outputs via template strings.

    Args:
        agents: Named ADK agents to evolve together as dict mapping agent
            names to LlmAgent instances. Must have at least one agent.
        primary: Name of the agent whose output is used for scoring.
            Must match one of the agent names in the dict.
        trainset: Training examples for evaluation. Each example should
            have an "input" key and optionally an "expected" key.
        components: Per-agent component configuration mapping agent names
            to lists of component names to evolve. If None, defaults to
            evolving "instruction" for all agents. Use empty list to
            exclude an agent from evolution. Available component names:
            "instruction", "output_schema", "generate_content_config".
        critic: Optional critic agent for scoring. If None, the primary
            agent must have an output_schema for schema-based scoring.
        share_session: Whether agents share session state during
            execution. When True (default), uses SequentialAgent.
            When False, agents execute with isolated sessions.
        config: Evolution configuration. If None, uses EvolutionConfig
            defaults.
        state_guard: Optional StateGuard instance for validating and
            repairing state injection tokens in evolved instructions.
        component_selector: Optional selector instance or selector name for
            choosing which components to update.
        reflection_agent: Optional ADK agent for proposals. If None, creates a
            default reflection agent using config.reflection_model.
        trajectory_config: Trajectory capture settings (uses defaults if None).
        workflow: Optional original workflow structure to preserve during
            evaluation. When provided, LoopAgent iterations and ParallelAgent
            concurrency are preserved instead of flattening to SequentialAgent.
            Used internally by evolve_workflow(); not typically set directly.
        session_service: Optional ADK session service for state management.
            If None (default), creates an InMemorySessionService internally.
            Pass a custom service (e.g., SqliteSessionService, DatabaseSessionService)
            to persist sessions alongside other agent executions in a shared database.
        app: Optional ADK App instance. When provided, evolution uses the app's
            configuration. Note that App does not hold services directly; pass
            a Runner for service extraction, or combine with session_service param.
        runner: Optional ADK Runner instance. When provided, evolution extracts
            and uses the runner's session_service for all agent executions
            (evolved agents, critic, and reflection agent). Takes precedence
            over both app and session_service parameters. This enables seamless
            integration with existing ADK infrastructure.

    Returns:
        MultiAgentEvolutionResult containing evolved_components dict
        mapping qualified component names (agent.component format) to their
        optimized values, along with score metrics and iteration history.

    Raises:
        MultiAgentValidationError: If agents dict is empty, primary agent
            not found, or no scorer and primary lacks output_schema.
        ValueError: If components mapping contains unknown agents, unknown
            component handlers, or is missing entries for agents.
        EvolutionError: If evolution fails during execution.

    Examples:
        Basic usage with per-agent components (API v0.3.x):

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk import evolve_group

        generator = LlmAgent(
            name="generator",
            model="gemini-2.5-flash",
            instruction="Generate code based on the requirement.",
        )
        critic = LlmAgent(
            name="critic",
            model="gemini-2.5-flash",
            instruction="Review the code in {generator_output}.",
        )
        validator = LlmAgent(
            name="validator",
            model="gemini-2.5-flash",
            instruction="Validate the reviewed code.",
            output_schema=ValidationResult,
        )

        result = await evolve_group(
            agents={
                "generator": generator,
                "critic": critic,
                "validator": validator,
            },
            primary="validator",
            trainset=training_data,
            components={
                "generator": ["instruction", "output_schema"],
                "critic": ["instruction"],
                "validator": ["instruction"],
            },
        )

        # Access evolved components using qualified names
        print(result.evolved_components["generator.instruction"])
        print(result.evolved_components["critic.instruction"])
        print(result.evolved_components["validator.instruction"])
        ```

        Exclude an agent from evolution:

        ```python
        result = await evolve_group(
            agents={"generator": gen, "static_validator": val},
            primary="generator",
            trainset=training_data,
            components={
                "generator": ["instruction"],
                "static_validator": [],  # Excluded from evolution
            },
        )
        ```

        Using custom session service for persistence:

        ```python
        from google.adk.sessions import SqliteSessionService

        # Use SQLite for session persistence
        session_service = SqliteSessionService(db_path="evolution_sessions.db")

        result = await evolve_group(
            agents={"generator": gen, "critic": critic},
            primary="critic",
            trainset=training_data,
            session_service=session_service,  # Sessions persisted to SQLite
        )
        ```

        Using App/Runner for existing infrastructure integration:

        ```python
        from google.adk.runners import Runner
        from google.adk.sessions import DatabaseSessionService

        # Configure Runner with your production session service
        runner = Runner(
            app_name="my_app",
            agent=generator,  # Any agent from the group
            session_service=DatabaseSessionService(connection_string="..."),
        )

        # Evolution uses Runner's session_service for all operations
        result = await evolve_group(
            agents={"generator": gen, "refiner": ref},
            primary="refiner",
            trainset=training_data,
            runner=runner,  # Services extracted from runner
        )
        ```

    Note:
        Breaking change in v0.3.x: The `agents` parameter changed from
        `list[LlmAgent]` to `dict[str, LlmAgent]`. Candidate keys now use
        qualified names (agent.component) instead of {agent_name}_instruction.
    """
    # Validate agent names are valid identifiers (T012a)
    for agent_name in agents:
        _validate_component_name(
            agent_name,
            context="evolve_group agent",
        )

    # Default components: evolve "instruction" for all agents
    if components is None:
        components = {name: ["instruction"] for name in agents}

    # Capture original instructions for StateGuard validation
    original_instructions = {
        name: str(agent.instruction) for name, agent in agents.items()
    }

    # Log precedence warnings if multiple config sources provided (#227 T009)
    if runner is not None and app is not None:
        logger.warning(
            "evolve_group.precedence.runner_over_app",
            message="Both runner and app provided; using runner (runner takes precedence)",
            runner_app_name=runner.app_name,
            app_name=app.name,
        )

    # Resolve services using precedence rules: runner > app > session_service > default (#227)
    resolved_session_service, _artifact_service = _resolve_evolution_services(
        runner=runner,
        app=app,
        session_service=session_service,
    )

    # Create unified executor for consistent session management (FR-003)
    executor = AgentExecutor(session_service=resolved_session_service)

    # Build scorer with executor (FR-005)
    scorer = None
    if critic:
        scorer = CriticScorer(critic_agent=critic, executor=executor)

    # Resolve config for reflection_model
    resolved_config = config or EvolutionConfig()

    # Create reflection-based proposer with executor (FR-006)
    # Use provided reflection_agent or create a default one
    if reflection_agent is None:
        reflection_agent = LlmAgent(
            name="reflection_agent",
            model=_resolve_model_for_agent(resolved_config.reflection_model),
            instruction=resolved_config.reflection_prompt or REFLECTION_INSTRUCTION,
        )
    adk_reflection_fn = create_adk_reflection_fn(
        reflection_agent,
        executor=executor,
        session_service=resolved_session_service,
    )
    proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=adk_reflection_fn)

    # Create adapter with executor (FR-004)
    adapter = MultiAgentAdapter(
        agents=agents,
        primary=primary,
        components=components,
        scorer=scorer,
        share_session=share_session,
        session_service=resolved_session_service,
        trajectory_config=trajectory_config,
        proposer=proposer,
        executor=executor,
        workflow=workflow,  # Preserve workflow structure (#215)
    )

    # Build seed candidate using qualified names (agent.component format per ADR-012)
    primary_agent = agents[primary]
    # Extract all configured components using their handlers
    seed_candidate_components: dict[str, str] = {}
    for agent_name, comp_list in components.items():
        agent = agents[agent_name]
        for comp_name in comp_list:
            qualified_name = f"{agent_name}.{comp_name}"
            handler = get_handler(comp_name)
            seed_candidate_components[qualified_name] = handler.serialize(agent)
    # Add required "instruction" key for engine compatibility
    seed_candidate_components["instruction"] = str(primary_agent.instruction)
    initial_candidate = Candidate(components=seed_candidate_components)

    # Create engine
    resolved_component_selector: ComponentSelectorProtocol | None = None
    if component_selector is not None:
        if isinstance(component_selector, str):
            resolved_component_selector = create_component_selector(component_selector)
        else:
            resolved_component_selector = component_selector

    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=resolved_config,
        initial_candidate=initial_candidate,
        batch=trainset,
        component_selector=resolved_component_selector,
    )

    # Run evolution
    evolution_result = await engine.run()

    # Extract best candidate components from engine state using qualified names
    # The engine stores evolved_components from the candidate, which now uses
    # qualified names (agent.component format per ADR-012)
    evolved_components = _extract_evolved_components(
        evolution_result=evolution_result,
        seed_components=seed_candidate_components,
        agents=agents,
        components=components,
        primary=primary,
    )

    # Apply StateGuard validation to instruction components only
    if state_guard is not None:
        validated_components = {}
        for qualified_name, evolved_value in evolved_components.items():
            # Only apply StateGuard to instruction components
            if qualified_name.endswith(".instruction"):
                agent_name = qualified_name.rsplit(".", 1)[0]
                original_instruction = original_instructions.get(agent_name, "")
                validated_components[qualified_name] = _apply_state_guard_validation(
                    state_guard=state_guard,
                    original_component_text=original_instruction,
                    evolved_component_text=evolved_value,
                    agent_name=agent_name,
                )
            else:
                # Non-instruction components pass through unchanged
                validated_components[qualified_name] = evolved_value
        evolved_components = validated_components

    # Convert EvolutionResult to MultiAgentEvolutionResult
    return MultiAgentEvolutionResult(
        evolved_components=evolved_components,
        original_score=evolution_result.original_score,
        final_score=evolution_result.final_score,
        primary_agent=primary,
        iteration_history=evolution_result.iteration_history,
        total_iterations=evolution_result.total_iterations,
    )


def _extract_evolved_components(
    evolution_result: EvolutionResult,
    seed_components: dict[str, str],
    agents: dict[str, LlmAgent],
    components: dict[str, list[str]],
    primary: str,
) -> dict[str, str]:
    """Extract evolved component values for all agent-component pairs.

    Args:
        evolution_result: Evolution result from engine.
        seed_components: Initial candidate components with qualified names.
        agents: Dict of agents that were evolved (name -> LlmAgent).
        components: Per-agent component configuration.
        primary: Name of the primary agent.

    Returns:
        Dictionary mapping qualified names (agent.component) to their evolved values.

    Note:
        Uses qualified names (agent.component format per ADR-012) as keys.
        Extracts evolved components from the engine result, falling back to
        seed values for components that weren't evolved.
    """
    evolved_components: dict[str, str] = {}

    # Extract evolved components using qualified names
    for agent_name, comp_list in components.items():
        agent = agents[agent_name]
        for comp_name in comp_list:
            qualified_name = f"{agent_name}.{comp_name}"
            if qualified_name in evolution_result.evolved_components:
                # Use evolved value from engine
                evolved_components[qualified_name] = (
                    evolution_result.evolved_components[qualified_name]
                )
            elif (
                DEFAULT_COMPONENT_NAME in evolution_result.evolved_components
                and agent_name == primary
                and comp_name == "instruction"
            ):
                # Fallback for single-agent evolution (key is just the default component)
                evolved_components[qualified_name] = (
                    evolution_result.evolved_components[DEFAULT_COMPONENT_NAME]
                )
            else:
                # Use seed value as fallback (component wasn't evolved)
                if comp_name == "instruction":
                    evolved_components[qualified_name] = seed_components.get(
                        qualified_name, str(agent.instruction)
                    )
                else:
                    evolved_components[qualified_name] = seed_components.get(
                        qualified_name, ""
                    )

    return evolved_components


async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,
    round_robin: bool = False,
    components: dict[str, list[str]] | None = None,
    session_service: BaseSessionService | None = None,
    app: App | None = None,
    runner: Runner | None = None,
) -> MultiAgentEvolutionResult:
    """Evolve LlmAgents within a workflow agent structure.

    Discovers all LlmAgent instances within a workflow (SequentialAgent,
    LoopAgent, or ParallelAgent) and evolves them while preserving the
    workflow structure. Uses shared session state to maintain workflow
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
            Limits how deeply nested workflow structures are traversed.
        config: Evolution configuration. If None, uses EvolutionConfig defaults.
        state_guard: Optional StateGuard instance for validating and
            repairing state injection tokens in evolved component_text.
        component_selector: Optional selector instance or selector name for
            choosing which components to update.
        round_robin: If False (default), only the first discovered agent's
            instruction is evolved across all iterations. If True, all agents'
            instructions are evolved in round-robin fashion (the engine cycles
            through agents each iteration). Ignored when components is provided.
        components: Optional per-agent component configuration mapping agent
            names to lists of component names to evolve. When provided, takes
            precedence over round_robin. Use empty list to exclude an agent.
        session_service: Optional ADK session service for state management.
            If None (default), creates an InMemorySessionService internally.
            Pass a custom service (e.g., SqliteSessionService, DatabaseSessionService)
            to persist sessions alongside other agent executions in a shared database.
        app: Optional ADK App instance. When provided, evolution uses the app's
            configuration. Note that App does not hold services directly; pass
            a Runner for service extraction, or combine with session_service param.
        runner: Optional ADK Runner instance. When provided, evolution extracts
            and uses the runner's session_service for all agent executions
            (evolved agents, critic, and reflection agent). Takes precedence
            over both app and session_service parameters. This enables seamless
            integration with existing ADK infrastructure.

    Returns:
        MultiAgentEvolutionResult containing evolved_components dict mapping
        agent names to their optimized component_text, along with score
        metrics and iteration history.

    Raises:
        WorkflowEvolutionError: If workflow contains no LlmAgents.
        MultiAgentValidationError: If primary agent not found or no scorer
            available.
        EvolutionError: If evolution fails during execution.

    Examples:
        Default behavior (evolve first agent only):

        ```python
        from google.adk.agents import LlmAgent, SequentialAgent
        from gepa_adk import evolve_workflow

        generator = LlmAgent(name="generator", instruction="Generate code")
        refiner = LlmAgent(name="refiner", instruction="Refine code")
        writer = LlmAgent(name="writer", instruction="Write docs")
        pipeline = SequentialAgent(
            name="Pipeline", sub_agents=[generator, refiner, writer]
        )

        # Only generator.instruction is evolved across all iterations
        result = await evolve_workflow(workflow=pipeline, trainset=trainset)
        ```

        Round-robin evolution (evolve all agents):

        ```python
        # All agents are evolved in round-robin: generator -> refiner -> writer -> ...
        result = await evolve_workflow(
            workflow=pipeline,
            trainset=trainset,
            round_robin=True,
        )
        ```

        Explicit components override (takes precedence over round_robin):

        ```python
        # Only generator and writer are evolved; refiner is excluded
        result = await evolve_workflow(
            workflow=pipeline,
            trainset=trainset,
            components={
                "generator": ["instruction"],
                "writer": ["instruction"],
                "refiner": [],  # Excluded
            },
        )
        ```

        Using custom session service for persistence:

        ```python
        from google.adk.sessions import SqliteSessionService

        # Persist workflow evolution sessions to SQLite
        session_service = SqliteSessionService(db_path="workflow_sessions.db")

        result = await evolve_workflow(
            workflow=pipeline,
            trainset=trainset,
            session_service=session_service,
        )
        ```

        Using App/Runner for existing infrastructure integration:

        ```python
        from google.adk.runners import Runner
        from google.adk.sessions import DatabaseSessionService

        # Configure Runner with your production session service
        runner = Runner(
            app_name="my_workflow_app",
            agent=pipeline,  # The workflow agent
            session_service=DatabaseSessionService(connection_string="..."),
        )

        # Evolution uses Runner's session_service for all operations
        result = await evolve_workflow(
            workflow=pipeline,
            trainset=trainset,
            runner=runner,  # Services extracted from runner
        )
        ```

    Note:
        Supports workflow agents (SequentialAgent, LoopAgent, ParallelAgent)
        with recursive traversal and depth limiting via max_depth parameter.
        Handles nested structures. LoopAgent and ParallelAgent configurations
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

    # Convert list to dict for evolve_group (API v0.3.x)
    agents_dict = {agent.name: agent for agent in llm_agents}

    # Build components dict based on round_robin flag
    # Explicit components parameter takes precedence over round_robin
    resolved_components: dict[str, list[str]] | None = None
    if components is not None:
        # Explicit components provided - use as-is
        resolved_components = components
        logger.debug(
            "Using explicit components",
            workflow_name=workflow.name,
            components=list(components.keys()),
        )
    elif round_robin:
        # round_robin=True: evolve all agents
        resolved_components = {agent.name: ["instruction"] for agent in llm_agents}
        logger.debug(
            "Using round_robin mode - evolving all agents",
            workflow_name=workflow.name,
            agents=[agent.name for agent in llm_agents],
        )
    else:
        # Default: evolve only the first agent
        first_agent = llm_agents[0]
        resolved_components = {first_agent.name: ["instruction"]}
        # Add empty lists for other agents (excluded from evolution)
        for agent in llm_agents[1:]:
            resolved_components[agent.name] = []
        logger.debug(
            "Using default mode - evolving first agent only",
            workflow_name=workflow.name,
            first_agent=first_agent.name,
        )

    # Delegate to evolve_group with share_session=True (FR-010)
    logger.debug(
        "Delegating to evolve_group",
        workflow_name=workflow.name,
        agent_count=len(llm_agents),
        primary=primary,
        share_session=True,
        round_robin=round_robin,
    )

    return await evolve_group(
        agents=agents_dict,
        primary=primary,
        trainset=trainset,
        components=resolved_components,
        critic=critic,
        share_session=True,  # FR-010: Always use shared session for workflow context
        config=config,
        state_guard=state_guard,
        component_selector=component_selector,
        workflow=workflow,  # Preserve workflow structure (#215)
        session_service=session_service,  # Pass through for persistence (#226)
        app=app,  # Pass through for App/Runner pattern (#227)
        runner=runner,  # Pass through for App/Runner pattern (#227)
    )


async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
    candidate_selector: CandidateSelectorProtocol | str | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,
    executor: AgentExecutorProtocol | None = None,
    components: list[str] | None = None,
    schema_constraints: SchemaConstraints | None = None,
    app: App | None = None,
    runner: Runner | None = None,
) -> EvolutionResult:
    """Evolve an ADK agent's instruction.

    Optimizes the instruction for a single ADK agent using evolutionary
    optimization. The agent's instruction is iteratively improved based on
    performance on the training set.

    Args:
        agent: The ADK LlmAgent to evolve.
        trainset: Training examples [{"input": "...", "expected": "..."}].
        valset: Optional validation examples used for scoring and acceptance.
            Defaults to the trainset when omitted.
        critic: Optional ADK agent for scoring (uses schema scoring if None).
        reflection_agent: Optional ADK agent for proposals. If None, creates a
            default reflection agent using config.reflection_model.
        config: Evolution configuration (uses defaults if None).
        trajectory_config: Trajectory capture settings (uses defaults if None).
        state_guard: Optional state token preservation settings.
        candidate_selector: Optional selector instance or selector name.
        component_selector: Optional selector instance or selector name for
            choosing which components to update.
        executor: Optional AgentExecutorProtocol implementation for unified
            agent execution. When provided, both the ADKAdapter and CriticScorer
            use this executor for consistent session management and execution.
            If None, creates an AgentExecutor automatically.
        components: List of component names to include in evolution. Supported:
            - "instruction": The agent's instruction text (default if None).
            - "output_schema": The agent's Pydantic output_schema (serialized).
            When None, defaults to ["instruction"]. Use ["output_schema"] with
            a schema reflection agent to evolve the output schema.
        schema_constraints: Optional SchemaConstraints for output_schema evolution.
            When provided, proposed schema mutations are validated against these
            constraints. Mutations that violate constraints (e.g., remove required
            fields) are rejected and the original schema is preserved.
        app: Optional ADK App instance. When provided, evolution uses the app's
            configuration. Note that App does not hold services directly; pass
            a Runner for service extraction, or combine with session_service param.
            See the App/Runner integration guide for details.
        runner: Optional ADK Runner instance. When provided, evolution extracts
            and uses the runner's session_service for all agent executions
            (evolved agents, critic, and reflection agent). Takes precedence
            over both app and executor parameters. This enables seamless
            integration with existing ADK infrastructure.

    Returns:
        EvolutionResult with evolved_components dict and metrics.

    Raises:
        ConfigurationError: If invalid parameters provided.
        EvolutionError: If evolution fails during execution.

    Note:
        Single-agent evolution with trainset reflection and valset scoring.

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
            model="gemini-2.5-flash",
            instruction="You are a helpful assistant.",
            output_schema=OutputSchema,
        )

        trainset = [
            {"input": "What is 2+2?", "expected": "4"},
            {"input": "What is the capital of France?", "expected": "Paris"},
        ]

        result = await evolve(agent, trainset)
        print(f"Evolved: {result.evolved_components['instruction']}")
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
            model="gemini-2.5-flash",
            instruction="Score the response quality.",
            output_schema=CriticOutput,
        )

        result = await evolve(agent, trainset, critic=critic)
        ```

        Evolving output_schema with schema reflection:

        ```python
        from gepa_adk.engine.reflection_agents import create_schema_reflection_agent

        # Create schema reflection agent with validation tool
        schema_reflector = create_schema_reflection_agent("gemini-2.5-flash")

        # Evolve output_schema component
        result = await evolve(
            agent,
            trainset,
            critic=critic,
            reflection_agent=schema_reflector,
            components=["output_schema"],  # Evolve schema, not instruction
        )
        print(f"Evolved schema: {result.evolved_components['output_schema']}")
        ```

        Using App/Runner for existing infrastructure integration:

        ```python
        from google.adk.apps.app import App
        from google.adk.runners import Runner
        from google.adk.sessions import DatabaseSessionService

        # Configure Runner with your production session service
        session_service = DatabaseSessionService(connection_string="...")
        runner = Runner(
            app_name="my_app",
            agent=agent,
            session_service=session_service,
        )

        # Evolution uses your Runner's session_service for all operations
        result = await evolve(
            agent,
            trainset,
            runner=runner,  # Services extracted from runner
        )
        ```
    """
    # Validate inputs
    _validate_evolve_inputs(agent, trainset)
    required_keys = (
        set(trainset[0].keys()) if trainset and len(trainset) > 0 else {"input"}
    )

    resolved_valset = valset if valset is not None else trainset
    if valset is not None:
        _validate_dataset(
            valset,
            "valset",
            allow_empty=False,
            required_keys=required_keys,
        )

    # Log reflection_agent configuration if provided
    if reflection_agent is not None:
        logger.debug(
            "evolve.reflection_agent.configured",
            agent_name=agent.name,
            reflection_agent_name=reflection_agent.name,
            message="Using ADK reflection agent for instruction improvement",
        )

    # Capture original instruction for StateGuard validation
    original_instruction = str(agent.instruction)

    candidate_selector_label = (
        candidate_selector
        if isinstance(candidate_selector, str)
        else type(candidate_selector).__name__
        if candidate_selector is not None
        else None
    )

    component_selector_label = (
        component_selector
        if isinstance(component_selector, str)
        else type(component_selector).__name__
        if component_selector is not None
        else None
    )

    # Log evolution start
    logger.info(
        "evolve.start",
        agent_name=agent.name,
        trainset_size=len(trainset),
        valset_size=len(resolved_valset),
        valset_defaulted=valset is None,
        has_critic=critic is not None,
        has_reflection_agent=reflection_agent is not None,
        has_state_guard=state_guard is not None,
        candidate_selector=candidate_selector_label,
        component_selector=component_selector_label,
    )

    # Resolve services from runner/app with precedence warnings (#227)
    # Log precedence warnings if multiple config sources provided (T009)
    if runner is not None and app is not None:
        logger.warning(
            "evolve.precedence.runner_over_app",
            message="Both runner and app provided; using runner (runner takes precedence)",
            runner_app_name=runner.app_name,
            app_name=app.name,
        )
    if runner is not None and executor is not None:
        logger.warning(
            "evolve.precedence.runner_over_executor",
            message="Both runner and executor provided; using runner's session_service",
            runner_app_name=runner.app_name,
        )

    # Extract services using precedence rules (T006)
    resolved_session_service, _artifact_service = _resolve_evolution_services(
        runner=runner,
        app=app,
        session_service=None,  # evolve() doesn't have direct session_service param
    )

    # Create executor with resolved session_service (T007)
    # Runner takes precedence over user-provided executor
    if runner is not None:
        resolved_executor = AgentExecutor(session_service=resolved_session_service)
    else:
        resolved_executor = executor or AgentExecutor(
            session_service=resolved_session_service
        )

    # Build scorer
    scorer: Scorer
    if critic:
        scorer = CriticScorer(critic_agent=critic, executor=resolved_executor)
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

    # Resolve config
    resolved_config = config or EvolutionConfig()

    # Create reflection agent if not provided
    resolved_reflection_agent = reflection_agent
    if resolved_reflection_agent is None:
        # Create default reflection agent with config settings
        resolved_reflection_agent = LlmAgent(
            name="reflection_agent",
            model=_resolve_model_for_agent(resolved_config.reflection_model),
            instruction=resolved_config.reflection_prompt or REFLECTION_INSTRUCTION,
        )
        logger.debug(
            "evolve.reflection_agent.default",
            reflection_model=resolved_config.reflection_model,
        )

    # Create adapter with resolved session_service (T008)
    # The adapter passes session_service to create_adk_reflection_fn()
    # ensuring the reflection agent shares the same session service
    adapter = ADKAdapter(
        agent=agent,
        scorer=scorer,
        trajectory_config=trajectory_config,
        reflection_agent=resolved_reflection_agent,
        executor=resolved_executor,
        schema_constraints=schema_constraints,
        session_service=resolved_session_service,
    )

    # Build initial candidate components based on requested components
    resolved_components = components if components else [DEFAULT_COMPONENT_NAME]
    initial_components: dict[str, str] = {}
    original_component_values: dict[str, str] = {}

    for comp_name in resolved_components:
        if comp_name == DEFAULT_COMPONENT_NAME:
            initial_components[comp_name] = original_instruction
            original_component_values[comp_name] = original_instruction
        elif comp_name == COMPONENT_OUTPUT_SCHEMA:
            if not hasattr(agent, "output_schema") or agent.output_schema is None:
                raise ConfigurationError(
                    f"Cannot evolve '{COMPONENT_OUTPUT_SCHEMA}': agent has no output_schema",
                    field="components",
                    value=comp_name,
                    constraint="agent must have output_schema to evolve it",
                )
            schema_text = serialize_pydantic_schema(agent.output_schema)
            initial_components[comp_name] = schema_text
            original_component_values[comp_name] = schema_text
        else:
            raise ConfigurationError(
                f"Unknown component: '{comp_name}'. Supported: "
                f"'{DEFAULT_COMPONENT_NAME}', '{COMPONENT_OUTPUT_SCHEMA}'",
                field="components",
                value=comp_name,
                constraint="must be a supported component name",
            )

    logger.debug(
        "evolve.components.resolved",
        agent_name=agent.name,
        components=resolved_components,
    )

    initial_candidate = Candidate(components=initial_components)

    # Create engine
    resolved_candidate_selector: CandidateSelectorProtocol | None = None
    if candidate_selector is not None:
        if isinstance(candidate_selector, str):
            resolved_candidate_selector = create_candidate_selector(candidate_selector)
        else:
            resolved_candidate_selector = candidate_selector

    resolved_component_selector: ComponentSelectorProtocol | None = None
    if component_selector is not None:
        if isinstance(component_selector, str):
            resolved_component_selector = create_component_selector(component_selector)
        else:
            resolved_component_selector = component_selector

    engine = AsyncGEPAEngine(
        adapter=adapter,
        config=resolved_config,
        initial_candidate=initial_candidate,
        batch=trainset,
        valset=resolved_valset,
        candidate_selector=resolved_candidate_selector,
        component_selector=resolved_component_selector,
    )

    # Run evolution with cleanup
    try:
        result = await engine.run()

        valset_score = result.valset_score
        trainset_score = result.trainset_score

        if trainset_score is not None:
            logger.info(
                "evolve.trainset.scored",
                agent_name=agent.name,
                trainset_size=len(trainset),
                trainset_score=trainset_score,
            )
        if valset_score is not None:
            logger.info(
                "evolve.valset.scored",
                agent_name=agent.name,
                valset_size=len(resolved_valset),
                valset_score=valset_score,
                valset_defaulted=valset is None,
            )

        # Apply state guard validation if provided (for token preservation)
        # Only applies to text components (instruction), not to output_schema
        validated_components = dict(result.evolved_components)
        for comp_name in resolved_components:
            if comp_name in result.evolved_components:
                if comp_name == DEFAULT_COMPONENT_NAME and state_guard is not None:
                    validated_components[comp_name] = _apply_state_guard_validation(
                        state_guard=state_guard,
                        original_component_text=original_component_values[comp_name],
                        evolved_component_text=result.evolved_components[comp_name],
                        agent_name=agent.name,
                    )
                else:
                    validated_components[comp_name] = result.evolved_components[
                        comp_name
                    ]

        # Log evolution completion
        logger.info(
            "evolve.complete",
            agent_name=agent.name,
            original_score=result.original_score,
            final_score=result.final_score,
            improvement=result.improvement,
            total_iterations=result.total_iterations,
            valset_score=valset_score,
            trainset_score=trainset_score,
            components=resolved_components,
        )

        # Return result with validated evolved_components and valset_score
        # (creates new instance since frozen)
        return EvolutionResult(
            original_score=result.original_score,
            final_score=result.final_score,
            evolved_components=validated_components,
            iteration_history=result.iteration_history,
            total_iterations=result.total_iterations,
            valset_score=valset_score,
            trainset_score=trainset_score,
        )
    finally:
        # Clean up adapter resources (clears handler constraints)
        adapter.cleanup()


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
        valset (list[dict[str, Any]] | None): Optional validation examples for
            held-out evaluation.
        critic (LlmAgent | None): Optional ADK agent for scoring.
        reflection_agent (LlmAgent | None): Optional ADK agent for proposals
            (not yet implemented).
        config (EvolutionConfig | None): EvolutionConfig for customizing
            evolution parameters.
        trajectory_config (TrajectoryConfig | None): TrajectoryConfig for trace
            capture settings.
        state_guard (StateGuard | None): Optional state token preservation
            settings.
        candidate_selector (CandidateSelectorProtocol | str | None): Optional
            selector instance or selector name.
        executor (AgentExecutorProtocol | None): Optional unified agent executor
            for consistent session management across all agent types.

    Returns:
        EvolutionResult with evolved_components dict and metrics.

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
            model="gemini-2.5-flash",
            instruction="You are a helpful assistant.",
            output_schema=OutputSchema,
        )

        trainset = [
            {"input": "What is 2+2?", "expected": "4"},
        ]

        result = evolve_sync(agent, trainset)
        print(f"Evolved: {result.evolved_components['instruction']}")
        ```

        With configuration:

        ```python
        from gepa_adk import evolve_sync, EvolutionConfig

        config = EvolutionConfig(max_iterations=50)
        result = evolve_sync(agent, trainset, config=config)
        ```

    Note:
        Synchronous wrapper for scripts and Jupyter notebooks. Automatically
        handles nested event loops using nest_asyncio when needed.
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
