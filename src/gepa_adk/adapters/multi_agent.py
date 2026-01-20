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
import warnings
from typing import Any, Mapping, Sequence

import structlog
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService

from gepa_adk.domain.exceptions import MultiAgentValidationError
from gepa_adk.domain.trajectory import ADKTrajectory, MultiAgentTrajectory
from gepa_adk.domain.types import TrajectoryConfig
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import AgentExecutorProtocol
from gepa_adk.ports.scorer import Scorer
from gepa_adk.utils.events import (
    extract_final_output,
    extract_output_from_state,
    extract_trajectory,
)

logger = structlog.get_logger(__name__)


class MultiAgentAdapter:
    """Adapter for multi-agent pipeline evaluation.

    Wraps multiple ADK agents into a SequentialAgent for evaluation,
    enabling session state sharing between agents. Implements
    AsyncGEPAAdapter protocol for use with AsyncGEPAEngine.

    Attributes:
        agents (list[LlmAgent]): List of ADK agents to evaluate together.
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
        Basic adapter setup with shared sessions:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters import MultiAgentAdapter
        from gepa_adk.ports.scorer import Scorer

        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            output_key="generated_code",  # Saves output to session state
        )
        critic = LlmAgent(
            name="critic",
            model="gemini-2.0-flash",
            instruction="Review the code in {generated_code}.",  # Accesses shared state
        )
        scorer = MyScorer()  # Implements Scorer protocol

        adapter = MultiAgentAdapter(
            agents=[generator, critic],
            primary="generator",
            scorer=scorer,
            share_session=True,  # Default: agents share session state
        )

        # Evaluate with candidate instructions
        batch = [{"input": "Generate code...", "expected": "def foo(): ..."}]
        candidate = {
            "generator_instruction": "Generate high-quality code",
            "critic_instruction": "Review thoroughly",
        }
        result = await adapter.evaluate(batch, candidate)
        ```

        Isolated sessions (share_session=False):

        ```python
        adapter = MultiAgentAdapter(
            agents=[generator, critic],
            primary="generator",
            scorer=scorer,
            share_session=False,  # Each agent has isolated session
        )
        # Agents cannot access each other's outputs when isolated
        ```

    Note:
        Adheres to AsyncGEPAAdapter[dict[str, Any], MultiAgentTrajectory, str] protocol.
        All methods are async and follow ADK's async-first patterns.

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
        agents: list[LlmAgent],
        primary: str,
        scorer: Scorer | None = None,
        share_session: bool = True,
        session_service: BaseSessionService | None = None,
        app_name: str = "multi_agent_eval",
        trajectory_config: TrajectoryConfig | None = None,
        proposer: AsyncReflectiveMutationProposer | None = None,
        reflection_model: str = "ollama_chat/gpt-oss:20b",
        reflection_prompt: str | None = None,
        executor: AgentExecutorProtocol | None = None,
    ) -> None:
        """Initialize the MultiAgent adapter with agents and scorer.

        Args:
            agents: List of ADK agents to evolve together. Must have at least
                one agent. All agents must have unique names.
            primary: Name of the agent whose output is used for scoring.
                Must match one of the agent names in the list.
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
                via LLM reflection. **Recommended:** Provide an ADK-based proposer
                using `create_adk_reflection_fn()`. If None, creates a deprecated
                LiteLLM-based proposer.
            reflection_model: LiteLLM model identifier for reflection/mutation operations.
                **Deprecated:** Use `proposer` with ADK reflection instead.
                Only used when creating the default proposer (when proposer=None).
            reflection_prompt: Custom reflection/mutation prompt template.
                **Deprecated:** Configure prompts via ADK agent instruction instead.
                Only used when creating the default proposer (when proposer=None).
            executor: Optional unified executor for consistent agent execution.
                If None, uses legacy execution path with direct Runner calls.
                When provided, all agent executions use the executor's execute_agent
                method for consistent session management and feature parity (FR-001).

        Raises:
            MultiAgentValidationError: If agents list is empty, primary agent
                not found, duplicate agent names, or no scorer and primary
                lacks output_schema.

        Examples:
            With default session service:

            ```python
            adapter = MultiAgentAdapter(
                agents=[generator, critic],
                primary="generator",
                scorer=scorer,
            )
            ```

            With custom session service:

            ```python
            from google.adk.sessions import FirestoreSessionService

            session_service = FirestoreSessionService(project_id="my-project")
            adapter = MultiAgentAdapter(
                agents=[generator, critic],
                primary="generator",
                scorer=scorer,
                session_service=session_service,
                app_name="my_optimizer",
            )
            ```

        Note:
            Clones agents during evaluation to apply candidate instructions.
            Original agents are never mutated.
        """
        # Validation
        if not agents:
            raise MultiAgentValidationError(
                "agents list cannot be empty",
                field="agents",
                value=[],
                constraint="len >= 1",
            )

        # Check for unique agent names
        agent_names = [agent.name for agent in agents]
        if len(agent_names) != len(set(agent_names)):
            duplicates = [name for name in agent_names if agent_names.count(name) > 1]
            raise MultiAgentValidationError(
                f"duplicate agent name: '{duplicates[0]}'",
                field="agents",
                value=agent_names,
                constraint="unique names",
            )

        # Check primary agent exists
        if primary not in agent_names:
            raise MultiAgentValidationError(
                f"primary agent '{primary}' not found in agents list",
                field="primary",
                value=primary,
                constraint=f"must be one of {agent_names}",
            )

        # Check scorer or output_schema
        primary_agent = next(agent for agent in agents if agent.name == primary)
        if scorer is None and primary_agent.output_schema is None:
            raise MultiAgentValidationError(
                "no scorer and primary agent lacks output_schema",
                field="scorer",
                value=None,
                constraint="scorer must be provided or primary agent must have output_schema",
            )

        self.agents = agents
        self.primary = primary
        self.scorer = scorer
        self.share_session = share_session
        self.session_service = session_service or InMemorySessionService()
        self.app_name = app_name
        self.trajectory_config = trajectory_config or TrajectoryConfig()
        if proposer is not None:
            self._proposer = proposer
        else:
            # Default proposer with LiteLLM reflection (deprecated)
            warnings.warn(
                "Default LiteLLM reflection is deprecated and will be removed in a "
                "future version. When using evolve_group(), provide a reflection_agent "
                "parameter with an ADK LlmAgent instead. "
                "See: https://github.com/Alberto-Codes/gepa-adk/issues/144",
                DeprecationWarning,
                stacklevel=2,
            )
            self._proposer = AsyncReflectiveMutationProposer(
                model=reflection_model,
                prompt_template=reflection_prompt,
            )
        self._executor = executor

        # Bind logger with adapter context (FR-008)
        self._logger = logger.bind(
            adapter="MultiAgentAdapter",
            primary_agent=self.primary,
            agent_count=len(self.agents),
            app_name=self.app_name,
            uses_executor=executor is not None,
        )

        self._logger.info("adapter.initialized")

    def _build_pipeline(
        self,
        candidate: dict[str, str],
    ) -> SequentialAgent:
        """Build SequentialAgent pipeline with instruction overrides.

        Clones each agent with candidate instruction if present, otherwise
        uses original instruction. Returns a SequentialAgent containing
        the cloned agents.

        Args:
            candidate: Component name to text mapping. Keys should follow
                the pattern `{agent.name}_instruction`.

        Returns:
            SequentialAgent with cloned agents as sub_agents.

        Examples:
            Building pipeline with instruction overrides:

            ```python
            candidate = {
                "generator_instruction": "Generate code...",
                "critic_instruction": "Review code...",
            }
            pipeline = adapter._build_pipeline(candidate)
            ```

        Note:
            Overrides agent instructions using candidate values. Uses Pydantic's
            model_copy() to clone agents efficiently. Original agents remain unchanged.
        """
        cloned_agents = []
        for agent in self.agents:
            instruction_key = f"{agent.name}_instruction"
            if instruction_key in candidate:
                # Clone agent with new instruction and clear parent to allow re-parenting
                cloned = agent.model_copy(
                    update={
                        "instruction": candidate[instruction_key],
                        "parent_agent": None,
                    }
                )
                cloned_agents.append(cloned)
            else:
                # Clone agent unchanged but clear parent to allow re-parenting
                cloned = agent.model_copy(update={"parent_agent": None})
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
        """Evaluate multi-agent pipeline with candidate instructions over a batch.

        Args:
            batch: List of input examples, each with "input" key and optional
                "expected" key for scoring.
            candidate: Component name to text mapping. Keys should follow
                the pattern `{agent.name}_instruction`.
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
                "generator_instruction": "Generate high-quality code",
                "critic_instruction": "Review thoroughly",
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
            Orchestrates evaluation by building a SequentialAgent pipeline with
            cloned agents for each evaluation. Primary agent's output is scored.
            Original agents remain unchanged.
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

        # Build pipeline with candidate instructions (if sharing session)
        # For isolated sessions, we'll clone agents with candidate instructions
        if self.share_session:
            pipeline = self._build_pipeline(candidate)
        else:
            pipeline = None

        primary_agent = next(
            agent for agent in self.agents if agent.name == self.primary
        )

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
        trajectories: list[MultiAgentTrajectory] | None = [] if capture_traces else None
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
            candidate: Candidate instructions to apply to agents.
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

        # Clone primary agent with candidate instruction
        primary_agent = next(
            agent for agent in self.agents if agent.name == self.primary
        )
        instruction_key = f"{primary_agent.name}_instruction"
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

    def _build_trajectory(
        self,
        events: list[Any],
        final_output: str,
        session_state: dict[str, Any],
        error: str | None = None,
    ) -> MultiAgentTrajectory:
        """Assemble complete multi-agent trajectory from event stream.

        Args:
            events: List of ADK Event objects collected during execution.
            final_output: The final text response from the pipeline.
            session_state: Session state dictionary from execution.
            error: Error message if execution failed, None otherwise.

        Returns:
            MultiAgentTrajectory with agent trajectories, pipeline output,
            token usage, and error (if any).

        Note:
            Organizes trajectory data by extracting individual agent trajectories
            from events and aggregating token usage across all agents.
        """
        # Extract trajectories for each agent
        agent_trajectories: dict[str, ADKTrajectory] = {}

        # For now, create a single aggregated trajectory
        # TODO: Extract individual agent trajectories from SequentialAgent events
        aggregated_trajectory = extract_trajectory(
            events=events,
            final_output=final_output,
            error=error,
            config=self.trajectory_config,
        )

        # Map to primary agent for now (simplified)
        agent_trajectories[self.primary] = aggregated_trajectory

        # Aggregate token usage
        total_token_usage = aggregated_trajectory.token_usage

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

        Follows the GEPA trial structure with feedback and trajectory dicts.
        This matches the adk_adapter.py pattern for consistency.

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
        # Build feedback dict (critic evaluation - stochastic)
        # Mandatory: score
        # Mandatory if available: feedback_text
        # Optional: feedback_dimensions, feedback_guidance
        feedback: dict[str, Any] = {"score": score}

        # Add scorer metadata if present (from CriticScorer)
        if metadata and isinstance(metadata, dict):
            # feedback_text is the primary text feedback (mandatory when available)
            feedback_text = metadata.get("feedback")
            if (
                feedback_text
                and isinstance(feedback_text, str)
                and feedback_text.strip()
            ):
                feedback["feedback_text"] = feedback_text.strip()

            # Optional extras - pass through when available
            guidance = metadata.get("actionable_guidance")
            if guidance and isinstance(guidance, str) and guidance.strip():
                feedback["feedback_guidance"] = guidance.strip()

            dimension_scores = metadata.get("dimension_scores")
            if (
                dimension_scores
                and isinstance(dimension_scores, dict)
                and dimension_scores
            ):
                feedback["feedback_dimensions"] = dimension_scores

        # Add error from trajectory if present
        if trajectory and trajectory.error:
            feedback["error"] = trajectory.error

        # Build trajectory dict (the journey: input → output)
        trajectory_dict: dict[str, Any] = {
            "output": output,
            "component": component_name,
            "component_value": component_value,
        }

        # Add input if available
        if input_text:
            trajectory_dict["input"] = input_text

        # Add trace details from trajectory if available
        if trajectory:
            if trajectory.total_token_usage:
                trajectory_dict["tokens"] = trajectory.total_token_usage.total_tokens

        # Return trial record: feedback + trajectory
        return {
            "feedback": feedback,
            "trajectory": trajectory_dict,
        }

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
