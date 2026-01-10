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

from gepa_adk.domain.trajectory import ADKTrajectory
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

            # Process each example in the batch
            for i, example in enumerate(batch):
                self._logger.debug(
                    "adapter.evaluate.example",
                    example_index=i,
                    example_input=example.get("input", "")[:50],
                )

                try:
                    # Run the agent for this example
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

            self._logger.info(
                "adapter.evaluate.complete",
                batch_size=len(batch),
                avg_score=sum(scores) / len(scores) if scores else 0.0,
            )

            return EvaluationBatch(
                outputs=outputs,
                scores=scores,
                trajectories=None,  # US2 will implement trace capture
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

    async def _run_single_example(self, example: dict[str, Any]) -> str:
        """Execute agent on a single input example.

        Args:
            example: Input example with "input" key.

        Returns:
            Final text output from the agent.

        Raises:
            RuntimeError: If agent execution fails.

        Note:
            Uses ADK Runner pattern with async event streaming.
            Extracts final response text from event stream.
        """
        from google.adk.runners import Runner
        from google.genai import types

        input_text = example.get("input", "")
        if not input_text:
            return ""

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
        async for event in runner.run_async(
            user_id="eval_user",
            session_id="eval_session",  # US4 will make this unique per example
            new_message=content,
        ):
            if event.is_final_response():
                # Extract text from response content
                if event.actions and event.actions.response_content:
                    for part in event.actions.response_content:
                        if hasattr(part, "text") and part.text:
                            final_output = part.text
                            break

        return final_output

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
        raise NotImplementedError("Phase 5 (US3) implementation")

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
