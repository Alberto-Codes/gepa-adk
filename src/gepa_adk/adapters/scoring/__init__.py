"""Scoring infrastructure for evolution evaluation.

Contains CriticScorer for LLM-based evaluation, LabelAgreementScorer for
labelled trainsets, RequireToolScorer for gating a scorer on a tool call,
and the create_critic() preset factory for
pre-configured critic agents.

Attributes:
    CriticScorer (class): LLM-based scorer using critic agents.
    LabelAgreementScorer (class): Exact-match scorer against labelled ``expected`` values.
    RequireToolScorer (class): Wrapper that scores 0.0 unless a named tool ran.
    SimpleCriticOutput (class): KISS schema with score + feedback.
    CriticOutput (class): Advanced schema with dimensions and guidance.
    SIMPLE_CRITIC_INSTRUCTION (str): Generic instruction for simple critics.
    ADVANCED_CRITIC_INSTRUCTION (str): Generic instruction for advanced critics.
    STRUCTURED_OUTPUT_CRITIC_INSTRUCTION (str): Preset instruction for structure evaluation.
    ACCURACY_CRITIC_INSTRUCTION (str): Preset instruction for factual accuracy evaluation.
    RELEVANCE_CRITIC_INSTRUCTION (str): Preset instruction for relevance evaluation.
    normalize_feedback (function): Normalizes critic output to trial format.
    create_critic (function): Factory for pre-configured critic agents by preset name.
    critic_presets (dict): Maps preset name to human-readable description.

Examples:
    Create a critic scorer with an executor:

    ```python
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from gepa_adk.adapters.scoring import CriticScorer, CriticOutput
    from gepa_adk.adapters.execution.agent_executor import AgentExecutor

    critic = LlmAgent(
        name="quality_critic",
        model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
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

Notes:
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
from gepa_adk.adapters.scoring.label_agreement import LabelAgreementScorer
from gepa_adk.adapters.scoring.require_tool import RequireToolScorer

__all__ = [
    "ACCURACY_CRITIC_INSTRUCTION",
    "ADVANCED_CRITIC_INSTRUCTION",
    "RELEVANCE_CRITIC_INSTRUCTION",
    "SIMPLE_CRITIC_INSTRUCTION",
    "STRUCTURED_OUTPUT_CRITIC_INSTRUCTION",
    "CriticOutput",
    "CriticScorer",
    "LabelAgreementScorer",
    "RequireToolScorer",
    "SimpleCriticOutput",
    "create_critic",
    "critic_presets",
    "normalize_feedback",
]
