"""Scoring infrastructure for evolution evaluation.

Contains CriticScorer for LLM-based evaluation and the create_critic()
preset factory for pre-configured critic agents.

Attributes:
    CriticScorer: LLM-based scorer using critic agents.
    SimpleCriticOutput: KISS schema with score + feedback.
    CriticOutput: Advanced schema with dimensions and guidance.
    SIMPLE_CRITIC_INSTRUCTION: Generic instruction for simple critics.
    ADVANCED_CRITIC_INSTRUCTION: Generic instruction for advanced critics.
    STRUCTURED_OUTPUT_CRITIC_INSTRUCTION: Preset instruction for structure evaluation.
    ACCURACY_CRITIC_INSTRUCTION: Preset instruction for factual accuracy evaluation.
    RELEVANCE_CRITIC_INSTRUCTION: Preset instruction for relevance evaluation.
    normalize_feedback: Normalizes critic output to trial format.
    create_critic: Factory for pre-configured critic agents by preset name.
    critic_presets: Maps preset name to human-readable description.

Examples:
    Create a critic scorer with an executor:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.adapters.scoring import CriticScorer, CriticOutput
    from gepa_adk.adapters.execution.agent_executor import AgentExecutor

    critic = LlmAgent(
        name="quality_critic",
        model="gemini-2.5-flash",
        instruction="Evaluate response quality...",
        output_schema=CriticOutput,
    )
    executor = AgentExecutor()
    scorer = CriticScorer(critic_agent=critic, executor=executor)
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Scorer protocol that CriticScorer
        implements.
    - [`gepa_adk.adapters.evolution`][gepa_adk.adapters.evolution]: Adapters that accept
        scorers for evaluation.

Note:
    This package isolates critic-based scoring from other adapter concerns.
"""

from gepa_adk.adapters.scoring.critic_scorer import (
    ACCURACY_CRITIC_INSTRUCTION,
    ADVANCED_CRITIC_INSTRUCTION,
    RELEVANCE_CRITIC_INSTRUCTION,
    SIMPLE_CRITIC_INSTRUCTION,
    STRUCTURED_OUTPUT_CRITIC_INSTRUCTION,
    CriticOutput,
    CriticScorer,
    SimpleCriticOutput,
    create_critic,
    critic_presets,
    normalize_feedback,
)

__all__ = [
    "CriticScorer",
    "SimpleCriticOutput",
    "CriticOutput",
    "SIMPLE_CRITIC_INSTRUCTION",
    "ADVANCED_CRITIC_INSTRUCTION",
    "STRUCTURED_OUTPUT_CRITIC_INSTRUCTION",
    "ACCURACY_CRITIC_INSTRUCTION",
    "RELEVANCE_CRITIC_INSTRUCTION",
    "normalize_feedback",
    "create_critic",
    "critic_presets",
]
