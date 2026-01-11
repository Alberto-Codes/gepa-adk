"""Multi-agent adapter implementation for AsyncGEPAAdapter protocol.

This module provides the MultiAgentAdapter implementation that enables
evolutionary optimization of multiple ADK agents together, with optional
session state sharing between agents during evaluation.

Note:
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

from gepa_adk.domain.exceptions import MultiAgentValidationError
from gepa_adk.domain.trajectory import ADKTrajectory, MultiAgentTrajectory
from gepa_adk.domain.types import TrajectoryConfig
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.scorer import Scorer
from gepa_adk.utils.events import extract_trajectory

logger = structlog.get_logger(__name__)


class MultiAgentAdapter:
    """Adapter for multi-agent pipeline evaluation.

    Wraps multiple ADK agents into a SequentialAgent for evaluation,
    enabling session state sharing between agents. Implements
    AsyncGEPAAdapter protocol for use with AsyncGEPAEngine.

    Attributes:
        agents: List of ADK agents to evaluate together.
        primary: Name of agent whose output is used for scoring.
        scorer: Scoring implementation (CriticScorer or similar).
        share_session: Whether agents share session state.
        session_service: Session service for state management.
        trajectory_config: Configuration for trajectory extraction.
        _logger: Bound structlog logger with context.

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

        # Bind logger with adapter context
        self._logger = logger.bind(
            adapter="MultiAgentAdapter",
            primary_agent=self.primary,
            agent_count=len(self.agents),
            app_name=self.app_name,
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
                # Clone agent with new instruction
                cloned = agent.model_copy(
                    update={"instruction": candidate[instruction_key]}
                )
                cloned_agents.append(cloned)
            else:
                # Use original agent unchanged
                cloned_agents.append(agent)

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
        session state. Otherwise, uses the pipeline's final output.

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
        """
        # Check if primary agent has output_key
        if hasattr(primary_agent, "output_key") and primary_agent.output_key:
            output_key = primary_agent.output_key
            if output_key in session_state:
                return str(session_state[output_key])

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
                # Unpack success case: (output_text, score, trajectory_or_none)
                output_text, score, trajectory = result  # type: ignore[misc]
                outputs.append(output_text)
                scores.append(score)
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
    ) -> tuple[str, float, MultiAgentTrajectory | None]:
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
            Tuple of (output_text, score, trajectory_or_none).
            On failure, returns ("", 0.0, error_trajectory).

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
                    # When capture_events=True, result is tuple[str, list[Any], dict]
                    output_text, events, session_state = result
                    # Build trajectory from collected events
                    trajectory = self._build_trajectory(
                        events=list(events),
                        final_output=output_text,
                        session_state=session_state,
                        error=None,
                    )
                else:
                    # When capture_events=False, result is tuple[str, dict]
                    run_result = await self._run_single_example(
                        example, pipeline, candidate, capture_events=False
                    )
                    output_text, session_state = run_result
                    trajectory = None

                # Extract primary agent output
                primary_output = self._extract_primary_output(
                    output_text, session_state, primary_agent
                )

                # Score the output
                input_text = example.get("input", "")
                expected = example.get("expected")
                if self.scorer:
                    score_result = await self.scorer.async_score(
                        input_text, primary_output, expected
                    )
                    # Handle both float and tuple[float, dict] return types
                    score = (
                        score_result[0]
                        if isinstance(score_result, tuple)
                        else float(score_result)
                    )
                else:
                    # Schema-based scoring (primary agent has output_schema)
                    # For now, return 0.5 as placeholder
                    # TODO: Implement schema-based scoring extraction
                    score = 0.5

                return (primary_output, score, trajectory)

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

                return ("", 0.0, error_trajectory)

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
            return await self._run_shared_session(
                input_text,
                pipeline,
                capture_events,  # type: ignore
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
        """
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

        session_id = self._create_session_id()
        final_output = ""
        events: list[Any] = []
        session_state: dict[str, Any] = {}

        try:
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session_id,
                new_message=content,
            ):
                if capture_events:
                    events.append(event)

                if event.is_final_response():
                    if event.actions and event.actions.response_content:  # type: ignore[union-attr]
                        for part in event.actions.response_content:  # type: ignore[union-attr]
                            if hasattr(part, "text") and part.text:
                                final_output = part.text
                                break

                if hasattr(event, "session") and event.session:
                    if hasattr(event.session, "state"):
                        session_state = dict(event.session.state)  # type: ignore
        finally:
            self._cleanup_session(session_id)

        if capture_events:
            return (final_output, events, session_state)
        return (final_output, session_state)

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

        final_output = ""
        all_events: list[Any] = []
        session_state: dict[str, Any] = {}

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

        session_id = self._create_session_id()

        try:
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session_id,
                new_message=content,
            ):
                if capture_events:
                    all_events.append(event)

                if event.is_final_response():
                    if event.actions and event.actions.response_content:  # type: ignore[union-attr]
                        for part in event.actions.response_content:  # type: ignore[union-attr]
                            if hasattr(part, "text") and part.text:
                                final_output = part.text
                                break

                if hasattr(event, "session") and event.session:
                    if hasattr(event.session, "state"):
                        session_state = dict(event.session.state)  # type: ignore
        finally:
            self._cleanup_session(session_id)

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

                example = self._build_reflection_example(
                    output=output,
                    score=score,
                    trajectory=trajectory,
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
        output: str,
        score: float,
        trajectory: MultiAgentTrajectory | None,
        component_name: str,
        component_value: str,
    ) -> dict[str, Any]:
        """Build a single reflection example in GEPA format.

        Args:
            output: Pipeline output text.
            score: Evaluation score for this output.
            trajectory: Optional trajectory with execution trace.
            component_name: Name of the component being evaluated.
            component_value: Current value of the component.

        Returns:
            Dictionary with GEPA-compatible reflection format containing
            'Inputs', 'Generated Outputs', and 'Feedback' keys.

        Note:
            Organizes reflection data to match GEPA's MutationProposer expectations.
            Trajectory context is included in Feedback when available.
        """
        # Build feedback string
        feedback_parts = [f"score: {score:.3f}"]

        if trajectory:
            if trajectory.error:
                feedback_parts.append(f"error: {trajectory.error}")
            if trajectory.total_token_usage:
                feedback_parts.append(
                    f"tokens: {trajectory.total_token_usage.total_tokens}"
                )

        feedback = " | ".join(feedback_parts)

        return {
            "Inputs": {
                "component": component_name,
                "component_value": component_value,
            },
            "Generated Outputs": output,
            "Feedback": feedback,
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new component texts based on reflective dataset.

        This is a stub implementation that returns unchanged candidate values.
        Full implementation will delegate to AsyncReflectiveMutationProposer
        (see Issue #7 / spec 007-async-mutation-proposer).

        Args:
            candidate: Current candidate component values.
            reflective_dataset: Dataset from make_reflective_dataset().
            components_to_update: Components to generate proposals for.

        Returns:
            Dictionary mapping component names to proposed new text values.
            Currently returns unchanged candidate values as stub.

        Examples:
            Using the stub implementation:

            ```python
            # After evaluation with traces
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            dataset = await adapter.make_reflective_dataset(
                candidate, result, ["generator_instruction"]
            )

            # Propose new texts (stub returns unchanged values)
            new_texts = await adapter.propose_new_texts(
                candidate, dataset, ["generator_instruction"]
            )
            assert (
                new_texts["generator_instruction"] == candidate["generator_instruction"]
            )
            ```

        Note:
            Only returns unchanged candidate values as a stub implementation.
        """
        self._logger.warning(
            "propose_new_texts_stub_called",
            message="Using stub implementation - returns unchanged candidate values",
            components_requested=components_to_update,
        )

        # Stub: return unchanged values for requested components
        return {
            component: candidate.get(component, "")
            for component in components_to_update
        }
