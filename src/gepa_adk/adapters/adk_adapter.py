"""ADK adapter implementation for AsyncGEPAAdapter protocol.

This module provides the concrete implementation of AsyncGEPAAdapter for
Google ADK agents, enabling evolutionary optimization of ADK agent instructions.

Note:
    This adapter bridges GEPA's evaluation patterns to ADK's agent/runner
    architecture, handling instruction overrides, trace capture, and session
    management per ADK conventions.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import structlog
from google.adk.agents import LlmAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService

from gepa_adk.domain.trajectory import ADKTrajectory, TokenUsage, ToolCallRecord
from gepa_adk.ports.adapter import EvaluationBatch
from gepa_adk.ports.scorer import Scorer

logger = structlog.get_logger(__name__)


class ADKAdapter:
    """ADK implementation of AsyncGEPAAdapter protocol.

    Bridges GEPA evaluation patterns to Google ADK's agent/runner architecture,
    enabling evolutionary optimization of ADK agents through instruction mutation
    and reflective learning.

    Attributes:
        agent: The ADK LlmAgent to evaluate with different candidate instructions.
        scorer: Scoring implementation for evaluating agent outputs.
        _session_service: Session service for managing agent state isolation.
        _app_name: Application name used for session management.
        _logger: Bound logger with adapter context for structured logging.

    Examples:
        Basic adapter setup:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters import ADKAdapter
        from gepa_adk.ports.scorer import Scorer

        agent = LlmAgent(
            name="helper",
            model="gemini-2.0-flash",
            instruction="Be helpful and concise"
        )
        scorer = MyScorer()  # Implements Scorer protocol
        adapter = ADKAdapter(agent=agent, scorer=scorer)

        # Evaluate with candidate instruction
        batch = [{"input": "What is 2+2?", "expected": "4"}]
        candidate = {"instruction": "Be very precise with math"}
        result = await adapter.evaluate(batch, candidate)
        ```

    Note:
        Implements AsyncGEPAAdapter[dict[str, Any], ADKTrajectory, str] protocol.
        All methods are async and follow ADK's async-first patterns.
    """

    def __init__(
        self,
        agent: LlmAgent,
        scorer: Scorer,
        session_service: BaseSessionService | None = None,
        app_name: str = "gepa_adk_eval",
    ) -> None:
        """Initialize the ADK adapter with agent and scorer.

        Args:
            agent: The ADK LlmAgent to evaluate with different instructions.
            scorer: Scorer implementation for evaluating agent outputs.
            session_service: Optional session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for session identification.

        Raises:
            TypeError: If agent is not an LlmAgent instance.
            TypeError: If scorer does not satisfy Scorer protocol.
            ValueError: If app_name is empty string.

        Examples:
            With default session service:

            ```python
            adapter = ADKAdapter(agent=agent, scorer=scorer)
            ```

            With custom session service:

            ```python
            from google.adk.sessions import FirestoreSessionService

            session_service = FirestoreSessionService(project_id="my-project")
            adapter = ADKAdapter(
                agent=agent,
                scorer=scorer,
                session_service=session_service,
                app_name="my_optimizer"
            )
            ```

        Note:
            The agent's original instruction is preserved and restored after
            each evaluation to ensure no side effects between evaluations.
        """
        # Type validation
        if not isinstance(agent, LlmAgent):
            raise TypeError(f"agent must be LlmAgent, got {type(agent)}")

        # Scorer protocol check (runtime_checkable)
        if not hasattr(scorer, "score") or not hasattr(scorer, "async_score"):
            raise TypeError(f"scorer must implement Scorer protocol, got {type(scorer)}")

        if not app_name or not app_name.strip():
            raise ValueError("app_name cannot be empty")

        self.agent = agent
        self.scorer = scorer
        self._session_service = session_service or InMemorySessionService()
        self._app_name = app_name.strip()

        # Bind logger with adapter context
        self._logger = logger.bind(
            adapter="ADKAdapter",
            agent_name=self.agent.name,
            app_name=self._app_name,
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
            result = await adapter.evaluate(
                batch, candidate, capture_traces=True
            )
            assert result.trajectories is not None
            assert len(result.trajectories) == len(batch)
            ```

        Note:
            Agent's original instruction is restored after evaluation completes,
            even if an exception occurs during evaluation.
        """
        self._logger.info(
            "adapter.evaluate.start",
            batch_size=len(batch),
            capture_traces=capture_traces,
        )

        # Handle empty batch case
        if not batch:
            self._logger.info("adapter.evaluate.complete", batch_size=0)
            return EvaluationBatch(outputs=[], scores=[], trajectories=None)

        # Apply candidate instruction (if present) and save original
        original_instruction = self._apply_candidate(candidate)

        try:
            outputs: list[str] = []
            scores: list[float] = []
            trajectories: list[ADKTrajectory] | None = [] if capture_traces else None

            # Process each example in the batch
            for i, example in enumerate(batch):
                self._logger.debug(
                    "adapter.evaluate.example",
                    example_index=i,
                    example_input=example.get("input", "")[:50],
                )

                try:
                    # Run the agent for this example
                    if capture_traces:
                        output, events = await self._run_single_example(
                            example, capture_events=True
                        )
                        # Build trajectory from collected events
                        trajectory = self._build_trajectory(
                            events=events,
                            final_output=output,
                            error=None,
                        )
                        trajectories.append(trajectory)  # type: ignore
                    else:
                        output = await self._run_single_example(example)
                    
                    outputs.append(output)

                    # Score the output
                    expected = example.get("expected")
                    score = await self.scorer.async_score(output, expected)
                    scores.append(score)

                except Exception as e:
                    # Handle execution errors gracefully
                    self._logger.warning(
                        "adapter.evaluate.example.error",
                        example_index=i,
                        error=str(e),
                    )
                    outputs.append("")
                    scores.append(0.0)
                    
                    # Add error trajectory if capturing traces
                    if capture_traces:
                        error_trajectory = self._build_trajectory(
                            events=[],
                            final_output="",
                            error=str(e),
                        )
                        trajectories.append(error_trajectory)  # type: ignore

            self._logger.info(
                "adapter.evaluate.complete",
                batch_size=len(batch),
                avg_score=sum(scores) / len(scores) if scores else 0.0,
            )

            return EvaluationBatch(
                outputs=outputs,
                scores=scores,
                trajectories=trajectories,
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
            Only modifies agent.instruction if "instruction" key is present
            in candidate. Otherwise, leaves instruction unchanged.
        """
        original_instruction = self.agent.instruction

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
            Always called in finally block to ensure restoration even
            if evaluation fails.
        """
        self.agent.instruction = original_instruction
        self._logger.debug(
            "adapter.instruction.restored",
            instruction=original_instruction[:50],
        )

    def _extract_tool_calls(self, events: list[Any]) -> list[ToolCallRecord]:
        """Extract tool call records from ADK Event stream.

        Args:
            events: List of ADK Event objects from runner.

        Returns:
            List of ToolCallRecord instances with tool name, arguments,
            and result (if available).

        Note:
            Extracts both function_call and function_response parts from
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
                                except Exception:
                                    pass
                            
                            # Extract arguments
                            args = getattr(fc, "args", {})
                            if not isinstance(args, dict):
                                args = {}
                            
                            tool_calls.append(
                                ToolCallRecord(
                                    name=name,
                                    arguments=args,
                                    result=None,  # Will be populated if response found
                                    timestamp=None,
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
            Only events with non-None state_delta attributes are processed.
            State deltas capture changes to session or agent state during
            execution.
        """
        state_deltas: list[dict[str, Any]] = []
        
        for event in events:
            if hasattr(event, "state_delta") and event.state_delta is not None:
                state_deltas.append({
                    "key": getattr(event.state_delta, "key", "unknown"),
                    "value": getattr(event.state_delta, "value", None),
                })
        
        return state_deltas

    def _extract_token_usage(self, events: list[Any]) -> TokenUsage | None:
        """Extract token usage metadata from ADK Event stream.

        Args:
            events: List of ADK Event objects from runner.

        Returns:
            TokenUsage instance if usage metadata found, None otherwise.

        Note:
            Looks for usage_metadata on final response events. Returns
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
            Orchestrates extraction of all trace components into single
            immutable trajectory object. This is the complete execution
            record for one batch example.
        """
        tool_calls = self._extract_tool_calls(events)
        state_deltas = self._extract_state_deltas(events)
        token_usage = self._extract_token_usage(events)
        
        return ADKTrajectory(
            tool_calls=tool_calls,
            state_deltas=state_deltas,
            token_usage=token_usage,
            final_output=final_output,
            error=error,
        )

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
            Uses ADK Runner pattern with async event streaming.
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

        # Execute and extract final response
        # Note: Session management (US4) will add session isolation here
        final_output = ""
        events: list[Any] = []
        
        async for event in runner.run_async(
            user_id="eval_user",
            session_id="eval_session",  # US4 will make this unique per example
            new_message=content,
        ):
            if capture_events:
                events.append(event)
            
            if event.is_final_response():
                # Extract text from response content
                if event.actions and event.actions.response_content:
                    for part in event.actions.response_content:
                        if hasattr(part, "text") and part.text:
                            final_output = part.text
                            break

        return (final_output, events) if capture_events else final_output

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[ADKTrajectory, str],
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
            result = await adapter.evaluate(
                batch, candidate, capture_traces=True
            )
            dataset = await adapter.make_reflective_dataset(
                candidate,
                result,
                ["instruction"]
            )
            assert "instruction" in dataset
            ```

        Note:
            Requires eval_batch to contain trajectories (capture_traces=True).
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
        trajectory: ADKTrajectory | None,
        component_name: str,
        component_value: str,
    ) -> dict[str, Any]:
        """Build a single reflection example in GEPA format.

        Args:
            output: Agent output text.
            score: Evaluation score for this output.
            trajectory: Optional trajectory with execution trace.
            component_name: Name of the component being evaluated.
            component_value: Current value of the component.

        Returns:
            Dictionary with GEPA-compatible reflection format containing
            'Inputs', 'Generated Outputs', and 'Feedback' keys.

        Note:
            The format matches GEPA's MutationProposer expectations.
            Trajectory context is included in Feedback when available.
        """
        # Build feedback string
        feedback_parts = [f"score: {score:.3f}"]
        
        if trajectory:
            if trajectory.tool_calls:
                feedback_parts.append(
                    f"tool_calls: {len(trajectory.tool_calls)}"
                )
            if trajectory.error:
                feedback_parts.append(f"error: {trajectory.error}")
            if trajectory.token_usage:
                feedback_parts.append(
                    f"tokens: {trajectory.token_usage.total_tokens}"
                )
        
        return {
            "Inputs": {
                component_name: component_value,
            },
            "Generated Outputs": output,
            "Feedback": ", ".join(feedback_parts),
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new component texts based on reflective dataset.

        Args:
            candidate: Current candidate component values.
            reflective_dataset: Dataset from make_reflective_dataset().
            components_to_update: Components to generate proposals for.

        Returns:
            Dictionary mapping component names to proposed new text values.

        Note:
            This method delegates to the mutation proposer (Issue #7).
            For now, returns unchanged candidate values as stub implementation.
        """
        raise NotImplementedError("Phase 7 (Polish) - stub delegates to MutationProposer")
