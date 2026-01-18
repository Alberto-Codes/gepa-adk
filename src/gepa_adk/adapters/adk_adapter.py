"""ADK adapter implementation for AsyncGEPAAdapter protocol.

This module provides the concrete implementation of AsyncGEPAAdapter for
Google ADK agents, enabling evolutionary optimization of ADK agent instructions.

Terminology:
    - **component**: An evolvable unit with a name and text (e.g., instruction)
    - **component_text**: The text content of a component being evolved
    - **trial**: One performance record {input, output, feedback, trajectory}
    - **trials**: Collection of trial records for reflection
    - **feedback**: Critic evaluation {score, feedback_text, feedback_*} (stochastic)
    - **trajectory**: Execution record {tool_calls, tokens, error} (deterministic)
    - **proposed_component_text**: The improved text for the same component

Note:
    This adapter bridges GEPA's evaluation patterns to ADK's agent/runner
    architecture, handling instruction overrides, trace capture, and session
    management per ADK conventions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

import structlog
from google.adk.agents import LlmAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService

from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord
from gepa_adk.domain.types import TrajectoryConfig
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.scorer import Scorer
from gepa_adk.utils.events import extract_final_output, extract_trajectory

logger = structlog.get_logger(__name__)


class ADKAdapter:
    """ADK implementation of AsyncGEPAAdapter protocol.

    Bridges GEPA evaluation patterns to Google ADK's agent/runner architecture,
    enabling evolutionary optimization of ADK agents through instruction mutation
    and reflective learning.

    Attributes:
        agent (LlmAgent): The ADK LlmAgent to evaluate with different candidate
            instructions.
        scorer (Scorer): Scoring implementation for evaluating agent outputs.
        max_concurrent_evals (int): Maximum number of concurrent evaluations
            to run in parallel.
        trajectory_config (TrajectoryConfig): Configuration for trajectory
            extraction behavior (redaction, truncation, feature selection).
        _session_service (BaseSessionService): Session service for managing
            agent state isolation.
        _app_name (str): Application name used for session management.
        _proposer (AsyncReflectiveMutationProposer): Mutation proposer for
            generating improved instructions via LLM reflection.
        _logger (structlog.BoundLogger): Bound logger with adapter context for
            structured logging.

    Examples:
        Basic adapter setup:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters import ADKAdapter
        from gepa_adk.ports.scorer import Scorer

        agent = LlmAgent(
            name="helper",
            model="gemini-2.0-flash",
            instruction="Be helpful and concise",
        )
        scorer = MyScorer()  # Implements Scorer protocol
        adapter = ADKAdapter(agent=agent, scorer=scorer)

        # Evaluate with candidate instruction
        batch = [{"input": "What is 2+2?", "expected": "4"}]
        candidate = {"instruction": "Be very precise with math"}
        result = await adapter.evaluate(batch, candidate)
        ```

    Note:
        Adheres to AsyncGEPAAdapter[dict[str, Any], ADKTrajectory, str] protocol.
        All methods are async and follow ADK's async-first patterns.
    """

    def __init__(
        self,
        agent: LlmAgent,
        scorer: Scorer,
        max_concurrent_evals: int = 5,
        session_service: BaseSessionService | None = None,
        app_name: str = "gepa_adk_eval",
        trajectory_config: TrajectoryConfig | None = None,
        proposer: AsyncReflectiveMutationProposer | None = None,
        reflection_agent: LlmAgent | None = None,
        reflection_model: str = "ollama_chat/gpt-oss:20b",
        reflection_prompt: str | None = None,
    ) -> None:
        """Initialize the ADK adapter with agent and scorer.

        Args:
            agent: The ADK LlmAgent to evaluate with different instructions.
            scorer: Scorer implementation for evaluating agent outputs.
            max_concurrent_evals: Maximum number of concurrent evaluations to run
                in parallel. Must be at least 1. Defaults to 5.
            session_service: Optional session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for session identification.
            trajectory_config: Configuration for trajectory extraction behavior.
                If None, uses TrajectoryConfig defaults (secure, all features enabled).
            proposer: Optional mutation proposer for generating improved instructions
                via LLM reflection. If None, creates a default AsyncReflectiveMutationProposer
                with default configuration.
            reflection_agent: Optional ADK LlmAgent to use for reflection operations.
                If provided, creates an ADK-based reflection function and passes it to
                the proposer. If None, proposer uses default LiteLLM-based reflection.
                If proposer is provided, it takes precedence over reflection_agent.
            reflection_model: LiteLLM model identifier for reflection/mutation operations.
                Only used when creating the default proposer (path 3). Ignored when
                proposer or reflection_agent is provided. Defaults to "ollama_chat/gpt-oss:20b".
            reflection_prompt: Custom reflection/mutation prompt template. If provided,
                overrides the default prompt template used by the proposer. The template
                must contain {component_text} and {trials} placeholders.
                Only used when creating the default proposer (path 3). Ignored when
                proposer or reflection_agent is provided.

        Raises:
            TypeError: If agent is not an LlmAgent instance.
            TypeError: If scorer does not satisfy Scorer protocol.
            TypeError: If reflection_agent is provided but not an LlmAgent instance.
            ValueError: If app_name is empty string or max_concurrent_evals < 1.

        Examples:
            With default session service and trajectory config:

            ```python
            adapter = ADKAdapter(agent=agent, scorer=scorer)
            ```

            With custom trajectory configuration:

            ```python
            config = TrajectoryConfig(
                redact_sensitive=True,
                max_string_length=5000,
            )
            adapter = ADKAdapter(agent=agent, scorer=scorer, trajectory_config=config)
            ```

            With custom session service:

            ```python
            from google.adk.sessions import FirestoreSessionService

            session_service = FirestoreSessionService(project_id="my-project")
            adapter = ADKAdapter(
                agent=agent,
                scorer=scorer,
                session_service=session_service,
                app_name="my_optimizer",
            )
            ```

        Note:
            Caches the agent's original instruction and restores it after
            each evaluation to ensure no side effects between evaluations.
        """
        # Type validation
        if not isinstance(agent, LlmAgent):
            raise TypeError(f"agent must be LlmAgent, got {type(agent)}")

        # Scorer protocol check (runtime_checkable)
        if not hasattr(scorer, "score") or not hasattr(scorer, "async_score"):
            raise TypeError(
                f"scorer must implement Scorer protocol, got {type(scorer)}"
            )

        if not app_name or not app_name.strip():
            raise ValueError("app_name cannot be empty")

        if max_concurrent_evals < 1:
            raise ValueError(
                f"max_concurrent_evals must be at least 1, got {max_concurrent_evals}"
            )

        # Validate reflection_agent if provided
        if reflection_agent is not None and not isinstance(reflection_agent, LlmAgent):
            raise TypeError(
                f"reflection_agent must be LlmAgent, got {type(reflection_agent)}"
            )

        self.agent = agent
        self.scorer = scorer
        self.max_concurrent_evals = max_concurrent_evals
        self.trajectory_config = trajectory_config or TrajectoryConfig()
        self._session_service = session_service or InMemorySessionService()
        self._app_name = app_name.strip()

        # Bind logger with adapter context
        self._logger = logger.bind(
            adapter="ADKAdapter",
            agent_name=self.agent.name,
            app_name=self._app_name,
        )

        # Create proposer with clear precedence: proposer overrides reflection_agent.
        if proposer is not None:
            if reflection_agent is not None:
                self._logger.warning(
                    "adapter.proposer.precedence",
                    message="proposer parameter takes precedence over reflection_agent",
                )
            self._proposer = proposer
        elif reflection_agent is not None:
            # Create ADK reflection function and pass to proposer
            adk_reflection_fn = create_adk_reflection_fn(
                reflection_agent,
                session_service=self._session_service,
            )
            self._proposer = AsyncReflectiveMutationProposer(
                adk_reflection_fn=adk_reflection_fn
            )
        else:
            # Default proposer with LiteLLM reflection
            self._proposer = AsyncReflectiveMutationProposer(
                model=reflection_model,
                prompt_template=reflection_prompt,
            )

        self._logger.info("adapter.initialized")

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[ADKTrajectory, str]:
        """Evaluate agent with candidate instruction over a batch of inputs.

        Args:
            batch: List of input examples, each with "input" key and optional
                "expected" key for scoring.
            candidate: Component name to text mapping. If "instruction" key
                is present, it overrides the agent's instruction.
            capture_traces: Whether to capture execution traces (tool calls,
                state deltas, token usage).

        Returns:
            EvaluationBatch containing outputs, scores, and optional trajectories.

        Examples:
            Basic evaluation without traces:

            ```python
            batch = [
                {"input": "What is 2+2?", "expected": "4"},
                {"input": "Capital of France?", "expected": "Paris"},
            ]
            candidate = {"instruction": "Be concise"}
            result = await adapter.evaluate(batch, candidate)
            assert len(result.outputs) == 2
            assert len(result.scores) == 2
            ```

            With trace capture:

            ```python
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            assert result.trajectories is not None
            assert len(result.trajectories) == len(batch)
            ```

        Note:
            Original instruction is restored after evaluation completes,
            even if an exception occurs during evaluation.
            Evaluations run in parallel with concurrency controlled by
            max_concurrent_evals parameter. Results maintain input order
            despite parallel execution.
        """
        self._logger.info(
            "adapter.evaluate.start",
            batch_size=len(batch),
            max_concurrent=self.max_concurrent_evals,
            capture_traces=capture_traces,
        )

        # Handle empty batch case
        if not batch:
            self._logger.info("adapter.evaluate.complete", batch_size=0)
            return EvaluationBatch(outputs=[], scores=[], trajectories=None)

        # Apply candidate instruction (if present) and save original
        original_instruction = self._apply_candidate(candidate)

        try:
            # Create semaphore to limit concurrent evaluations
            semaphore = asyncio.Semaphore(self.max_concurrent_evals)

            # Create tasks for all examples
            tasks = [
                self._eval_single_with_semaphore(
                    example=example,
                    example_index=i,
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
            trajectories: list[ADKTrajectory] | None = [] if capture_traces else None
            metadata_list: list[dict[str, Any]] = []
            inputs: list[str] = []  # Collect inputs for reflection

            successful = 0
            failed = 0

            for i, result in enumerate(results):
                # Collect input text for this example
                inputs.append(batch[i].get("input", ""))
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
                    failed += 1

                    if capture_traces:
                        error_trajectory = self._build_trajectory(
                            events=[],
                            final_output="",
                            error=str(result),
                        )
                        trajectories.append(error_trajectory)  # type: ignore
                else:
                    # Unpack success: (output_text, score, trajectory_or_none, metadata_or_none)
                    # After isinstance check, result is guaranteed to be the tuple type
                    output_text, score, trajectory, metadata = result  # type: ignore[misc]
                    outputs.append(output_text)
                    scores.append(score)
                    metadata_list.append(metadata if metadata is not None else {})
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

            # Only include metadata if at least one example has non-empty metadata
            # Check if any metadata dict has content (not just empty dicts)
            has_metadata = any(
                meta and isinstance(meta, dict) and meta for meta in metadata_list
            )
            final_metadata = metadata_list if has_metadata else None

            return EvaluationBatch(
                outputs=outputs,
                scores=scores,
                trajectories=trajectories,
                metadata=final_metadata,
                inputs=inputs,
            )

        finally:
            # Always restore original instruction
            self._restore_instruction(original_instruction)

    def _apply_candidate(self, candidate: dict[str, str]) -> str:
        """Apply candidate instruction to agent, return original.

        Args:
            candidate: Component name to text mapping.

        Returns:
            Original instruction value for later restoration.

        Note:
            Selectively modifies agent.instruction only if "instruction" key
            is present in candidate. Otherwise, leaves instruction unchanged.
        """
        original_instruction: str = str(self.agent.instruction)

        if "instruction" in candidate:
            new_instruction = candidate["instruction"]
            self.agent.instruction = new_instruction
            self._logger.debug(
                "adapter.instruction.override",
                original=original_instruction[:50],
                new=new_instruction[:50],
            )

        return original_instruction

    def _restore_instruction(self, original_instruction: str) -> None:
        """Restore agent's original instruction.

        Args:
            original_instruction: The instruction value to restore.

        Note:
            Should always be called in finally block to ensure restoration
            even if evaluation fails.
        """
        self.agent.instruction = original_instruction
        self._logger.debug(
            "adapter.instruction.restored",
            instruction=original_instruction[:50],
        )

    def _cleanup_session(self, session_id: str) -> None:
        """Clean up resources for a completed evaluation session.

        Args:
            session_id: The session ID to clean up.

        Note:
            Stub for InMemorySessionService (no-op), but provides extension
            point for other session service implementations that require
            explicit cleanup.
        """
        # InMemorySessionService doesn't require explicit cleanup
        # This provides an extension point for custom session services
        self._logger.debug(
            "adapter.session.cleanup",
            session_id=session_id,
        )

    def _extract_tool_calls(self, events: list[Any]) -> list[ToolCallRecord]:
        """Extract tool call records from ADK Event stream.

        Args:
            events: List of ADK Event objects from runner.

        Returns:
            List of ToolCallRecord instances with tool name, arguments,
            and result (if available).

        Note:
            Scans function_call and function_response parts from
            Event.actions.function_calls if present. Tool calls without
            responses are still recorded. Handles both real ADK Events
            and test mocks gracefully.
        """
        tool_calls: list[ToolCallRecord] = []

        for event in events:
            # Check if event has function_calls in actions
            if hasattr(event, "actions") and hasattr(event.actions, "function_calls"):
                function_calls = event.actions.function_calls
                # function_calls could be None, a list, or a single object
                if function_calls:
                    # Ensure it's iterable
                    if not hasattr(function_calls, "__iter__"):
                        function_calls = [function_calls]

                    try:
                        for fc in function_calls:
                            # Extract name - be defensive for mocks and real objects
                            name = "unknown"

                            # Try direct access first
                            if hasattr(fc, "name"):
                                try:
                                    name_val = fc.name
                                    # Real string value
                                    if isinstance(name_val, str) and name_val != "name":
                                        name = name_val
                                    # Check if it's a Mock (has _mock_name attribute)
                                    elif hasattr(name_val, "_mock_name"):
                                        # Extract actual mock name, not the attribute name
                                        mock_name = str(name_val._mock_name)
                                        # Mock names often have format "mock.attribute.name"
                                        if "." in mock_name:
                                            name = mock_name.split(".")[-1]
                                        else:
                                            name = mock_name
                                except Exception as exc:
                                    logger.debug(
                                        "Failed to extract tool call name; using fallback.",
                                        error=str(exc),
                                        function_call_repr=repr(fc),
                                    )

                            # Extract arguments
                            args = getattr(fc, "args", {})
                            if not isinstance(args, dict):
                                args = {}

                            tool_calls.append(
                                ToolCallRecord(
                                    name=name,
                                    arguments=args,
                                    result=None,  # Will be populated if response found
                                    timestamp=0.0,  # Not tracked in current impl
                                )
                            )
                    except (TypeError, AttributeError):
                        # function_calls not iterable or other issues, skip
                        pass

        return tool_calls

    def _extract_state_deltas(self, events: list[Any]) -> list[dict[str, Any]]:
        """Extract state change records from ADK Event stream.

        Args:
            events: List of ADK Event objects from runner.

        Returns:
            List of dictionaries containing state delta information.
            Each dict has 'key' and 'value' fields from Event.state_delta.

        Note:
            Skips events with None state_delta attributes. State deltas
            capture changes to session or agent state during execution.
        """
        state_deltas: list[dict[str, Any]] = []

        for event in events:
            if hasattr(event, "state_delta") and event.state_delta is not None:
                state_deltas.append(
                    {
                        "key": getattr(event.state_delta, "key", "unknown"),
                        "value": getattr(event.state_delta, "value", None),
                    }
                )

        return state_deltas

    def _extract_token_usage(self, events: list[Any]) -> TokenUsage | None:
        """Extract token usage metadata from ADK Event stream.

        Args:
            events: List of ADK Event objects from runner.

        Returns:
            TokenUsage instance if usage metadata found, None otherwise.

        Note:
            Searches for usage_metadata on final response events. Returns
            the last found usage data (most complete metrics).
        """
        usage_data = None

        for event in events:
            if hasattr(event, "usage_metadata") and event.usage_metadata is not None:
                metadata = event.usage_metadata
                usage_data = TokenUsage(
                    input_tokens=getattr(metadata, "input_tokens", 0),
                    output_tokens=getattr(metadata, "output_tokens", 0),
                    total_tokens=getattr(metadata, "total_tokens", 0),
                )

        return usage_data

    def _build_trajectory(
        self,
        events: list[Any],
        final_output: str,
        error: str | None = None,
    ) -> ADKTrajectory:
        """Assemble complete trajectory from event stream.

        Args:
            events: List of ADK Event objects collected during execution.
            final_output: The final text response from the agent.
            error: Error message if execution failed, None otherwise.

        Returns:
            ADKTrajectory with tool calls, state deltas, token usage,
            final output, and error (if any).

        Note:
            Delegates to extract_trajectory utility with configured
            trajectory_config. This is the complete execution record
            for one batch example.
        """
        return extract_trajectory(
            events=events,
            final_output=final_output,
            error=error,
            config=self.trajectory_config,
        )

    async def _eval_single_with_semaphore(
        self,
        example: dict[str, Any],
        example_index: int,
        candidate: dict[str, str],
        capture_traces: bool,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, float, ADKTrajectory | None, dict[str, Any] | None]:
        """Evaluate a single example with semaphore-controlled concurrency.

        Args:
            example: Input example with "input" key and optional "expected" key.
            example_index: Index of example in batch (for logging).
            candidate: Candidate component values (for instruction override).
            capture_traces: Whether to capture execution traces.
            semaphore: Semaphore to control concurrent execution.

        Returns:
            Tuple of (output_text, score, trajectory_or_none, metadata_or_none).
            On failure, returns ("", 0.0, error_trajectory, None).

        Note:
            Semaphore-controlled wrapper around single example evaluation.
            Called from evaluate() for each example in the batch to ensure
            at most max_concurrent_evals evaluations run simultaneously.
        """
        async with semaphore:
            self._logger.debug(
                "adapter.evaluate.example",
                example_index=example_index,
                example_input=example.get("input", "")[:50],
            )

            try:
                # Run the agent for this example
                output_text: str
                if capture_traces:
                    result = await self._run_single_example(
                        example, capture_events=True
                    )
                    # When capture_events=True, result is tuple[str, list[Any]]
                    output_text, events = result
                    # Build trajectory from collected events
                    trajectory = self._build_trajectory(
                        events=list(events),
                        final_output=output_text,
                        error=None,
                    )
                else:
                    # When capture_events=False, result is str
                    run_result = await self._run_single_example(example)
                    output_text = str(run_result)
                    trajectory = None

                # Score the output
                input_text = example.get("input", "")
                expected = example.get("expected")
                score_result = await self.scorer.async_score(
                    input_text, output_text, expected
                )
                # Handle both float and tuple[float, dict] return types
                if isinstance(score_result, tuple):
                    score = score_result[0]
                    metadata = score_result[1]
                else:
                    score = float(score_result)
                    metadata = None

                return (output_text, score, trajectory, metadata)

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
                    error_trajectory = self._build_trajectory(
                        events=[],
                        final_output="",
                        error=str(e),
                    )

                return ("", 0.0, error_trajectory, None)

    async def _run_single_example(
        self, example: dict[str, Any], capture_events: bool = False
    ) -> tuple[str, list[Any]] | str:
        """Execute agent on a single input example.

        Args:
            example: Input example with "input" key.
            capture_events: If True, return (output, events) tuple.
                           If False, return just output string.

        Returns:
            If capture_events=True: (final_output, event_list) tuple
            If capture_events=False: final_output string only

        Raises:
            RuntimeError: If agent execution fails.

        Note:
            Streams events via ADK Runner pattern with async iteration.
            When capture_events=True, collects all events for trace
            extraction. Otherwise just extracts final response text.
        """
        from google.adk.runners import Runner
        from google.genai import types

        input_text = example.get("input", "")
        if not input_text:
            return ("", []) if capture_events else ""

        # Create runner (uses adapter's session service)
        runner = Runner(
            agent=self.agent,
            app_name=self._app_name,
            session_service=self._session_service,
        )

        # Create user message content
        content = types.Content(
            role="user",
            parts=[types.Part(text=input_text)],
        )

        # Create session in session service first (required by ADK Runner)
        session = await self._session_service.create_session(
            app_name=self._app_name,
            user_id="eval_user",
        )
        session_id = session.id

        self._logger.debug(
            "adapter.session.created",
            session_id=session_id,
        )

        # Execute and collect events for output extraction
        events: list[Any] = []

        try:
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session_id,
                new_message=content,
            ):
                events.append(event)
        finally:
            # Clean up session after execution
            self._cleanup_session(session_id)

        # Extract final output using shared utility (filters thought parts)
        final_output = extract_final_output(events)

        return (final_output, events) if capture_events else final_output

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[ADKTrajectory, str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build trials from evaluation results for reflection.

        Terminology:
            - trial: One performance record {input, output, feedback, trajectory}
            - trials: Collection of trial records for a component

        Args:
            candidate: Current candidate component values.
            eval_batch: Evaluation results including trajectories and optional
                scorer metadata (e.g., from CriticScorer).
            components_to_update: List of component names to generate
                trials for.

        Returns:
            Mapping from component name to sequence of trials.
            Each trial contains input, output, feedback (with score and
            feedback_text), and optional trajectory.

        Examples:
            Generate trials for reflection:

            ```python
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            trials_dataset = await adapter.make_reflective_dataset(
                candidate, result, ["instruction"]
            )
            assert "instruction" in trials_dataset
            # Each trial has structured feedback
            trial = trials_dataset["instruction"][0]
            assert "input" in trial
            assert "output" in trial
            assert "feedback" in trial
            assert trial["feedback"]["score"] == 0.75
            ```

        Note:
            Operates on eval_batch trajectories (capture_traces=True required).
            Dataset format is compatible with proposer's trial-based interface.
            Scorer metadata (feedback_text, feedback_dimensions) from
            eval_batch.metadata is included in each trial's feedback dict.
        """
        self._logger.info(
            "adapter.make_reflective_dataset.start",
            num_trials=len(eval_batch.outputs),
            components=components_to_update,
        )

        # Build trials for each requested component
        result: dict[str, list[dict[str, Any]]] = {}

        for component in components_to_update:
            trials: list[dict[str, Any]] = []

            for i, (output, score) in enumerate(
                zip(eval_batch.outputs, eval_batch.scores, strict=True)
            ):
                # Get trajectory info if available
                trajectory = None
                if eval_batch.trajectories and i < len(eval_batch.trajectories):
                    trajectory = eval_batch.trajectories[i]

                # Get metadata if available
                metadata = None
                if eval_batch.metadata and i < len(eval_batch.metadata):
                    metadata = eval_batch.metadata[i]

                # Get input text if available
                input_text = ""
                if eval_batch.inputs and i < len(eval_batch.inputs):
                    input_text = eval_batch.inputs[i]

                trial = self._build_trial(
                    input_text=input_text,
                    output=output,
                    score=score,
                    trajectory=trajectory,
                    metadata=metadata,
                )
                trials.append(trial)

            result[component] = trials

        self._logger.info(
            "adapter.make_reflective_dataset.complete",
            num_components=len(result),
            total_trials=sum(len(t) for t in result.values()),
        )

        return result

    def _build_trace(self, trajectory: ADKTrajectory) -> dict[str, Any] | None:
        """Build trace dict from ADK trajectory data.

        Extracts execution details from ADK trajectory - the intermediate
        steps between input and output (tool calls, token usage, errors).

        Args:
            trajectory: ADK execution record with tool calls, tokens, etc.

        Returns:
            Trace dict with available details, or None if no trace data.
            Can include: tool_calls, tokens, error, and future fields
            like reasoning, state_deltas, etc.
        """
        trace: dict[str, Any] = {}

        if trajectory.tool_calls:
            trace["tool_calls"] = len(trajectory.tool_calls)
        if trajectory.error:
            trace["error"] = trajectory.error
        if trajectory.token_usage:
            trace["tokens"] = trajectory.token_usage.total_tokens

        # Return None if no trace data collected
        return trace if trace else None

    def _build_trial(
        self,
        input_text: str,
        output: str,
        score: float,
        trajectory: ADKTrajectory | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a single trial record for reflection.

        Terminology:
            - trial: One performance record {feedback, trajectory}
            - feedback: Critic evaluation {score, feedback_text, feedback_*}
            - trajectory: The journey from input to output with optional trace

        Args:
            input_text: The input that was given to the system.
            output: What the system produced.
            score: Evaluation score for this output.
            trajectory: Optional execution record with tool calls, state, etc.
            metadata: Optional scorer metadata dict (e.g., from CriticScorer).

        Returns:
            Trial dict with keys: feedback, trajectory.
            - feedback: score (mandatory), feedback_text, feedback_* (optional)
            - trajectory: input, output (mandatory), trace (optional)
        """
        # Build feedback dict (critic evaluation - stochastic)
        feedback: dict[str, Any] = {"score": score}

        # Add scorer metadata if present
        if metadata:
            if not isinstance(metadata, dict):
                self._logger.warning(
                    "adapter.metadata.malformed",
                    metadata_type=type(metadata).__name__,
                    expected_type="dict",
                )
            else:
                # Log metadata passthrough for debugging
                has_feedback = bool(metadata.get("feedback"))
                has_guidance = bool(metadata.get("actionable_guidance"))
                has_dimensions = bool(metadata.get("dimension_scores"))
                self._logger.debug(
                    "adapter.metadata.passthrough",
                    has_feedback=has_feedback,
                    has_guidance=has_guidance,
                    has_dimensions=has_dimensions,
                )

                # Add feedback_text if present and non-empty
                feedback_text = metadata.get("feedback")
                if (
                    feedback_text
                    and isinstance(feedback_text, str)
                    and feedback_text.strip()
                ):
                    feedback["feedback_text"] = feedback_text.strip()

                # Add feedback_guidance if present and non-empty
                guidance = metadata.get("actionable_guidance")
                if guidance and isinstance(guidance, str) and guidance.strip():
                    feedback["feedback_guidance"] = guidance.strip()

                # Add feedback_dimensions if present and non-empty
                dimension_scores = metadata.get("dimension_scores")
                if (
                    dimension_scores
                    and isinstance(dimension_scores, dict)
                    and dimension_scores
                ):
                    feedback["feedback_dimensions"] = dimension_scores

        # Build trajectory dict (the journey: input → [trace] → output)
        # input and output are always present, trace is optional
        trajectory_dict: dict[str, Any] = {
            "input": input_text,
            "output": output,
        }

        # Add optional trace (execution details between input and output)
        if trajectory:
            trace = self._build_trace(trajectory)
            if trace:
                trajectory_dict["trace"] = trace

        # Build trial record: feedback + trajectory
        trial: dict[str, Any] = {
            "feedback": feedback,
            "trajectory": trajectory_dict,
        }

        return trial

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new component texts based on trials.

        Delegates to AsyncReflectiveMutationProposer to generate improved
        component text via LLM reflection on trials. When the proposer returns
        None (no trials), falls back to unchanged candidate values.

        Args:
            candidate: Current candidate component texts (name → text).
            reflective_dataset: Trials from make_reflective_dataset().
                Maps component name to list of trial records.
            components_to_update: Components to generate proposals for.

        Returns:
            Dictionary mapping component names to proposed component text.
            When proposer returns None, returns unchanged candidate values.

        Examples:
            Using the proposer to generate improved component text:

            ```python
            # After evaluation with traces
            result = await adapter.evaluate(batch, candidate, capture_traces=True)
            trials = await adapter.make_reflective_dataset(
                candidate, result, ["instruction"]
            )

            # Propose new component text via LLM reflection on trials
            new_texts = await adapter.propose_new_texts(
                candidate, trials, ["instruction"]
            )
            # new_texts["instruction"] contains proposed component text
            ```

        Note:
            Delegates to AsyncReflectiveMutationProposer for actual mutation
            generation. Falls back gracefully when no trials available.
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
