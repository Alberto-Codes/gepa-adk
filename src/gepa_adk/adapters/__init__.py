"""Adapters layer - External implementations of ports.

Adapters connect the domain logic to external systems (Google ADK, LiteLLM, etc.).
Each adapter implements one or more protocol interfaces from the ports layer.

Attributes:
    ADKAdapter (class): AsyncGEPAAdapter implementation for Google ADK agents.
    TrialBuilder (class): Shared utility for building trial records in reflection datasets.

Examples:
    Basic usage with Google ADK agent:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.adapters import ADKAdapter

    agent = LlmAgent(name="helper", model="gemini-2.5-flash")
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
from gepa_adk.adapters.component_handlers import (
    ComponentHandlerRegistry,
    GenerateContentConfigHandler,
    InstructionHandler,
    OutputSchemaHandler,
    component_handlers,
    get_handler,
    register_handler,
)
from gepa_adk.adapters.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.adapters.critic_scorer import (
    ADVANCED_CRITIC_INSTRUCTION,
    SIMPLE_CRITIC_INSTRUCTION,
    CriticOutput,
    CriticScorer,
    SimpleCriticOutput,
    normalize_feedback,
)
from gepa_adk.adapters.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.adapters.stoppers import TimeoutStopper
from gepa_adk.adapters.trial_builder import TrialBuilder
from gepa_adk.adapters.video_blob_service import MAX_VIDEO_SIZE_BYTES, VideoBlobService
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
    # Component handlers
    "ComponentHandlerRegistry",
    "GenerateContentConfigHandler",
    "InstructionHandler",
    "OutputSchemaHandler",
    "component_handlers",
    "get_handler",
    "register_handler",
    # Component selectors
    "RoundRobinComponentSelector",
    "AllComponentSelector",
    "create_component_selector",
    # Critic schemas and helpers
    "CriticScorer",
    "SimpleCriticOutput",
    "CriticOutput",
    "SIMPLE_CRITIC_INSTRUCTION",
    "ADVANCED_CRITIC_INSTRUCTION",
    "normalize_feedback",
    # Multi-agent
    "MultiAgentAdapter",
    "is_workflow_agent",
    "find_llm_agents",
    "WorkflowAgentType",
    "FullEvaluationPolicy",
    "SubsetEvaluationPolicy",
    # Stoppers
    "TimeoutStopper",
    # Trial building
    "TrialBuilder",
    # Video blob service
    "VideoBlobService",
    "MAX_VIDEO_SIZE_BYTES",
]
