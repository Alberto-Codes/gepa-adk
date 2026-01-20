"""Trial building utilities for reflection datasets.

This module provides a shared TrialBuilder class for constructing trial records
from evaluation results. Both ADKAdapter and MultiAgentAdapter use this to build
consistent trial structures for reflection.

Terminology:
    - **trial**: One performance record {feedback, trajectory}
    - **feedback**: Critic evaluation {score, feedback_text, feedback_*}
    - **trajectory**: The journey from input to output with optional trace

Attributes:
    TrialBuilder (class): Builder for trial records from evaluation results.

Examples:
    Build a trial record:

    ```python
    from gepa_adk.adapters.trial_builder import TrialBuilder

    builder = TrialBuilder()
    trial = builder.build_trial(
        input_text="What is 2+2?",
        output="4",
        score=0.95,
        metadata={"feedback": "Correct answer"},
    )
    assert trial["feedback"]["score"] == 0.95
    assert trial["trajectory"]["input"] == "What is 2+2?"
    ```

See Also:
    - [`gepa_adk.adapters.adk_adapter`][gepa_adk.adapters.adk_adapter]:
      Uses TrialBuilder for single-agent trials.
    - [`gepa_adk.adapters.multi_agent`][gepa_adk.adapters.multi_agent]:
      Uses TrialBuilder for multi-agent pipeline trials.

Note:
    This implements the GEPA whitepaper trial structure where score and
    feedback_text are mandatory, with optional extras like feedback_dimensions
    and feedback_guidance passed through when available.
"""

from typing import Any

import structlog


class TrialBuilder:
    """Build trial records for reflection datasets.

    Constructs consistent trial structures following the GEPA whitepaper format.
    Extracts feedback fields from scorer metadata and builds trajectory dicts.

    Attributes:
        _logger (structlog.BoundLogger): Logger for metadata passthrough debugging.

    Examples:
        Basic trial building:

        ```python
        builder = TrialBuilder()

        # With minimal data
        trial = builder.build_trial(
            input_text="Hello",
            output="Hi there!",
            score=0.8,
        )

        # With full metadata
        trial = builder.build_trial(
            input_text="Explain AI",
            output="AI is...",
            score=0.9,
            metadata={
                "feedback": "Clear explanation",
                "dimension_scores": {"clarity": 0.95},
                "actionable_guidance": "Add examples",
            },
            extra_trajectory={"component": "instruction"},
        )
        ```

    See Also:
        - [`build_feedback`][gepa_adk.adapters.trial_builder.TrialBuilder.build_feedback]:
          Build just the feedback dict.

    Note:
        All optional metadata fields are validated before inclusion to prevent
        malformed data from propagating to reflection prompts.
    """

    def __init__(self) -> None:
        """Initialize the TrialBuilder.

        Examples:
            ```python
            builder = TrialBuilder()
            ```

        Note:
            Creates a module-scoped logger for metadata passthrough debugging.
        """
        self._logger = structlog.get_logger(__name__)

    def build_feedback(
        self,
        score: float,
        metadata: dict[str, Any] | None = None,
        *,
        error: str | None = None,
        log_passthrough: bool = False,
    ) -> dict[str, Any]:
        """Build the feedback dict from score and metadata.

        Extracts and validates feedback fields from scorer metadata, including
        feedback_text, feedback_guidance, and feedback_dimensions.

        Args:
            score: Evaluation score (mandatory).
            metadata: Optional scorer metadata dict containing:
                - feedback: Text feedback from critic.
                - actionable_guidance: Improvement suggestions.
                - dimension_scores: Per-dimension score breakdown.
            error: Optional error message to include in feedback.
            log_passthrough: If True, log debug info about metadata extraction.

        Returns:
            Feedback dict with keys:
                - score (mandatory): The evaluation score.
                - feedback_text (if available): Text feedback from critic.
                - feedback_guidance (if available): Improvement suggestions.
                - feedback_dimensions (if available): Dimension score breakdown.
                - error (if provided): Error message from execution.

        Examples:
            ```python
            builder = TrialBuilder()

            # Minimal feedback
            feedback = builder.build_feedback(0.75)
            assert feedback == {"score": 0.75}

            # With metadata
            feedback = builder.build_feedback(
                0.85,
                metadata={
                    "feedback": "Good work",
                    "dimension_scores": {"accuracy": 0.9},
                },
            )
            assert "feedback_text" in feedback
            ```

        Note:
            Only non-empty strings and dicts are included to keep feedback clean.
        """
        feedback: dict[str, Any] = {"score": score}

        # Add scorer metadata if present
        if metadata:
            if not isinstance(metadata, dict):
                self._logger.warning(
                    "trial_builder.metadata.malformed",
                    metadata_type=type(metadata).__name__,
                    expected_type="dict",
                )
            else:
                # Log metadata passthrough for debugging if requested
                if log_passthrough:
                    has_feedback = bool(metadata.get("feedback"))
                    has_guidance = bool(metadata.get("actionable_guidance"))
                    has_dimensions = bool(metadata.get("dimension_scores"))
                    self._logger.debug(
                        "trial_builder.metadata.passthrough",
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

        # Add error if present
        if error:
            feedback["error"] = error

        return feedback

    def build_trial(
        self,
        input_text: str | None,
        output: str,
        score: float,
        metadata: dict[str, Any] | None = None,
        *,
        error: str | None = None,
        trace: dict[str, Any] | None = None,
        extra_trajectory: dict[str, Any] | None = None,
        log_passthrough: bool = False,
    ) -> dict[str, Any]:
        """Build a complete trial record for reflection.

        Constructs a trial with feedback and trajectory dicts following the
        GEPA whitepaper structure.

        Args:
            input_text: The input that was given to the system. Can be None for
                pipelines where input context is implicit.
            output: What the system produced.
            score: Evaluation score for this output.
            metadata: Optional scorer metadata dict (from CriticScorer).
            error: Optional error message from execution.
            trace: Optional execution trace dict (tool calls, state, tokens).
            extra_trajectory: Optional extra fields to include in trajectory
                (e.g., component name, component value, tokens).
            log_passthrough: If True, log debug info about metadata extraction.

        Returns:
            Trial dict with keys:
                - feedback: Evaluation feedback (score, feedback_text, etc.)
                - trajectory: Execution journey (input, output, trace, etc.)

        Examples:
            ```python
            builder = TrialBuilder()

            # Simple trial
            trial = builder.build_trial(
                input_text="What is Python?",
                output="A programming language",
                score=0.9,
            )
            assert trial["feedback"]["score"] == 0.9
            assert trial["trajectory"]["output"] == "A programming language"

            # With trace and extra trajectory data
            trial = builder.build_trial(
                input_text="Count to 3",
                output="1, 2, 3",
                score=1.0,
                trace={"tool_calls": [{"name": "count"}]},
                extra_trajectory={"component": "counter"},
            )
            assert "trace" in trial["trajectory"]
            assert trial["trajectory"]["component"] == "counter"
            ```

        Note:
            Optional input is only included in trajectory when not None,
            supporting pipelines where input context is implicit.
        """
        # Build feedback dict
        feedback = self.build_feedback(
            score,
            metadata,
            error=error,
            log_passthrough=log_passthrough,
        )

        # Build trajectory dict
        trajectory: dict[str, Any] = {"output": output}

        # Add input if available
        if input_text is not None:
            trajectory["input"] = input_text

        # Add trace if available
        if trace:
            trajectory["trace"] = trace

        # Add extra trajectory fields if provided
        if extra_trajectory:
            trajectory.update(extra_trajectory)

        # Build trial record
        return {
            "feedback": feedback,
            "trajectory": trajectory,
        }
