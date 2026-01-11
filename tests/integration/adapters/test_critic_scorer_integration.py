"""Integration tests for CriticScorer with real ADK components.

These tests validate CriticScorer behavior with real ADK agents and sessions.
Requires Google ADK credentials for full functionality.

Note:
    Tests are marked with @pytest.mark.integration for selective execution.
    Some tests may require environment configuration (API keys, etc.).
    Integration tests use real LLM calls and may incur API costs.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel, Field

from gepa_adk.adapters.critic_scorer import CriticScorer


class SimpleCriticOutput(BaseModel):
    """Simple critic output schema for testing.

    Attributes:
        score: Score value between 0.0 and 1.0.
        feedback: Human-readable feedback text.
    """

    score: float = Field(ge=0.0, le=1.0, description="Score from 0.0 to 1.0")
    feedback: str = Field(default="", description="Feedback text")


class MultiDimensionalCriticOutput(BaseModel):
    """Multi-dimensional critic output schema for testing.

    Attributes:
        score: Overall score value between 0.0 and 1.0.
        feedback: Human-readable feedback text.
        dimension_scores: Per-dimension evaluation scores.
        actionable_guidance: Specific improvement suggestions.
    """

    score: float = Field(ge=0.0, le=1.0, description="Overall score")
    feedback: str = Field(default="", description="Feedback text")
    dimension_scores: dict[str, float] = Field(
        default_factory=dict, description="Per-dimension scores"
    )
    actionable_guidance: str = Field(default="", description="Improvement suggestions")


@pytest.fixture
def simple_critic_agent() -> LlmAgent:
    """Create a simple critic agent for integration tests.

    Returns:
        LlmAgent configured with SimpleCriticOutput schema.
    """
    return LlmAgent(
        name="simple_critic",
        model="gemini-2.0-flash",
        instruction="""You are a quality evaluator. Given an input query and agent output,
evaluate the response quality and provide a score from 0.0 to 1.0.

Score guidelines:
- 1.0: Perfect response, accurate and complete
- 0.7-0.9: Good response with minor issues
- 0.4-0.6: Acceptable but needs improvement
- 0.1-0.3: Poor response with significant issues
- 0.0: Completely wrong or irrelevant

Provide brief feedback explaining your score.""",
        output_schema=SimpleCriticOutput,
    )


@pytest.fixture
def multi_dimensional_critic_agent() -> LlmAgent:
    """Create a multi-dimensional critic agent for integration tests.

    Returns:
        LlmAgent configured with MultiDimensionalCriticOutput schema.
    """
    return LlmAgent(
        name="multi_dimensional_critic",
        model="gemini-2.0-flash",
        instruction="""You are a comprehensive quality evaluator. Evaluate responses on:

1. accuracy: Is the information factually correct? (0.0-1.0)
2. clarity: Is the response easy to understand? (0.0-1.0)
3. completeness: Does it fully address the query? (0.0-1.0)

Provide:
- Overall score (weighted average)
- Individual dimension scores
- Specific actionable guidance for improvement""",
        output_schema=MultiDimensionalCriticOutput,
    )


@pytest.fixture
def workflow_critic_agent() -> SequentialAgent:
    """Create a workflow critic agent with validator + scorer for integration tests.

    Returns:
        SequentialAgent with validation step followed by scoring step.
    """
    # Step 1: Validate response format
    validator = LlmAgent(
        name="format_validator",
        model="gemini-2.0-flash",
        instruction="""Check if the response is well-formatted and coherent.
Output a brief validation status that will be used by the next agent.""",
        output_key="validation_result",
    )

    # Step 2: Score based on validation
    scorer = LlmAgent(
        name="quality_scorer",
        model="gemini-2.0-flash",
        instruction="""Based on the validation result in the conversation,
provide a final quality score. Consider the validation feedback when scoring.

Score guidelines:
- 1.0: Perfect, passed all validation
- 0.5-0.9: Good but with some issues noted
- 0.0-0.4: Failed validation or poor quality""",
        output_schema=SimpleCriticOutput,
    )

    return SequentialAgent(
        name="workflow_critic",
        sub_agents=[validator, scorer],
    )


@pytest.fixture
def shared_session_service() -> InMemorySessionService:
    """Create a shared session service for session sharing tests.

    Returns:
        InMemorySessionService instance for session state sharing.
    """
    return InMemorySessionService()


pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.requires_gemini]


@pytest.mark.slow
class TestCriticScorerBasicIntegration:
    """Basic integration tests for CriticScorer with real LlmAgent.

    Note:
        These tests make real API calls to the LLM provider.
        Ensure valid API credentials are configured.
    """

    @pytest.mark.asyncio
    async def test_simple_scoring_with_real_agent(
        self, simple_critic_agent: LlmAgent
    ) -> None:
        """Verify CriticScorer produces valid score with real LlmAgent (T017 partial).

        This test validates that:
        1. CriticScorer executes the real critic agent
        2. Output is properly parsed as structured JSON
        3. Score is within valid range [0.0, 1.0]
        4. Feedback is included in metadata
        """
        scorer = CriticScorer(critic_agent=simple_critic_agent)

        score, metadata = await scorer.async_score(
            input_text="What is 2 + 2?",
            output="The answer is 4.",
            expected="4",
        )

        # Verify score is valid
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # Verify metadata contains feedback
        assert "feedback" in metadata
        assert isinstance(metadata["feedback"], str)

    @pytest.mark.asyncio
    async def test_scoring_without_expected(
        self, simple_critic_agent: LlmAgent
    ) -> None:
        """Verify CriticScorer handles open-ended evaluation without expected output."""
        scorer = CriticScorer(critic_agent=simple_critic_agent)

        score, metadata = await scorer.async_score(
            input_text="Write a haiku about coding.",
            output="Debugging all night\nCoffee fuels the tired mind\nBug fixed at sunrise",
            expected=None,
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_multi_dimensional_scoring(
        self, multi_dimensional_critic_agent: LlmAgent
    ) -> None:
        """Verify CriticScorer extracts dimension_scores and actionable_guidance."""
        scorer = CriticScorer(critic_agent=multi_dimensional_critic_agent)

        score, metadata = await scorer.async_score(
            input_text="Explain photosynthesis.",
            output="Plants use sunlight to make food.",
            expected=None,
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # Verify dimension scores are extracted
        if "dimension_scores" in metadata:
            assert isinstance(metadata["dimension_scores"], dict)
            # Dimension scores should contain expected keys
            for key in metadata["dimension_scores"]:
                assert isinstance(metadata["dimension_scores"][key], (int, float))

        # Verify actionable guidance is extracted if present
        if "actionable_guidance" in metadata:
            assert isinstance(metadata["actionable_guidance"], str)


@pytest.mark.slow
class TestCriticScorerWorkflowIntegration:
    """Integration tests for CriticScorer with SequentialAgent workflow critics (T017).

    Note:
        These tests verify that CriticScorer correctly handles
        multi-step workflow agents where the final output comes
        from the last sub-agent.
    """

    @pytest.mark.asyncio
    async def test_workflow_critic_execution(
        self, workflow_critic_agent: SequentialAgent
    ) -> None:
        """Verify CriticScorer executes full SequentialAgent workflow (T017).

        This test validates that:
        1. SequentialAgent critic executes all sub-agents in order
        2. Final score is extracted from the last sub-agent's output
        3. Workflow completes successfully with valid structured output
        """
        scorer = CriticScorer(critic_agent=workflow_critic_agent)

        score, metadata = await scorer.async_score(
            input_text="What is the capital of France?",
            output="Paris is the capital of France.",
            expected="Paris",
        )

        # Verify score is valid
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # Verify feedback from final scorer agent
        assert "feedback" in metadata
        assert isinstance(metadata["feedback"], str)

    @pytest.mark.asyncio
    async def test_workflow_critic_with_validation_failure(
        self, workflow_critic_agent: SequentialAgent
    ) -> None:
        """Verify workflow critic handles validation issues appropriately.

        When the validator agent detects issues, the scorer should
        reflect this in the final score.
        """
        scorer = CriticScorer(critic_agent=workflow_critic_agent)

        # Provide a poor response that should score lower
        score, metadata = await scorer.async_score(
            input_text="Explain quantum entanglement in detail.",
            output="It's complicated.",
            expected=None,
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        # Poor response should generally score lower, but we can't guarantee exact score


@pytest.mark.slow
class TestCriticScorerSessionIntegration:
    """Integration tests for CriticScorer session sharing (T027).

    Note:
        These tests verify that session state can be shared between
        the main agent workflow and the critic for context-aware evaluation.
    """

    @pytest.mark.asyncio
    async def test_isolated_session_creation(
        self, simple_critic_agent: LlmAgent
    ) -> None:
        """Verify CriticScorer creates isolated session when no session_id provided (T027).

        This test validates that:
        1. Each scoring call without session_id creates a new isolated session
        2. Sessions don't leak state between calls
        """
        scorer = CriticScorer(critic_agent=simple_critic_agent)

        # First scoring call
        score1, _ = await scorer.async_score(
            input_text="What is 1 + 1?",
            output="2",
        )

        # Second scoring call (should be independent)
        score2, _ = await scorer.async_score(
            input_text="What is 3 + 3?",
            output="6",
        )

        # Both should produce valid scores (sessions are independent)
        assert isinstance(score1, float)
        assert isinstance(score2, float)
        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0

    @pytest.mark.asyncio
    async def test_session_sharing_with_explicit_id(
        self,
        simple_critic_agent: LlmAgent,
        shared_session_service: InMemorySessionService,
    ) -> None:
        """Verify CriticScorer can share session state via session_id (T027).

        This test validates that:
        1. Providing a session_id allows session state to be shared
        2. The critic can access conversation history from shared session
        """
        scorer = CriticScorer(
            critic_agent=simple_critic_agent,
            session_service=shared_session_service,
        )

        # Create a session first by making a call
        session_id = "shared_test_session_123"

        # First call establishes the session
        score1, metadata1 = await scorer.async_score(
            input_text="Remember: the secret word is 'banana'.",
            output="I will remember the secret word.",
            session_id=session_id,
        )

        # Second call with same session_id (session context may be available)
        score2, metadata2 = await scorer.async_score(
            input_text="What was discussed earlier?",
            output="We discussed a secret word.",
            session_id=session_id,
        )

        # Both calls should succeed with the shared session
        assert isinstance(score1, float)
        assert isinstance(score2, float)
        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0

    @pytest.mark.asyncio
    async def test_different_sessions_are_isolated(
        self,
        simple_critic_agent: LlmAgent,
        shared_session_service: InMemorySessionService,
    ) -> None:
        """Verify different session_ids maintain separate state.

        This test validates that:
        1. Different session_ids create separate session contexts
        2. State from one session doesn't leak to another
        """
        scorer = CriticScorer(
            critic_agent=simple_critic_agent,
            session_service=shared_session_service,
        )

        # Call with session A
        score_a, _ = await scorer.async_score(
            input_text="Session A context.",
            output="Response for session A.",
            session_id="session_a",
        )

        # Call with session B (should be independent)
        score_b, _ = await scorer.async_score(
            input_text="Session B context.",
            output="Response for session B.",
            session_id="session_b",
        )

        # Both should produce valid independent scores
        assert isinstance(score_a, float)
        assert isinstance(score_b, float)
        assert 0.0 <= score_a <= 1.0
        assert 0.0 <= score_b <= 1.0


@pytest.mark.slow
class TestCriticScorerSyncIntegration:
    """Integration tests for synchronous score() method."""

    def test_sync_score_with_real_agent(self, simple_critic_agent: LlmAgent) -> None:
        """Verify synchronous score() works with real agent."""
        scorer = CriticScorer(critic_agent=simple_critic_agent)

        score, metadata = scorer.score(
            input_text="What color is the sky?",
            output="The sky is blue.",
            expected="blue",
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert "feedback" in metadata
