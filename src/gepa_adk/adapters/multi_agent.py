"""Multi-agent adapter implementation for AsyncGEPAAdapter protocol.

This module provides the MultiAgentAdapter implementation that enables
evolutionary optimization of multiple ADK agents together, with optional
session state sharing between agents during evaluation.

Note:
    The MultiAgentAdapter coordinates evaluation of multiple agents as a unified pipeline.
    This adapter bridges GEPA evaluation patterns to Google ADK's multi-agent
    architecture, using SequentialAgent for session state sharing and enabling
    co-evolution of multiple agent instructions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

import structlog
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService

from gepa_adk.adapters.component_handlers import component_handlers, get_handler
from gepa_adk.adapters.trial_builder import TrialBuilder
from gepa_adk.domain.exceptions import MultiAgentValidationError, RestoreError
from gepa_adk.domain.trajectory import ADKTrajectory, MultiAgentTrajectory, TokenUsage
from gepa_adk.domain.types import ComponentsMapping, ComponentSpec, TrajectoryConfig
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import AgentExecutorProtocol
from gepa_adk.ports.scorer import Scorer
from gepa_adk.utils.events import (
    extract_final_output,
    extract_output_from_state,
    extract_trajectory,
    partition_events_by_agent,
)

logger = structlog.get_logger(__name__)


class MultiAgentAdapter:
    """Adapter for multi-agent pipeline evaluation with per-agent component routing.

    Wraps multiple ADK agents into a SequentialAgent for evaluation,
    enabling session state sharing between agents. Implements
    AsyncGEPAAdapter protocol for use with AsyncGEPAEngine.

    Supports per-agent component configuration via the `components` parameter,
    allowing different components to be evolved for each agent (e.g., evolve
    generator's instruction while evolving critic's generate_content_config).

    Attributes:
        agents (dict[str, LlmAgent]): Named ADK agents to evaluate together.
        components (ComponentsMapping): Per-agent component configuration.
        primary (str): Name of agent whose output is used for scoring.
        scorer (Scorer): Scoring implementation (CriticScorer or similar).
        share_session (bool): Whether agents share session state.
        session_service (InMemorySessionService): Session service for state management.
        trajectory_config (TrajectoryConfig | None): Configuration for trajectory extraction.
        _executor (AgentExecutorProtocol | None): Optional unified executor for
            consistent agent execution. When None, uses legacy execution path.
        _proposer (AsyncReflectiveMutationProposer): Mutation proposer for
            generating improved instructions via LLM reflection.
        _logger (BoundLogger): Bound structlog logger with context.

    Examples:
        Basic adapter setup with per-agent components (API v0.3.x):

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters import MultiAgentAdapter
        from gepa_adk.ports.scorer import Scorer

        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            output_key="generated_code",
        )
        critic = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review the code in {generated_code}.",
        )
        scorer = MyScorer()

        adapter = MultiAgentAdapter(
            agents={"generator": generator, "critic": critic},
            primary="generator",
            scorer=scorer,
            components={
                "generator": ["instruction", "output_schema"],
                "critic": ["generate_content_config"],
            },
        )

        # Candidates use qualified names (agent.component format per ADR-012)
        candidate = {
            "generator.instruction": "Generate high-quality code",
            "generator.output_schema": "class Output(BaseModel): ...",
            "critic.generate_content_config": "temperature: 0.3",
        }
        result = await adapter.evaluate(batch, candidate)
        ```

        Exclude an agent from evolution:

        ```python
        adapter = MultiAgentAdapter(
            agents={"generator": gen, "validator": val},
            primary="generator",
            scorer=scorer,
            components={
                "generator": ["instruction"],
                "validator": [],  # Empty list = no evolution
            },
        )
        ```

    Note:
        Adheres to AsyncGEPAAdapter[dict[str, Any], MultiAgentTrajectory, str] protocol.
        All methods are async and follow ADK's async-first patterns.

        **Breaking Change (0.3.x)**:
        - `agents` parameter changed from `list[LlmAgent]` to `dict[str, LlmAgent]`
        - `components` parameter is now required
        - Candidate keys use qualified names (agent.component) instead of
          {agent_name}_instruction format

        **Session Sharing Behavior**:
        - When `share_session=True` (default): Uses SequentialAgent to execute
          agents sequentially with shared InvocationContext. Earlier agents can
          write to session state (via `output_key`), later agents can read that
          state via template strings like `{output_key}` in their instructions.
        - When `share_session=False`: Each agent executes with an isolated session.
          Agents cannot access each other's outputs. This is useful when agents
          should not interfere with each other's state (EdgeCase-5: incompatible
          outputs behavior).

        **output_key State Propagation**:
        - When an agent has `output_key` set, its final response is automatically
          saved to `session.state[output_key]`.
        - With `share_session=True`, subsequent agents can reference this via
          template strings: `instruction="Process {output_key}"`.
        - With `share_session=False`, state is not shared and template references
          will not resolve (agents see empty or undefined state).
    """

    def __init__(
        self,
        agents: dict[str, LlmAgent],
        primary: str,
        components: ComponentsMapping,
        scorer: Scorer | None = None,
        share_session: bool = True,
        session_service: BaseSessionService | None = None,
        app_name: str = "multi_agent_eval",
        trajectory_config: TrajectoryConfig | None = None,
        proposer: AsyncReflectiveMutationProposer | None = None,
        executor: AgentExecutorProtocol | None = None,
    ) -> None:
        """Initialize the MultiAgent adapter with named agents and component config.

        Args:
            agents: Named ADK agents to evolve together. Must have at least
                one agent. Keys are agent names, values are LlmAgent instances.
            primary: Name of the agent whose output is used for scoring.
                Must match one of the agent names in the dict.
            components: Per-agent component configuration mapping agent names
                to lists of component names to evolve. All agents must have
                an entry (use empty list to exclude from evolution). Component
                names must have registered handlers.
            scorer: Optional scorer implementation. If None, the primary agent
                must have an output_schema for schema-based scoring.
            share_session: Whether agents share session state during execution.
                When True (default), uses SequentialAgent. When False, agents
                execute with isolated sessions.
            session_service: Optional session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for session identification.
            trajectory_config: Configuration for trajectory extraction behavior.
                If None, uses TrajectoryConfig defaults.
            proposer: Mutation proposer for generating improved instructions
                via LLM reflection. Required. Create using `create_adk_reflection_fn()`
                with an ADK LlmAgent for reflection.
            executor: Optional unified executor for consistent agent execution.
                If None, uses legacy execution path with direct Runner calls.
                When provided, all agent executions use the executor's execute_agent
                method for consistent session management and feature parity (FR-001).

        Raises:
            MultiAgentValidationError: If agents dict is empty, primary agent
                not found, or no scorer and primary lacks output_schema.
            ValueError: If proposer is not provided, or if components mapping
                contains unknown agents, unknown component handlers, or is
                missing entries for agents in the agents dict.

        Examples:
            With per-agent components (API v0.3.x):

            ```python
            from gepa_adk.engine import (
                create_adk_reflection_fn,
                AsyncReflectiveMutationProposer,
            )

            reflection_fn = create_adk_reflection_fn(reflection_agent, executor)
            proposer = AsyncReflectiveMutationProposer(adk_reflection_fn=reflection_fn)
            adapter = MultiAgentAdapter(
                agents={"generator": gen, "critic": critic},
                primary="generator",
                components={
                    "generator": ["instruction", "output_schema"],
                    "critic": ["instruction"],
                },
                scorer=scorer,
                proposer=proposer,
            )
            ```

            Excluding an agent from evolution:

            ```python
            adapter = MultiAgentAdapter(
                agents={"generator": gen, "validator": val},
                primary="generator",
                components={
                    "generator": ["instruction"],
                    "validator": [],  # Excluded from evolution
                },
                scorer=scorer,
                proposer=proposer,
            )
            ```

        Note:
            Clones agents during evaluation to apply candidate instructions.
            Original agents are never mutated.
        """
        # Validation
        if not agents:
            raise MultiAgentValidationError(
                "agents dict cannot be empty",
                field="agents",
                value={},
                constraint="len >= 1",
            )

        agent_names = list(agents.keys())

        # Check primary agent exists
        if primary not in agent_names:
            raise MultiAgentValidationError(
                f"primary agent '{primary}' not found in agents dict",
                field="primary",
                value=primary,
                constraint=f"must be one of {agent_names}",
            )

        # Check scorer or output_schema
        primary_agent = agents[primary]
        if scorer is None and primary_agent.output_schema is None:
            raise MultiAgentValidationError(
                "no scorer and primary agent lacks output_schema",
                field="scorer",
                value=None,
                constraint="scorer must be provided or primary agent must have output_schema",
            )

        self.agents = agents
        self.components = components
        self.primary = primary
        self.scorer = scorer
        self.share_session = share_session
        self.session_service = session_service or InMemorySessionService()
        self.app_name = app_name
        self.trajectory_config = trajectory_config or TrajectoryConfig()
        if proposer is None:
            raise ValueError(
                "proposer is required. Create one using create_adk_reflection_fn() "
                "with an ADK LlmAgent for reflection operations."
            )
        self._proposer = proposer
        self._executor = executor

        # Validate components mapping (fail-fast)
        self._validate_components()

        # Bind logger with adapter context (FR-008)
        self._logger = logger.bind(
            adapter="MultiAgentAdapter",
            primary_agent=self.primary,
            agent_count=len(self.agents),
            app_name=self.app_name,
            uses_executor=executor is not None,
        )

        # Initialize trial builder for reflective dataset construction
        self._trial_builder = TrialBuilder()

        self._logger.info("adapter.initialized")

    def _validate_components(self) -> None:
        """Validate components mapping at initialization time.

        Performs fail-fast validation to ensure:
        1. All agent names in components exist in agents dict
        2. All agents in agents dict have entries in components
        3. All component names have registered handlers

        Raises:
            ValueError: If validation fails with descriptive error message.

        Note:
            Called during __init__ to catch configuration errors early.
        """
        agent_names = set(self.agents.keys())

        # Check all agent names in components exist in agents dict
        for agent_name in self.components:
            if agent_name not in agent_names:
                raise ValueError(
                    f"Agent '{agent_name}' not found in agents dict. "
                    f"Available: {sorted(agent_names)}"
                )

        # Check all agents in agents dict have entries in components
        missing_agents = agent_names - set(self.components.keys())
        if missing_agents:
            raise ValueError(
                f"Agents {sorted(missing_agents)} missing from components mapping. "
                "All agents must have an entry in components (use empty list to exclude)."
            )

        # Check all component names have handlers
        for agent_name, comp_list in self.components.items():
            for comp_name in comp_list:
                if not component_handlers.has(comp_name):
                    available = component_handlers.names()
                    raise ValueError(
                        f"No handler registered for component '{comp_name}'. "
                        f"Available: {available}"
                    )

        logger.debug(
            "components.validated",
            agents=list(self.components.keys()),
            components_per_agent={k: len(v) for k, v in self.components.items()},
        )

    def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
        """Apply candidate component values to agents, tracking originals.

        Routes each candidate component to the correct agent based on
        qualified component names (agent.component format per ADR-012).

        Args:
            candidate: Mapping of qualified component names to new values.
                Keys must be in format 'agent.component'.

        Returns:
            Dictionary mapping qualified names to original values for restoration.

        Raises:
            ValueError: If qualified name format is invalid.
            KeyError: If agent not found or handler not registered.

        Examples:
            Apply candidate and get originals:

            ```python
            candidate = {
                "generator.instruction": "evolved text",
                "critic.generate_content_config": "temperature: 0.3",
            }
            originals = adapter._apply_candidate(candidate)
            # originals["generator.instruction"] contains original instruction
            ```

        Note:
            Returns originals dict for use with _restore_agents(). Does not
            modify self.agents - modifications are applied in-place to agent
            objects which are later cloned for pipeline execution.
        """
        originals: dict[str, Any] = {}

        for qualified_name, value in candidate.items():
            # Skip non-component keys (e.g., evolution_id)
            if "." not in qualified_name:
                continue

            spec = ComponentSpec.parse(qualified_name)

            if spec.agent not in self.agents:
                raise KeyError(
                    f"Agent '{spec.agent}' not found. "
                    f"Available: {list(self.agents.keys())}"
                )

            agent = self.agents[spec.agent]
            handler = get_handler(spec.component)
            originals[qualified_name] = handler.apply(agent, value)

            self._logger.debug(
                "component.applied",
                qualified_name=qualified_name,
                agent=spec.agent,
                component=spec.component,
            )

        return originals

    def _restore_agents(self, originals: dict[str, Any]) -> None:
        """Restore all agents to original state after evaluation.

        Uses best-effort restoration: all components are attempted even if
        some fail. Errors are aggregated and raised as RestoreError after
        all restoration attempts complete.

        Args:
            originals: Mapping of qualified names to original values,
                as returned by _apply_candidate().

        Raises:
            RestoreError: If one or more components fail to restore, containing
                list of (qualified_name, exception) pairs.

        Note:
            Always attempts to restore all components even if some fail,
            to minimize state corruption. Uses try/except for each component.
        """
        errors: list[tuple[str, Exception]] = []

        for qualified_name, original in originals.items():
            try:
                spec = ComponentSpec.parse(qualified_name)
                agent = self.agents[spec.agent]
                handler = get_handler(spec.component)
                handler.restore(agent, original)

                self._logger.debug(
                    "component.restored",
                    qualified_name=qualified_name,
                )
            except Exception as e:
                errors.append((qualified_name, e))
                self._logger.warning(
                    "component.restore_failed",
                    qualified_name=qualified_name,
                    error=str(e),
                )

        if errors:
            raise RestoreError(
                f"Failed to restore {len(errors)} components",
                errors=errors,
            )

    def _build_pipeline(
        self,
        candidate: dict[str, str],
    ) -> SequentialAgent:
        """Build SequentialAgent pipeline with instruction overrides.

        Clones each agent with instruction values from the candidate dict.
        Non-instruction components (output_schema, generate_content_config)
        must be applied to original agents via _apply_candidate() before
        calling this method.

        Args:
            candidate: Qualified component name to text mapping. Keys should
                follow the pattern `{agent_name}.{component_name}` per ADR-012.

        Returns:
            SequentialAgent with cloned agents as sub_agents.

        Examples:
            Building pipeline with instruction overrides:

            ```python
            candidate = {
                "generator.instruction": "Generate code...",
                "critic.instruction": "Review code...",
            }
            pipeline = adapter._build_pipeline(candidate)
            ```

        Note:
            Only instruction components are applied via model_copy() cloning.
            Other components are inherited from the (pre-modified) original
            agents. See evaluate() for the full execution flow.
        """
        cloned_agents = []

        # Build set of updates per agent from qualified names
        agent_updates: dict[str, dict[str, Any]] = {name: {} for name in self.agents}

        for qualified_name, value in candidate.items():
            # Skip non-component keys (e.g., evolution_id)
            if "." not in qualified_name:
                continue

            spec = ComponentSpec.parse(qualified_name)
            if spec.agent in agent_updates:
                # Only instruction is cloned via model_copy; other components
                # (output_schema, generate_content_config) are applied to the
                # original agents via _apply_candidate() BEFORE this method.
                #
                # Full execution flow in evaluate():
                # 1. _apply_candidate() - applies ALL components to originals
                # 2. _build_pipeline() - clones agents with instruction override
                # 3. Run pipeline (clones inherit non-instruction from originals)
                # 4. _restore_agents() - restores original state
                if spec.component == "instruction":
                    agent_updates[spec.agent]["instruction"] = value

        for agent_name, agent in self.agents.items():
            updates = agent_updates.get(agent_name, {})
            # Always clear parent_agent to allow re-parenting
            updates["parent_agent"] = None

            cloned = agent.model_copy(update=updates)
            cloned_agents.append(cloned)

        pipeline = SequentialAgent(
            name="MultiAgentPipeline",
            sub_agents=cloned_agents,
        )

        return pipeline

    def _extract_primary_output(
        self,
        pipeline_output: str,
        session_state: dict[str, Any],
        primary_agent: LlmAgent,
    ) -> str:
        """Extract primary agent's output from pipeline execution.

        If the primary agent has an output_key, retrieves the output from
        session state using the shared extract_output_from_state utility.
        Otherwise, uses the pipeline's final output.

        Args:
            pipeline_output: Final output from SequentialAgent execution.
            session_state: Session state dictionary from execution.
            primary_agent: The primary agent instance.

        Returns:
            Primary agent's output text for scoring.

        Examples:
            Extracting output with output_key:

            ```python
            primary_agent = LlmAgent(name="generator", output_key="generated_code")
            output = adapter._extract_primary_output(
                pipeline_output="...",
                session_state={"generated_code": "def foo(): ..."},
                primary_agent=primary_agent,
            )
            # output == "def foo(): ..."
            ```

        Note:
            Outputs are saved to session state via the agent's output_key property.
            When share_session=True, later agents can access earlier outputs via
            template strings like {output_key} in their instructions. When
            share_session=False, agents have isolated sessions and cannot
            access each other's outputs (EdgeCase-5: incompatible outputs behavior).

            Uses the shared extract_output_from_state utility for consistent
            state-based output extraction across the codebase.
        """
        # Try state-based extraction using shared utility
        output_key = getattr(primary_agent, "output_key", None)
        state_output = extract_output_from_state(session_state, output_key)
        if state_output is not None:
            return state_output

        # Fallback to pipeline output
        return pipeline_output

    def _create_session_id(self) -> str:
        """Create a unique session ID for evaluation isolation.

        Returns:
            Unique session identifier string.

        Note:
            Outputs unique session identifiers using timestamp and random components.
        """
        import time
        import uuid

        return f"eval_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

    def _cleanup_session(self, session_id: str) -> None:
        """Clean up session after evaluation.

        Args:
            session_id: Session identifier to clean up.

        Note:
            Optional cleanup method. Currently a no-op. Future implementations
            may delete sessions from persistent storage.
        """
        # No-op for now - sessions are in-memory and cleaned up automatically
        pass

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[MultiAgentTrajectory, str]:
        """Evaluate multi-agent pipeline with candidate component values over a batch.

        Args:
            batch: List of input examples, each with "input" key and optional
                "expected" key for scoring.
            candidate: Qualified component name to text mapping. Keys should
                follow the pattern `{agent_name}.{component_name}` per ADR-012.
            capture_traces: Whether to capture execution traces (tool calls,
                state deltas, token usage).

        Returns:
            EvaluationBatch containing outputs, scores, and optional trajectories.

        Examples:
            Basic evaluation without traces:

            ```python
            batch = [
                {"input": "Generate code...", "expected": "def foo(): ..."},
            ]
            candidate = {
                "generator.instruction": "Generate high-quality code",
                "critic.instruction": "Review thoroughly",
            }
            result = await adapter.evaluate(batch, candidate)
            assert len(result.outputs) == 1
            assert len(result.scores) == 1
            ```

            With trace capture:

            ```python
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            assert result.trajectories is not None
            assert len(result.trajectories) == len(batch)
            ```

        Note:
            Orchestrates evaluation by applying candidate components to agents,
            building a SequentialAgent pipeline with cloned agents, then restoring
            original agent state. Primary agent's output is scored.

            Uses try/finally to ensure agents are restored even on evaluation errors,
            preventing state corruption between candidate evaluations.
        """
        self._logger.info(
            "adapter.evaluate.start",
            batch_size=len(batch),
            capture_traces=capture_traces,
            evolution_id=candidate.get("evolution_id", "unknown"),
        )

        # Handle empty batch case
        if not batch:
            self._logger.info("adapter.evaluate.complete", batch_size=0)
            return EvaluationBatch(outputs=[], scores=[], trajectories=None)

        # Apply candidate components to agents, track originals for restoration
        # This applies all component types (instruction, output_schema,
        # generate_content_config) via their handlers per FR-003
        originals = self._apply_candidate(candidate)

        try:
            # Build pipeline with candidate instructions (if sharing session)
            # For isolated sessions, we'll clone agents with candidate instructions
            # Note: _build_pipeline clones agents; non-instruction components are
            # inherited from the (now-modified) original agents
            if self.share_session:
                pipeline = self._build_pipeline(candidate)
            else:
                pipeline = None

            primary_agent = self.agents[self.primary]

            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(5)  # Default max concurrent evals

            # Create tasks for all examples
            tasks = [
                self._eval_single_with_semaphore(
                    example=example,
                    example_index=i,
                    pipeline=pipeline,
                    primary_agent=primary_agent,
                    candidate=candidate,
                    capture_traces=capture_traces,
                    semaphore=semaphore,
                )
                for i, example in enumerate(batch)
            ]

            # Execute all tasks in parallel with exception handling
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and maintain order
            outputs: list[str] = []
            scores: list[float] = []
            trajectories: list[MultiAgentTrajectory] | None = (
                [] if capture_traces else None
            )
            metadata_list: list[dict[str, Any]] = []
            inputs: list[str] = []

            successful = 0
            failed = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle exception case
                    self._logger.warning(
                        "adapter.evaluate.example.error",
                        example_index=i,
                        error=str(result),
                    )
                    outputs.append("")
                    scores.append(0.0)
                    metadata_list.append({})
                    inputs.append(batch[i].get("input", "") if i < len(batch) else "")
                    failed += 1

                    if capture_traces:
                        error_trajectory = MultiAgentTrajectory(
                            agent_trajectories={},
                            pipeline_output="",
                            total_token_usage=None,
                            error=str(result),
                        )
                        trajectories.append(error_trajectory)  # type: ignore
                else:
                    # Unpack success case: (output, score, trajectory, metadata, input_text)
                    output_text, score, trajectory, metadata, input_text = result  # type: ignore[misc]
                    outputs.append(output_text)
                    scores.append(score)
                    metadata_list.append(metadata or {})
                    inputs.append(input_text or "")
                    successful += 1

                    if capture_traces and trajectory is not None:
                        trajectories.append(trajectory)  # type: ignore

            avg_score = sum(scores) / len(scores) if scores else 0.0

            self._logger.info(
                "adapter.evaluate.complete",
                batch_size=len(batch),
                successful=successful,
                failed=failed,
                avg_score=avg_score,
            )

            return EvaluationBatch(
                outputs=outputs,
                scores=scores,
                trajectories=trajectories,
                metadata=metadata_list,
                inputs=inputs,
            )
        finally:
            # Restore all agents to original state per FR-004
            # Uses best-effort restoration: attempts all components even if some fail
            self._restore_agents(originals)

    async def _eval_single_with_semaphore(
        self,
        example: dict[str, Any],
        example_index: int,
        pipeline: SequentialAgent | None,
        primary_agent: LlmAgent,
        candidate: dict[str, str],
        capture_traces: bool,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, float, MultiAgentTrajectory | None, dict[str, Any] | None, str]:
        """Evaluate a single example with semaphore-controlled concurrency.

        Args:
            example: Input example with "input" key and optional "expected" key.
            example_index: Index of example in batch (for logging).
            pipeline: SequentialAgent pipeline to execute (if share_session=True).
            primary_agent: Primary agent for output extraction.
            candidate: Candidate instructions to apply (for isolated sessions).
            capture_traces: Whether to capture execution traces.
            semaphore: Semaphore to control concurrent execution.

        Returns:
            Tuple of (output_text, score, trajectory_or_none, metadata, input_text).
            On failure, returns ("", 0.0, error_trajectory, None, input_text).

        Note:
            Orchestrates single example evaluation with semaphore-controlled concurrency.
        """
        async with semaphore:
            self._logger.debug(
                "adapter.evaluate.example",
                example_index=example_index,
                example_input=example.get("input", "")[:50],
            )

            try:
                # Run the pipeline for this example
                output_text: str
                session_state: dict[str, Any] = {}

                if capture_traces:
                    result = await self._run_single_example(
                        example, pipeline, candidate, capture_events=True
                    )
                    # When capture_events=True, result is a 3-tuple of
                    # (output_text, events, session_state).
                    output_text, events, session_state = result  # type: ignore[misc]
                    # Build trajectory from collected events
                    trajectory = self._build_trajectory(
                        events=list(events),
                        final_output=output_text,
                        session_state=session_state,
                        error=None,
                    )
                else:
                    # When capture_events=False, result is a 2-tuple of
                    # (output_text, session_state).
                    run_result = await self._run_single_example(
                        example, pipeline, candidate, capture_events=False
                    )
                    output_text, session_state = run_result  # type: ignore[misc]
                    trajectory = None

                # Extract primary agent output
                primary_output = self._extract_primary_output(
                    output_text, session_state, primary_agent
                )

                # Score the output
                input_text = example.get("input", "")
                expected = example.get("expected")
                metadata: dict[str, Any] | None = None
                if self.scorer:
                    score_result = await self.scorer.async_score(
                        input_text, primary_output, expected
                    )
                    # Handle both float and tuple[float, dict] return types
                    # The dict contains metadata like feedback, dimension_scores, etc.
                    if isinstance(score_result, tuple):
                        score = score_result[0]
                        metadata = score_result[1] if len(score_result) > 1 else None
                    else:
                        score = float(score_result)
                else:
                    # Simple schema-based scoring fallback when no external scorer is provided.
                    # If an expected value is given, return 1.0 on exact match of the primary
                    # output and 0.0 otherwise; if no expected is provided, return 0.0.
                    if expected is None:
                        score = 0.0
                    else:
                        score = 1.0 if primary_output == expected else 0.0

                return (primary_output, score, trajectory, metadata, input_text)

            except Exception as e:
                # Handle execution errors gracefully
                self._logger.warning(
                    "adapter.evaluate.example.error",
                    example_index=example_index,
                    error=str(e),
                )

                # Create error trajectory if capturing traces
                error_trajectory = None
                if capture_traces:
                    error_trajectory = MultiAgentTrajectory(
                        agent_trajectories={},
                        pipeline_output="",
                        total_token_usage=None,
                        error=str(e),
                    )

                return ("", 0.0, error_trajectory, None, example.get("input", ""))

    async def _run_single_example(
        self,
        example: dict[str, Any],
        pipeline: SequentialAgent | None,
        candidate: dict[str, str],
        capture_events: bool = False,
    ) -> tuple[str, list[Any], dict[str, Any]] | tuple[str, dict[str, Any]]:
        """Execute pipeline on a single input example.

        Args:
            example: Input example with "input" key.
            pipeline: SequentialAgent pipeline to execute (if share_session=True).
                      If None, executes agents independently (share_session=False).
            candidate: Candidate instructions to apply (for isolated sessions).
            capture_events: If True, return (output, events, state) tuple.
                           If False, return (output, state) tuple.

        Returns:
            If capture_events=True: (final_output, event_list, session_state) tuple
            If capture_events=False: (final_output, session_state) tuple

        Raises:
            RuntimeError: If pipeline execution fails.

        Note:
            Orchestrates execution based on session sharing mode. When
            share_session=False, executes agents independently with isolated
            sessions. When share_session=True, uses SequentialAgent pipeline.
            Streams events via ADK Runner pattern with async iteration.
        """
        input_text = example.get("input", "")
        if not input_text:
            return ("", [], {}) if capture_events else ("", {})

        if self.share_session:
            # Use SequentialAgent pipeline (shared session)
            if pipeline is None:
                raise RuntimeError("Pipeline required for shared session mode")
            return await self._run_shared_session(
                input_text,
                pipeline,
                capture_events,
            )
        else:
            # Execute agents independently (isolated sessions)
            return await self._run_isolated_sessions(
                input_text, candidate, capture_events
            )

    async def _run_shared_session(
        self,
        input_text: str,
        pipeline: SequentialAgent,
        capture_events: bool,
    ) -> tuple[str, list[Any], dict[str, Any]] | tuple[str, dict[str, Any]]:
        """Execute agents with shared session state via SequentialAgent.

        Args:
            input_text: Input text for the pipeline.
            pipeline: SequentialAgent pipeline to execute.
            capture_events: Whether to capture events.

        Returns:
            Tuple of (output, events, state) or (output, state).

        Note:
            Uses unified AgentExecutor when available (FR-002), otherwise
            falls back to legacy execution via direct Runner calls.
        """
        # Use executor if available (FR-002)
        if self._executor is not None:
            from gepa_adk.ports.agent_executor import ExecutionStatus

            result = await self._executor.execute_agent(
                agent=pipeline,
                input_text=input_text,
            )

            if result.status == ExecutionStatus.FAILED:
                # Log failure and return empty output
                self._logger.error(
                    "pipeline.execution.failed",
                    session_id=result.session_id,
                    error=result.error_message,
                )
                if capture_events:
                    return ("", result.captured_events or [], {})
                return ("", {})

            final_output = result.extracted_value or ""
            session_state: dict[str, Any] = {}

            # Retrieve session state from session service
            try:
                session = await self.session_service.get_session(
                    app_name=self.app_name,
                    user_id="eval_user",
                    session_id=result.session_id,
                )
                if session and hasattr(session, "state"):
                    session_state = dict(session.state)
            except (KeyError, AttributeError, TypeError) as exc:
                # Session state retrieval failed due to expected lookup/attribute issues.
                self._logger.debug(
                    "session_state.retrieval_failed",
                    session_id=result.session_id,
                    error=str(exc),
                )

            if capture_events:
                return (final_output, result.captured_events or [], session_state)
            return (final_output, session_state)

        # Legacy execution path (no executor)
        from google.genai import types

        runner = Runner(
            agent=pipeline,
            app_name=self.app_name,
            session_service=self.session_service,
        )

        content = types.Content(
            role="user",
            parts=[types.Part(text=input_text)],
        )

        # Create session in session service first (required by ADK Runner)
        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id="eval_user",
        )
        session_id = session.id

        events: list[Any] = []
        session_state_legacy: dict[str, Any] = {}

        try:
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session_id,
                new_message=content,
            ):
                events.append(event)

                if hasattr(event, "session") and event.session:
                    if hasattr(event.session, "state"):
                        session_state_legacy = dict(event.session.state)  # type: ignore
        finally:
            self._cleanup_session(session_id)

        # Extract final output using shared utility (filters thought parts)
        final_output = extract_final_output(events)

        if capture_events:
            return (final_output, events, session_state_legacy)
        return (final_output, session_state_legacy)

    async def _run_isolated_sessions(
        self,
        input_text: str,
        candidate: dict[str, str],
        capture_events: bool,
    ) -> tuple[str, list[Any], dict[str, Any]] | tuple[str, dict[str, Any]]:
        """Execute agents independently with isolated sessions.

        Args:
            input_text: Input text for the first agent.
            candidate: Candidate component values using qualified names.
            capture_events: Whether to capture events.

        Returns:
            Tuple of (output, events, state) or (output, state).
            Returns the primary agent's output.

        Note:
            Orchestrates independent execution of each agent with its own session.
            State is not shared between agents. The primary agent's output is returned.
            Agents are cloned with candidate instructions to avoid mutation.
        """
        from google.genai import types

        # Clone primary agent with candidate instruction using qualified name
        primary_agent = self.agents[self.primary]
        instruction_key = f"{self.primary}.instruction"
        if instruction_key in candidate:
            primary_agent = primary_agent.model_copy(
                update={"instruction": candidate[instruction_key]}
            )

        all_events: list[Any] = []
        session_state: dict[str, Any] = {}

        # Use executor if available (FR-002)
        if self._executor is not None:
            from gepa_adk.ports.agent_executor import ExecutionStatus

            result = await self._executor.execute_agent(
                agent=primary_agent,
                input_text=input_text,
            )

            if result.status == ExecutionStatus.FAILED:
                self._logger.warning(
                    "isolated_session_failed",
                    agent=primary_agent.name,
                    session_id=result.session_id,
                    error=result.error_message,
                )
                # Return empty output on failure
                if capture_events:
                    return ("", result.captured_events or [], {})
                return ("", {})

            final_output = result.extracted_value or ""

            # Retrieve session state from session service if session was created
            if result.session_id:
                try:
                    session = await self.session_service.get_session(
                        app_name=self.app_name,
                        user_id="eval_user",
                        session_id=result.session_id,
                    )
                    if session and hasattr(session, "state"):
                        session_state = dict(session.state)
                except KeyError:
                    # Session might not exist or might have been cleaned up.
                    self._logger.debug(
                        "session_state_unavailable",
                        app_name=self.app_name,
                        user_id="eval_user",
                        session_id=result.session_id,
                    )
                except ValueError:
                    # Session identifier or parameters may be invalid; ignore for evaluation.
                    self._logger.debug(
                        "session_state_invalid",
                        app_name=self.app_name,
                        user_id="eval_user",
                        session_id=result.session_id,
                    )

            if capture_events:
                return (final_output, result.captured_events or [], session_state)
            return (final_output, session_state)

        # Legacy execution path (no executor)
        # Execute primary agent with isolated session
        runner = Runner(
            agent=primary_agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

        content = types.Content(
            role="user",
            parts=[types.Part(text=input_text)],
        )

        # Create session in session service first (required by ADK Runner)
        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id="eval_user",
        )
        session_id = session.id

        try:
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session_id,
                new_message=content,
            ):
                all_events.append(event)

                if hasattr(event, "session") and event.session:
                    if hasattr(event.session, "state"):
                        session_state = dict(event.session.state)  # type: ignore
        finally:
            self._cleanup_session(session_id)

        # Extract final output using shared utility (filters thought parts)
        final_output = extract_final_output(all_events)

        if capture_events:
            return (final_output, all_events, session_state)
        return (final_output, session_state)

    def _aggregate_token_usage(
        self,
        agent_trajectories: dict[str, ADKTrajectory],
    ) -> TokenUsage | None:
        """Sum token usage across all agent trajectories.

        Args:
            agent_trajectories: Mapping of agent names to their trajectories.

        Returns:
            TokenUsage with summed totals if any agent has usage data,
            None if no usage data available.

        Note:
            Sums input, output, and total tokens across all agents to provide
            pipeline-level token consumption metrics.
        """
        total_input = 0
        total_output = 0
        total = 0
        has_usage = False

        for trajectory in agent_trajectories.values():
            if trajectory.token_usage:
                has_usage = True
                total_input += trajectory.token_usage.input_tokens
                total_output += trajectory.token_usage.output_tokens
                total += trajectory.token_usage.total_tokens

        if has_usage:
            return TokenUsage(
                input_tokens=total_input,
                output_tokens=total_output,
                total_tokens=total,
            )
        return None

    def _build_trajectory(
        self,
        events: list[Any],
        final_output: str,
        session_state: dict[str, Any],
        error: str | None = None,
    ) -> MultiAgentTrajectory:
        """Assemble complete multi-agent trajectory from event stream.

        Partitions events by originating agent (using event.author) and builds
        individual ADKTrajectory objects for each agent. This enables fine-grained
        observability into which sub-agent contributed which tool calls, state
        changes, and token usage.

        Args:
            events: List of ADK Event objects collected during execution.
            final_output: The final text response from the pipeline.
            session_state: Session state dictionary from execution.
            error: Error message if execution failed, None otherwise.

        Returns:
            MultiAgentTrajectory with per-agent trajectories, pipeline output,
            aggregated token usage, and error (if any).

        Note:
            Organizes trajectory data by extracting individual agent trajectories
            from events and aggregating token usage across all agents.
        """
        # Partition events by originating agent
        partitions = partition_events_by_agent(events)

        # Build per-agent trajectories
        if not partitions:
            # If no agent-authored events were found, fall back to a minimal
            # trajectory for the primary agent using the full event list.
            agent_trajectories: dict[str, ADKTrajectory] = {
                self.primary: extract_trajectory(
                    events=events,
                    final_output=final_output,
                    error=error,
                    config=self.trajectory_config,
                )
            }
        else:
            agent_trajectories = {}
            for agent_name, agent_events in partitions.items():
                # Only primary agent gets final_output and error attribution
                agent_output = final_output if agent_name == self.primary else ""
                agent_error = error if agent_name == self.primary else None

                agent_trajectories[agent_name] = extract_trajectory(
                    events=agent_events,
                    final_output=agent_output,
                    error=agent_error,
                    config=self.trajectory_config,
                )

        # Aggregate token usage across all agents
        total_token_usage = self._aggregate_token_usage(agent_trajectories)

        return MultiAgentTrajectory(
            agent_trajectories=agent_trajectories,
            pipeline_output=final_output,
            total_token_usage=total_token_usage,
            error=error,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[MultiAgentTrajectory, str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build reflective datasets from evaluation results with traces.

        Args:
            candidate: Current candidate component values.
            eval_batch: Evaluation results including trajectories.
            components_to_update: List of component names to generate
                datasets for.

        Returns:
            Mapping from component name to sequence of reflection examples.
            Each example contains input, output, score, and trace context.

        Examples:
            Generate reflection dataset:

            ```python
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            dataset = await adapter.make_reflective_dataset(
                candidate, result, ["generator_instruction", "critic_instruction"]
            )
            assert "generator_instruction" in dataset
            ```

        Note:
            Operates on eval_batch trajectories (capture_traces=True required).
            Dataset format is compatible with MutationProposer interface.
        """
        self._logger.info(
            "adapter.make_reflective_dataset.start",
            num_examples=len(eval_batch.outputs),
            components=components_to_update,
        )

        # Build reflective dataset for each requested component
        result: dict[str, list[dict[str, Any]]] = {}

        for component in components_to_update:
            examples: list[dict[str, Any]] = []

            for i, (output, score) in enumerate(
                zip(eval_batch.outputs, eval_batch.scores, strict=True)
            ):
                # Get trajectory info if available
                trajectory = None
                if eval_batch.trajectories and i < len(eval_batch.trajectories):
                    trajectory = eval_batch.trajectories[i]

                # Get metadata (critic feedback) if available
                metadata = None
                if eval_batch.metadata and i < len(eval_batch.metadata):
                    metadata = eval_batch.metadata[i]

                # Get input text if available
                input_text = None
                if eval_batch.inputs and i < len(eval_batch.inputs):
                    input_text = eval_batch.inputs[i]

                example = self._build_reflection_example(
                    input_text=input_text,
                    output=output,
                    score=score,
                    trajectory=trajectory,
                    metadata=metadata,
                    component_name=component,
                    component_value=candidate.get(component, ""),
                )
                examples.append(example)

            result[component] = examples

        self._logger.info(
            "adapter.make_reflective_dataset.complete",
            num_components=len(result),
            total_examples=sum(len(exs) for exs in result.values()),
        )

        return result

    def _build_reflection_example(
        self,
        input_text: str | None,
        output: str,
        score: float,
        trajectory: MultiAgentTrajectory | None,
        metadata: dict[str, Any] | None,
        component_name: str,
        component_value: str,
    ) -> dict[str, Any]:
        """Build a single trial record for reflection.

        Delegates to shared TrialBuilder for consistent trial structure.

        Terminology:
            - trial: One performance record {feedback, trajectory}
            - feedback: Critic evaluation {score, feedback_text, ...}
            - trajectory: The journey from input to output with optional trace

        Args:
            input_text: The input that was given to the pipeline.
            output: Pipeline output text.
            score: Evaluation score for this output.
            trajectory: Optional trajectory with execution trace.
            metadata: Optional scorer metadata dict (e.g., from CriticScorer)
                containing 'feedback', 'dimension_scores', 'actionable_guidance'.
            component_name: Name of the component being evaluated.
            component_value: Current value of the component.

        Returns:
            Trial dict with keys: feedback, trajectory.
            - feedback: score (mandatory), feedback_text (mandatory if available)
            - trajectory: input, output (mandatory), component context

        Note:
            Aligns with whitepaper requirements: score + feedback_text are the
            minimum required fields. Extra metadata (dimensions, guidance) is
            passed through when available.
        """
        # Extract error from trajectory if present
        error = trajectory.error if trajectory else None

        # Build extra trajectory fields specific to multi-agent pipelines
        extra_trajectory: dict[str, Any] = {
            "component": component_name,
            "component_value": component_value,
        }

        # Add token usage from trajectory if available
        if trajectory and trajectory.total_token_usage:
            extra_trajectory["tokens"] = trajectory.total_token_usage.total_tokens

        return self._trial_builder.build_trial(
            input_text=input_text,
            output=output,
            score=score,
            metadata=metadata,
            error=error,
            extra_trajectory=extra_trajectory,
        )

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new component texts based on reflective dataset.

        Delegates to AsyncReflectiveMutationProposer to generate improved
        instruction text via LLM reflection. When the proposer returns None
        (empty dataset), falls back to unchanged candidate values.

        Args:
            candidate: Current candidate component values.
            reflective_dataset: Dataset from make_reflective_dataset(), keyed by
                component name with sequences of reflection examples in the format
                produced by build_reflection_example().
            components_to_update: Components to generate proposals for.

        Returns:
            Dictionary mapping component names to proposed new text values.
            When proposer returns None, returns unchanged candidate values.

        Examples:
            Propose new component texts via LLM reflection:

            ```python
            # After evaluation with traces
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            dataset = await adapter.make_reflective_dataset(
                candidate, result, ["generator_instruction", "critic_instruction"]
            )

            # Propose new texts via LLM reflection
            proposals = await adapter.propose_new_texts(
                candidate,
                dataset,
                ["generator_instruction", "critic_instruction"],
            )
            # proposals contains improved instructions based on feedback
            ```

        Note:
            Delegates to AsyncReflectiveMutationProposer for actual mutation
            generation. Falls back gracefully when dataset is empty.
        """
        self._logger.debug(
            "propose_new_texts.delegating",
            components_requested=components_to_update,
        )

        result = await self._proposer.propose(
            candidate, reflective_dataset, components_to_update
        )

        if result is None:
            self._logger.info(
                "propose_new_texts.fallback",
                reason="proposer_returned_none",
                components_requested=components_to_update,
            )
            return {
                component: candidate.get(component, "")
                for component in components_to_update
            }

        # Merge with candidate for any missing components
        merged = {
            component: result.get(component, candidate.get(component, ""))
            for component in components_to_update
        }

        # Log proposed texts for each component
        for component, proposed_text in result.items():
            self._logger.info(
                "proposal.text",
                component=component,
                proposed_length=len(proposed_text),
                proposed_preview=proposed_text[:300] + "..."
                if len(proposed_text) > 300
                else proposed_text,
            )

        self._logger.info(
            "propose_new_texts.complete",
            components_proposed=list(result.keys()),
            components_requested=components_to_update,
        )

        return merged
