"""Adapter layer convenience re-exports.

All public symbols are re-exported from their sub-package locations so that
``from gepa_adk.adapters import <symbol>`` continues to work. New code should
import from sub-packages directly. Note that the old flat-module paths
(e.g. ``gepa_adk.adapters.agent_executor``) have been reorganized into
sub-packages and are no longer available.

Sub-packages:
    execution/: Agent execution infrastructure (AgentExecutor, TrialBuilder).
    scoring/: Scoring infrastructure (CriticScorer, schemas, create_critic factory).
    evolution/: Core adapter implementations (ADKAdapter, MultiAgentAdapter).
    selection/: Selection strategies (candidates, components, evaluation).
    components/: Evolvable surface handlers (ComponentHandlerRegistry).
    workflow/: Workflow agent utilities (is_workflow_agent, find_llm_agents).
    media/: Multimodal adapters (VideoBlobService).
    stoppers/: Evolution stopping conditions (unchanged).

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

Compatibility:
    Tested against google-adk 1.20.0 through latest. All import paths used
    by gepa-adk (agents, sessions, runners, models, tools, genai types) are
    stable across this range. No compatibility shims are required — the core
    ADK APIs (LlmAgent, BaseAgent, SequentialAgent, LoopAgent, ParallelAgent,
    Runner, BaseSessionService, InMemorySessionService, Session, BaseLlm,
    LiteLlm, FunctionTool, App) and google-genai types (Content, Part,
    GenerateContentConfig) have identical import paths in 1.20.0 and later.
    CI enforces compatibility via a version matrix in tests.yml.

Note:
    This layer ONLY contains adapters - they import from ports/ and domain/
    but never the reverse. This maintains hexagonal architecture boundaries.
"""

# Components
from gepa_adk.adapters.components.component_handlers import (
    ComponentHandlerRegistry,
    GenerateContentConfigHandler,
    InstructionHandler,
    OutputSchemaHandler,
    component_handlers,
    get_handler,
    register_handler,
)
from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.evolution.multi_agent import MultiAgentAdapter

# Execution
from gepa_adk.adapters.execution.agent_executor import (
    AgentExecutor,
    SessionNotFoundError,
)
from gepa_adk.adapters.execution.trial_builder import TrialBuilder

# Media
from gepa_adk.adapters.media.video_blob_service import (
    MAX_VIDEO_SIZE_BYTES,
    VideoBlobService,
)

# Scoring
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

# Selection
from gepa_adk.adapters.selection.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
    create_candidate_selector,
)
from gepa_adk.adapters.selection.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.adapters.selection.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)

# Stoppers (unchanged — already a sub-package)
from gepa_adk.adapters.stoppers import TimeoutStopper

# Workflow
from gepa_adk.adapters.workflow.workflow import (
    WorkflowAgentType,
    clone_workflow_with_overrides,
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
    "STRUCTURED_OUTPUT_CRITIC_INSTRUCTION",
    "ACCURACY_CRITIC_INSTRUCTION",
    "RELEVANCE_CRITIC_INSTRUCTION",
    "normalize_feedback",
    "create_critic",
    "critic_presets",
    # Multi-agent
    "MultiAgentAdapter",
    "is_workflow_agent",
    "find_llm_agents",
    "clone_workflow_with_overrides",
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
