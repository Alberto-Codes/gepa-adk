"""CriticScorer adapter for structured scoring with ADK critic agents.

This module provides the CriticScorer implementation that wraps ADK critic
agents to provide structured scoring with feedback, dimension scores, and
actionable guidance. The scorer implements the Scorer protocol, enabling
integration with gepa-adk's evaluation and evolution workflows.

Attributes:
    CriticScorer (class): Adapter that wraps ADK critic agents for scoring.
    CriticOutput (class): Pydantic schema for structured critic output.

Examples:
    Basic usage with LlmAgent critic:

    ```python
    from pydantic import BaseModel, Field
    from google.adk.agents import LlmAgent
    from gepa_adk.adapters.critic_scorer import CriticScorer, CriticOutput

    critic = LlmAgent(
        name="quality_critic",
        model="gemini-2.0-flash",
        instruction="Evaluate response quality...",
        output_schema=CriticOutput,
    )

    scorer = CriticScorer(critic_agent=critic)
    score, metadata = await scorer.async_score(
        input_text="What is Python?",
        output="Python is a programming language.",
    )
    ```

Note:
    This module wraps ADK critic agents to provide structured scoring.
    When using LlmAgent with output_schema, the agent can ONLY reply and
    CANNOT use any tools (ADK constraint). For evaluations requiring tool
    usage, use a SequentialAgent with tool-enabled agents before the
    output-constrained scorer.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import structlog
from google.adk.agents import BaseAgent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

from gepa_adk.domain.exceptions import (
    CriticOutputParseError,
    MissingScoreFieldError,
    ScoringError,
)
from gepa_adk.utils.events import extract_final_output

logger = structlog.get_logger(__name__)


class CriticOutput(BaseModel):
    """Expected structured output format from critic agents.

    This schema defines the expected JSON structure that critic agents
    should return when configured with output_schema. The score field is
    required, while other fields are optional and will be preserved in
    metadata.

    Attributes:
        score: Score value between 0.0 and 1.0 (required).
        feedback: Human-readable feedback text (optional).
        dimension_scores: Per-dimension evaluation scores (optional).
        actionable_guidance: Specific improvement suggestions (optional).

    Examples:
        Example critic output:

        ```json
        {
            "score": 0.75,
            "feedback": "Good response but could be more concise",
            "dimension_scores": {
                "accuracy": 0.9,
                "clarity": 0.6,
                "completeness": 0.8
            },
            "actionable_guidance": "Reduce response length by 30%"
        }
        ```

    Note:
        All critic agents using this schema must return structured JSON.
        When this schema is used as output_schema on an LlmAgent, the
        agent can ONLY reply and CANNOT use any tools. This is acceptable
        for critic agents focused on scoring.
    """

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score from 0.0 to 1.0",
    )
    feedback: str = Field(
        default="",
        description="Human-readable feedback",
    )
    dimension_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension scores",
    )
    actionable_guidance: str = Field(
        default="",
        description="Improvement suggestions",
    )


class CriticScorer:
    """Adapter that wraps ADK critic agents to provide structured scoring.

    CriticScorer implements the Scorer protocol, enabling integration with
    gepa-adk's evaluation and evolution workflows. It executes ADK critic
    agents (LlmAgent, SequentialAgent, etc.) and extracts structured scores
    with metadata from their outputs.

    Attributes:
        critic_agent (BaseAgent): ADK agent configured for evaluation.
        _session_service (BaseSessionService): Session service for state
            management.
        _app_name (str): Application name for session identification.
        _logger (structlog.BoundLogger): Bound logger with scorer context.

    Examples:
        Basic usage:

        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk.adapters.critic_scorer import CriticScorer, CriticOutput

        critic = LlmAgent(
            name="quality_critic",
            model="gemini-2.0-flash",
            instruction="Evaluate response quality...",
            output_schema=CriticOutput,
        )

        scorer = CriticScorer(critic_agent=critic)
        score, metadata = await scorer.async_score(
            input_text="What is Python?",
            output="Python is a programming language.",
        )
        ```

    Note:
        Adapter wraps ADK critic agents to provide structured scoring.
        Implements Scorer protocol for compatibility with evolution engine.
        Creates isolated sessions per scoring call unless session_id provided.
    """

    def __init__(
        self,
        critic_agent: BaseAgent,
        session_service: BaseSessionService | None = None,
        app_name: str = "critic_scorer",
    ) -> None:
        """Initialize CriticScorer with critic agent.

        Args:
            critic_agent: ADK agent (LlmAgent or workflow agent) configured
                for evaluation.
            session_service: Optional session service for state management.
                If None, creates an InMemorySessionService.
            app_name: Application name for session identification.

        Raises:
            TypeError: If critic_agent is not a BaseAgent instance.
            ValueError: If app_name is empty string.

        Examples:
            With default session service:

            ```python
            scorer = CriticScorer(critic_agent=critic)
            ```

            With custom session service:

            ```python
            from google.adk.sessions import FirestoreSessionService

            session_service = FirestoreSessionService(project_id="my-project")
            scorer = CriticScorer(
                critic_agent=critic,
                session_service=session_service,
            )
            ```

        Note:
            Creates logger with scorer context and validates agent type.
            Default session service is InMemorySessionService if not provided.
        """
        if not isinstance(critic_agent, BaseAgent):
            raise TypeError(f"critic_agent must be BaseAgent, got {type(critic_agent)}")

        if not app_name or not app_name.strip():
            raise ValueError("app_name cannot be empty")

        self.critic_agent = critic_agent
        self._session_service = session_service or InMemorySessionService()
        self._app_name = app_name.strip()

        # Bind logger with scorer context
        self._logger = logger.bind(
            scorer="CriticScorer",
            agent_name=self.critic_agent.name,
            app_name=self._app_name,
        )

        self._logger.info("scorer.initialized")

    def _format_critic_input(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> str:
        """Format input for critic agent evaluation.

        Builds a prompt that presents the input query, agent output, and
        optionally the expected output for the critic to evaluate.

        Args:
            input_text: The original input provided to the agent being evaluated.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.

        Returns:
            Formatted prompt string for the critic agent.

        Examples:
            Basic formatting:

            ```python
            prompt = scorer._format_critic_input(
                input_text="What is 2+2?",
                output="4",
                expected="4",
            )
            ```

        Note:
            Structures input for critic evaluation with clear sections.
            Format is designed to give critic context for evaluation.
            Expected output is included only if provided.
        """
        parts = [
            "Input Query:",
            input_text,
            "",
            "Agent Output:",
            output,
        ]

        if expected is not None:
            parts.extend(
                [
                    "",
                    "Expected Output:",
                    expected,
                ]
            )

        parts.append("")
        parts.append(
            "Please evaluate the agent output and provide a score with feedback."
        )

        return "\n".join(parts)

    def _parse_critic_output(self, output_text: str) -> tuple[float, dict[str, Any]]:
        """Parse critic agent output and extract score with metadata.

        Parses the critic's output text as JSON and extracts the score field
        along with optional metadata (feedback, dimension_scores,
        actionable_guidance, and any additional fields).

        Args:
            output_text: Raw text output from critic agent.

        Returns:
            Tuple of (score, metadata) where:
            - score: Float value extracted from output
            - metadata: Dict containing feedback, dimension_scores,
                actionable_guidance, and any additional fields

        Raises:
            CriticOutputParseError: If output cannot be parsed as JSON.
            MissingScoreFieldError: If parsed JSON lacks required score field.

        Examples:
            Parse structured output:

            ```python
            output = '{"score": 0.75, "feedback": "Good", "dimension_scores": {"accuracy": 0.9}}'
            score, metadata = scorer._parse_critic_output(output)
            assert score == 0.75
            assert metadata["feedback"] == "Good"
            ```

        Note:
            Safely extracts score and metadata from critic JSON output.
            Preserves all fields from parsed JSON in metadata, not just
            the known CriticOutput schema fields. This allows for extensibility.
        """
        # Parse JSON output
        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as e:
            raise CriticOutputParseError(
                f"Critic output is not valid JSON: {e}",
                raw_output=output_text,
                parse_error=str(e),
                cause=e,
            ) from e

        # Validate parsed output is a dict
        if not isinstance(parsed, dict):
            raise CriticOutputParseError(
                f"Critic output must be a JSON object, got {type(parsed).__name__}",
                raw_output=output_text,
                parse_error="Not a JSON object",
            )

        # Extract required score field
        if "score" not in parsed:
            raise MissingScoreFieldError(
                "Critic output missing required 'score' field",
                parsed_output=parsed,
            )

        score = parsed["score"]
        if not isinstance(score, (int, float)):
            raise MissingScoreFieldError(
                f"Score field must be numeric, got {type(score).__name__}",
                parsed_output=parsed,
            )

        # Build metadata dict with known fields and any additional fields
        metadata: dict[str, Any] = {}

        # Extract known fields if present
        if "feedback" in parsed:
            metadata["feedback"] = str(parsed["feedback"])
        if "dimension_scores" in parsed:
            # Preserve dimension_scores as-is (may contain non-numeric values)
            metadata["dimension_scores"] = parsed["dimension_scores"]
        if "actionable_guidance" in parsed:
            metadata["actionable_guidance"] = str(parsed["actionable_guidance"])

        # Preserve any additional fields
        known_fields = {"score", "feedback", "dimension_scores", "actionable_guidance"}
        for key, value in parsed.items():
            if key not in known_fields:
                metadata[key] = value

        return float(score), metadata

    def _extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text that may contain markdown code blocks.

        Minimal implementation - tries direct parse and markdown extraction.
        A more robust implementation will be added per GitHub issue #78.

        Args:
            text: Text that may contain JSON.

        Returns:
            Extracted JSON string, or original text if extraction fails.
        """
        # Try parsing the entire text as-is
        try:
            json.loads(text.strip())
            return text.strip()
        except json.JSONDecodeError:
            pass

        # Extract from markdown code blocks (```json ... ``` or ``` ... ```)
        json_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        matches = re.findall(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        for match in matches:
            try:
                json.loads(match.strip())
                return match.strip()
            except json.JSONDecodeError:
                continue

        # Try to find JSON object embedded in text (minimal regex for { ... })
        # Look for opening brace and try to find matching closing brace
        brace_start = text.find("{")
        if brace_start != -1:
            # Try to find the matching closing brace
            # NOTE: This algorithm doesn't account for braces within string literals
            # (e.g., JSON with template strings like "instruction": "Use {variable}").
            # This is a minimal implementation; a more robust parser will be added
            # per GitHub issue #78.
            depth = 0
            for i in range(brace_start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[brace_start : i + 1]
                        try:
                            json.loads(candidate)
                            return candidate
                        except json.JSONDecodeError:
                            break

        # Return original text (will fail with clear error message)
        return text

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
        session_id: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output asynchronously using the critic agent.

        Executes the critic agent with formatted input and extracts structured
        score and metadata from the response.

        Args:
            input_text: The original input provided to the agent being evaluated.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.
            session_id: Optional session ID to share state with main agent
                workflow. If None, creates an isolated session.

        Returns:
            Tuple of (score, metadata) where:
            - score: Float value, conventionally 0.0-1.0
            - metadata: Dict with feedback, dimension_scores,
                actionable_guidance, and any additional fields

        Raises:
            CriticOutputParseError: If critic output is not valid JSON.
            MissingScoreFieldError: If score field missing from output.

        Examples:
            Basic async scoring:

            ```python
            score, metadata = await scorer.async_score(
                input_text="What is Python?",
                output="Python is a programming language.",
            )
            ```

            With session sharing:

            ```python
            score, metadata = await scorer.async_score(
                input_text="...",
                output="...",
                session_id="existing_session_123",
            )
            ```

        Note:
            Orchestrates critic agent execution and extracts structured output.
            Creates isolated session unless session_id provided for state sharing.
        """
        self._logger.debug(
            "scorer.async_score.start",
            input_preview=input_text[:50] if input_text else "",
            output_preview=output[:50] if output else "",
            has_expected=expected is not None,
            session_id=session_id,
        )

        # Format input for critic
        critic_input = self._format_critic_input(input_text, output, expected)

        # Create or reuse session and get valid session_id
        effective_session_id: str
        if session_id is None:
            # Create isolated session
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id="critic_user",
                session_id=None,  # Let service generate unique ID
            )
            # Type guard: session service should always return valid session
            # Note: ADK Session uses 'id' field, not 'session_id'
            if session is None or not hasattr(session, "id"):
                raise ScoringError("Session service returned invalid session")
            effective_session_id = str(session.id)
        else:
            # Use provided session_id - check if it exists, create if not
            existing_session = await self._session_service.get_session(
                app_name=self._app_name,
                user_id="critic_user",
                session_id=session_id,
            )
            if existing_session is None:
                # Session doesn't exist, create it with the provided ID
                await self._session_service.create_session(
                    app_name=self._app_name,
                    user_id="critic_user",
                    session_id=session_id,
                )
            effective_session_id = session_id

        # Create runner
        runner = Runner(
            agent=self.critic_agent,
            app_name=self._app_name,
            session_service=self._session_service,
        )

        # Create user message content
        content = types.Content(
            role="user",
            parts=[types.Part(text=critic_input)],
        )

        # Execute critic agent and collect events
        events: list[Any] = []
        try:
            async for event in runner.run_async(
                user_id="critic_user",
                session_id=effective_session_id,
                new_message=content,
            ):
                events.append(event)
        except Exception as e:
            self._logger.error(
                "scorer.async_score.execution_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ScoringError(
                f"Critic agent execution failed: {e}",
                cause=e,
            ) from e

        # Extract final output using shared utility (filters thought parts)
        final_output = extract_final_output(events)

        if not final_output:
            raise ScoringError(
                "Critic agent returned empty output",
            )

        # Parse output and extract score
        try:
            score, metadata = self._parse_critic_output(final_output)
        except (CriticOutputParseError, MissingScoreFieldError) as e:
            self._logger.error(
                "scorer.async_score.parse_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Log multi-dimensional scoring context if present
        log_context = {
            "score": score,
            "has_feedback": "feedback" in metadata,
            "has_dimension_scores": "dimension_scores" in metadata,
            "has_actionable_guidance": "actionable_guidance" in metadata,
        }
        if "dimension_scores" in metadata:
            log_context["dimension_count"] = len(metadata["dimension_scores"])

        self._logger.info(
            "scorer.async_score.complete",
            **log_context,
        )

        return score, metadata

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output synchronously using the critic agent.

        Synchronous wrapper around async_score() using asyncio.run().

        Args:
            input_text: The original input provided to the agent being evaluated.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.

        Returns:
            Tuple of (score, metadata) where:
            - score: Float value, conventionally 0.0-1.0
            - metadata: Dict with feedback, dimension_scores,
                actionable_guidance, and any additional fields

        Raises:
            CriticOutputParseError: If critic output is not valid JSON.
            MissingScoreFieldError: If score field missing from output.

        Examples:
            Basic sync scoring:

            ```python
            score, metadata = scorer.score(
                input_text="What is 2+2?",
                output="4",
                expected="4",
            )
            ```

        Note:
            Operates synchronously by wrapping async_score() with asyncio.run().
            Uses asyncio.run() to execute async_score(). Prefer async_score()
            for better performance in async contexts.
        """
        return asyncio.run(self.async_score(input_text, output, expected))
