"""Adapters layer - External implementations of ports.

Adapters connect the domain logic to external systems (Google ADK, LiteLLM, etc.).
Each adapter implements one or more protocol interfaces from the ports layer.

Attributes:
    ADKAdapter (class): AsyncGEPAAdapter implementation for Google ADK agents.

Examples:
    Basic usage with Google ADK agent:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.adapters import ADKAdapter

    agent = LlmAgent(name="helper", model="gemini-2.0-flash")
    adapter = ADKAdapter(agent=agent, scorer=my_scorer)
    result = await adapter.evaluate(batch, candidate)
    ```

See Also:
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: AsyncGEPAAdapter protocol.
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Scorer protocol for metrics.
    - [`gepa_adk.domain.trajectory`][gepa_adk.domain.trajectory]: ADKTrajectory types.

Note:
    This layer ONLY contains adapters - they import from ports/ and domain/
    but never the reverse. This maintains hexagonal architecture boundaries.
"""

from gepa_adk.adapters.adk_adapter import ADKAdapter
from gepa_adk.adapters.agent_executor import AgentExecutor, SessionNotFoundError
from gepa_adk.adapters.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
    create_candidate_selector,
)
from gepa_adk.adapters.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.adapters.critic_scorer import CriticOutput, CriticScorer
from gepa_adk.adapters.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.adapters.workflow import (
    WorkflowAgentType,
    find_llm_agents,
    is_workflow_agent,
)

__all__ = [
    "ADKAdapter",
    "AgentExecutor",
    "SessionNotFoundError",
    "ParetoCandidateSelector",
    "CurrentBestCandidateSelector",
    "EpsilonGreedyCandidateSelector",
    "create_candidate_selector",
    "RoundRobinComponentSelector",
    "AllComponentSelector",
    "create_component_selector",
    "CriticScorer",
    "CriticOutput",
    "MultiAgentAdapter",
    "is_workflow_agent",
    "find_llm_agents",
    "WorkflowAgentType",
    "FullEvaluationPolicy",
    "SubsetEvaluationPolicy",
]
