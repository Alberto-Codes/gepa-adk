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
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import structlog
from google.adk.agents import LlmAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai.types import Content, Part

from gepa_adk.adapters.component_handlers import OutputSchemaHandler, get_handler
from gepa_adk.adapters.trial_builder import TrialBuilder
from gepa_adk.adapters.video_blob_service import VideoBlobService
from gepa_adk.domain.exceptions import EvaluationError
from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord
from gepa_adk.domain.types import (
    COMPONENT_OUTPUT_SCHEMA,
    SchemaConstraints,
    TrajectoryConfig,
)
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.agent_executor import AgentExecutorProtocol, ExecutionStatus
from gepa_adk.ports.scorer import Scorer
from gepa_adk.ports.video_blob_service import VideoBlobServiceProtocol
from gepa_adk.utils.events import extract_trajectory

if TYPE_CHECKING:
    pass

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
        from gepa_adk.adapters.agent_executor import AgentExecutor

        agent = LlmAgent(
            name="helper",
            model="gemini-2.5-flash",
            instruction="Be helpful and concise",
        )
        scorer = MyScorer()  # Implements Scorer protocol
        executor = AgentExecutor()
        adapter = ADKAdapter(agent, scorer, executor)

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
        executor: AgentExecutorProtocol,
        max_concurrent_evals: int = 5,
        session_service: BaseSessionService | None = None,
        app_name: str = "gepa_adk_eval",
        trajectory_config: TrajectoryConfig | None = None,
        proposer: AsyncReflectiveMutationProposer | None = None,
        reflection_agent: LlmAgent | None = None,
        reflection_output_field: str | None = None,
        schema_constraints: SchemaConstraints | None = None,
        video_service: VideoBlobServiceProtocol | None = None,
    ) -> None:
        """Initialize the ADK adapter with agent and scorer.

        Args:
            agent: The ADK LlmAgent to evaluate with different instructions.
            scorer: Scorer implementation for evaluating agent outputs.
            executor: AgentExecutorProtocol implementation for unified agent execution.
                The executor handles session management and execution, enabling feature
                parity across all agent types.
            max_concurrent_evals: Maximum number of concurrent evaluations to run
                in parallel. Must be at least 1. Defaults to 5.
            session_service: Optional session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for session identification.
            trajectory_config: Configuration for trajectory extraction behavior.
                If None, uses TrajectoryConfig defaults (secure, all features enabled).
            proposer: Optional mutation proposer for generating improved instructions
                via LLM reflection. If provided, takes precedence over reflection_agent.
            reflection_agent: ADK LlmAgent to use for reflection operations.
                Either this or proposer must be provided. When provided, creates an
                ADK-based reflection function and passes it to a new proposer.
            reflection_output_field: Field name to extract from structured output when
                reflection_agent has an output_schema. When the reflection agent returns
                structured output (dict), this specifies which field contains the proposed
                text. For schema evolution, use "class_definition" with a SchemaProposal
                output_schema. Only used when reflection_agent is provided.
            schema_constraints: Optional SchemaConstraints for output_schema evolution.
                When provided, proposed schema mutations are validated against these
                constraints. Mutations that violate constraints (e.g., remove required
                fields) are rejected and the original schema is preserved.
            video_service: Optional VideoBlobServiceProtocol for multimodal input support.
                When provided, enables processing of trainset examples with 'videos' field.
                If None, defaults to a new VideoBlobService instance.

        Raises:
            TypeError: If agent is not an LlmAgent instance.
            TypeError: If scorer does not satisfy Scorer protocol.
            TypeError: If reflection_agent is provided but not an LlmAgent instance.
            ValueError: If app_name is empty string or max_concurrent_evals < 1.
            ValueError: If neither proposer nor reflection_agent is provided.

        Examples:
            Basic setup with reflection agent:

            ```python
            from gepa_adk.adapters.agent_executor import AgentExecutor

            reflection_agent = LlmAgent(name="reflector", model="gemini-2.5-flash")
            executor = AgentExecutor()
            adapter = ADKAdapter(
                agent, scorer, executor, reflection_agent=reflection_agent
            )
            ```

            With custom trajectory configuration:

            ```python
            config = TrajectoryConfig(
                redact_sensitive=True,
                max_string_length=5000,
            )
            executor = AgentExecutor()
            adapter = ADKAdapter(
                agent,
                scorer,
                executor,
                reflection_agent=reflection_agent,
                trajectory_config=config,
            )
            ```

            With shared session service:

            ```python
            from google.adk.sessions import InMemorySessionService
            from gepa_adk.adapters.agent_executor import AgentExecutor

            session_service = InMemorySessionService()
            executor = AgentExecutor(session_service=session_service)
            adapter = ADKAdapter(
                agent,
                scorer,
                executor,
                reflection_agent=reflection_agent,
                session_service=session_service,
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

        # Store executor for unified execution (T048)
        self._executor = executor

        # Store video service for multimodal input support
        self._video_service = video_service or VideoBlobService()

        # Store and apply schema constraints to output_schema handler
        self._schema_constraints = schema_constraints
        if schema_constraints is not None:
            handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
            if isinstance(handler, OutputSchemaHandler):
                handler.set_constraints(schema_constraints)

        # Bind logger with adapter context
        self._logger = logger.bind(
            adapter="ADKAdapter",
            agent_name=self.agent.name,
            app_name=self._app_name,
        )

        # Initialize trial builder for reflective dataset construction
        self._trial_builder = TrialBuilder()

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
                executor=self._executor,
                session_service=self._session_service,
                output_field=reflection_output_field,
            )
            self._proposer = AsyncReflectiveMutationProposer(
                adk_reflection_fn=adk_reflection_fn
            )
        else:
            raise ValueError(
                "Either proposer or reflection_agent must be provided. "
                "Use reflection_agent with an ADK LlmAgent for reflection operations."
            )

        self._logger.info("adapter.initialized")

    def cleanup(self) -> None:
        """Clean up adapter resources and clear handler constraints.

        Clears any schema constraints set on the OutputSchemaHandler to prevent
        constraint leakage between evolution runs. Should be called when the
        adapter is no longer needed.

        Note:
            OutputSchemaHandler is a singleton, so constraints set during one
            evolution run could affect subsequent runs if not cleared.
        """
        if self._schema_constraints is not None:
            handler = get_handler(COMPONENT_OUTPUT_SCHEMA)
            if isinstance(handler, OutputSchemaHandler):
                handler.set_constraints(None)
            self._logger.debug("adapter.cleanup.constraints_cleared")

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

        # Apply candidate components (instruction and/or output_schema) and save originals
        originals = self._apply_candidate(candidate)

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
            # Always restore original components via registry dispatch
            self._restore_agent(originals)

    def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
        """Apply candidate components to agent via registry dispatch.

        Args:
            candidate: Component name to evolved text mapping.
                Example: {"instruction": "Be helpful", "output_schema": "class ..."}

        Returns:
            Dictionary mapping component names to their original values.
            Original values are typed per handler (str for instruction,
            type[BaseModel] or None for output_schema).

        Raises:
            KeyError: If candidate contains unregistered component name.

        Note:
            Original values are captured before overwriting via ComponentHandler
            registry dispatch instead of hardcoded if/elif logic. Each handler's
            apply() method sets the new value and returns the original for
            later restoration.

        Examples:
            >>> originals = adapter._apply_candidate(
            ...     {
            ...         "instruction": "New prompt",
            ...         "output_schema": "class X(BaseModel): ...",
            ...     }
            ... )
            >>> originals
            {"instruction": "Original prompt", "output_schema": <class 'OriginalSchema'>}
        """
        originals: dict[str, Any] = {}

        for component_name, value in candidate.items():
            handler = get_handler(component_name)
            originals[component_name] = handler.apply(self.agent, value)
            self._logger.debug(
                "adapter.component.applied",
                component=component_name,
                value_preview=value[:50] if value else "",
            )

        return originals

    def _restore_agent(self, originals: dict[str, Any]) -> None:
        """Restore agent to original state via registry dispatch.

        Args:
            originals: Component name to original value mapping,
                as returned by _apply_candidate().

        Raises:
            KeyError: If originals contains unregistered component name.

        Note:
            Operates via ComponentHandler registry for dispatch. Each handler's
            restore() method reinstates the original value. Should always
            be called in finally block to ensure restoration even if
            evaluation fails.

        Examples:
            >>> adapter._restore_agent(
            ...     {"instruction": "Original prompt", "output_schema": OriginalSchema}
            ... )
            # agent.instruction == "Original prompt"
            # agent.output_schema == OriginalSchema
        """
        for component_name, original in originals.items():
            handler = get_handler(component_name)
            handler.restore(self.agent, original)

        self._logger.debug(
            "adapter.agent.restored",
            components=list(originals.keys()),
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
            Synthesizes trajectory by delegating to extract_trajectory utility
            with configured trajectory_config. This is the complete execution
            record for one batch example.
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
                # Wrap in domain exception per ADR-009 (preserve batch resilience)
                wrapped = EvaluationError(
                    f"Example {example_index} evaluation failed",
                    cause=e,
                    example_index=example_index,
                )

                self._logger.warning(
                    "adapter.evaluate.example.error",
                    example_index=example_index,
                    error=str(wrapped),
                )

                # Create error trajectory if capturing traces
                error_trajectory = None
                if capture_traces:
                    error_trajectory = self._build_trajectory(
                        events=[],
                        final_output="",
                        error=str(wrapped),
                    )

                return ("", 0.0, error_trajectory, None)

    async def _prepare_multimodal_content(
        self, example: dict[str, Any]
    ) -> Content | None:
        """Prepare multimodal Content from example with videos field.

        Args:
            example: Input example dict with optional 'input' text and 'videos' paths.

        Returns:
            Content object with text and video parts, or None if no videos present.

        Note:
            Orchestrates video loading via VideoBlobService and Content assembly.
            Text part is included first, followed by video parts in order.
        """
        videos = example.get("videos")
        if not videos:
            return None

        parts: list[Part] = []

        # Add text part first if present
        input_text = example.get("input")
        if input_text:
            parts.append(Part(text=input_text))

        # Load video parts
        video_parts = await self._video_service.prepare_video_parts(videos)
        parts.extend(video_parts)

        self._logger.debug(
            "adapter.multimodal_content.prepared",
            text_present=bool(input_text),
            video_count=len(videos),
            total_parts=len(parts),
        )

        return Content(parts=parts, role="user")

    async def _run_single_example(
        self, example: dict[str, Any], capture_events: bool = False
    ) -> tuple[str, list[Any]] | str:
        """Execute agent on a single input example via AgentExecutor.

        Args:
            example: Input example with "input" key and/or "videos" key.
            capture_events: If True, return (output, events) tuple.
                           If False, return just output string.

        Returns:
            If capture_events=True: (final_output, event_list) tuple
            If capture_events=False: final_output string only

        Raises:
            RuntimeError: If agent execution fails.

        Note:
            Delegates to AgentExecutor for unified execution path.
            When capture_events=True, collects all events for trace extraction.
            Supports multimodal inputs via 'videos' field in example.
        """
        input_text = example.get("input", "")
        videos = example.get("videos")

        # Check if we have any input (text or videos)
        if not input_text and not videos:
            return ("", []) if capture_events else ""

        # Prepare multimodal content if videos present
        input_content = await self._prepare_multimodal_content(example)

        result = await self._executor.execute_agent(
            agent=self.agent,
            input_text=input_text,
            input_content=input_content,
        )

        if result.status == ExecutionStatus.FAILED:
            raise RuntimeError(result.error_message or "Executor returned FAILED")

        final_output = result.extracted_value or ""
        events = result.captured_events or []

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

        Delegates to shared TrialBuilder for consistent trial structure.

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
        # Build trace from ADK trajectory if available
        trace = self._build_trace(trajectory) if trajectory else None

        return self._trial_builder.build_trial(
            input_text=input_text,
            output=output,
            score=score,
            metadata=metadata,
            trace=trace,
            log_passthrough=True,
        )

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
