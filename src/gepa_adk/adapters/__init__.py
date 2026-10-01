"""Adapter layer convenience re-exports.

All public symbols are re-exported from their sub-package locations so that
``from gepa_adk.adapters import <symbol>`` continues to work. New code should
import from sub-packages directly. Note that the old flat-module paths
(e.g. ``gepa_adk.adapters.agent_executor``) have been reorganized into
sub-packages and are no longer available.

Sub-packages:
    execution/: Agent execution infrastructure (AgentExecutor, TrialBuilder).
    scoring/: Scoring infrastructure (CriticScorer, LabelAgreementScorer,
        RequireToolScorer, schemas, create_critic factory).
    evolution/: Core adapter implementations (ADKAdapter, MultiAgentAdapter).
    selection/: Selection strategies (candidates, components, evaluation).
    components/: Evolvable surface handlers (ComponentHandlerRegistry).
    workflow/: Workflow agent utilities (is_workflow_agent, find_llm_agents).
    media/: Multimodal adapters (VideoBlobService).
    stoppers/: Evolution stopping conditions (RegressionStopper, TimeoutStopper).

Attributes:
    ADKAdapter (class): AsyncGEPAAdapter implementation for Google ADK agents.
    TrialBuilder (class): Shared utility for building trial records in reflection datasets.
    MappingComponentHandler (class): Handler for one key of a caller-owned mapping.
    register_mapping_components (function): Register a handler for every key of a
        caller-owned mapping.
    RequireToolScorer (class): Scorer wrapper that scores 0.0 unless a named tool ran.
    AgentExecutor (class): Unified agent execution adapter.
    SessionNotFoundError (class): Raised when a requested session does not exist.
    ParetoCandidateSelector (class): Sample from the Pareto front proportional to
        leadership frequency.
    CurrentBestCandidateSelector (class): Always select the candidate with the highest
        average score.
    EpsilonGreedyCandidateSelector (class): Epsilon-greedy selection balancing
        exploration and exploitation.
    create_candidate_selector (function): Create a candidate selector by name.
    ComponentHandlerRegistry (class): Registry for component handlers with O(1) lookup.
    GenerateContentConfigHandler (class): Handler for agent.generate_content_config
        component.
    InstructionHandler (class): Handler for agent.instruction component.
    OutputSchemaHandler (class): Handler for agent.output_schema component.
    component_handlers (ComponentHandlerRegistry): Default component handler registry.
    get_handler (function): Get handler from default registry.
    register_handler (function): Register handler in default registry.
    RoundRobinComponentSelector (class): Selects components in a round-robin fashion.
    AllComponentSelector (class): Selects all available components for simultaneous
        update.
    create_component_selector (function): Create a component selector strategy from a
        string alias.
    CriticScorer (class): Adapter that wraps ADK critic agents to provide structured
        scoring.
    LabelAgreementScorer (class): Scorer that measures exact agreement between output
        and label.
    SimpleCriticOutput (class): KISS schema for basic critic feedback.
    CriticOutput (class): Advanced schema for structured critic feedback with
        dimensions.
    SIMPLE_CRITIC_INSTRUCTION (str): Generic instruction for simple critics.
    ADVANCED_CRITIC_INSTRUCTION (str): Generic instruction for advanced critics.
    STRUCTURED_OUTPUT_CRITIC_INSTRUCTION (str): Preset instruction for structure
        evaluation.
    ACCURACY_CRITIC_INSTRUCTION (str): Preset instruction for factual accuracy
        evaluation.
    RELEVANCE_CRITIC_INSTRUCTION (str): Preset instruction for relevance evaluation.
    normalize_feedback (function): Normalize critic feedback to consistent trial format.
    create_critic (function): Create a pre-configured critic agent by preset name.
    critic_presets (dict): Maps preset name to human-readable description.
    MultiAgentAdapter (class): Adapter for multi-agent pipeline evaluation with
        per-agent component routing.
    is_workflow_agent (function): Check if an agent is a workflow type.
    find_llm_agents (function): Find all LlmAgents in a workflow (recursive traversal
        with depth limiting).
    clone_workflow_with_overrides (function): Clone workflow with instruction overrides
        applied to LlmAgent leaves.
    WorkflowAgentType (type): Type alias for workflow agent types.
    FullEvaluationPolicy (class): Evaluation policy that scores all validation examples
        every iteration.
    SubsetEvaluationPolicy (class): Evaluation policy that scores a configurable subset
        with round-robin coverage.
    RegressionStopper (class): Stops evolution when best score declines over a lookback
        window.
    TimeoutStopper (class): Stop evolution after a specified timeout.
    VideoBlobService (class): Video blob loading service for multimodal content.
    MAX_VIDEO_SIZE_BYTES (int): Maximum allowed video file size (2GB).

Examples:
    Basic usage with Google ADK agent:

    ```python
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from gepa_adk.adapters import ADKAdapter

    agent = LlmAgent(name="helper", model=LiteLlm(model="ollama_chat/gpt-oss:20b"))
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

Notes:
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
from gepa_adk.adapters.components.mapping_handler import (
    MappingComponentHandler,
    register_mapping_components,
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
from gepa_adk.adapters.scoring.label_agreement import LabelAgreementScorer
from gepa_adk.adapters.scoring.require_tool import RequireToolScorer

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

# Stoppers (updated — RegressionStopper added)
from gepa_adk.adapters.stoppers import RegressionStopper, TimeoutStopper

# Workflow
from gepa_adk.adapters.workflow.workflow import (
    WorkflowAgentType,
    clone_workflow_with_overrides,
    find_llm_agents,
    is_workflow_agent,
)

__all__ = [  # noqa: RUF022  # grouped by layer under section comments
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
    "MappingComponentHandler",
    "register_mapping_components",
    # Component selectors
    "RoundRobinComponentSelector",
    "AllComponentSelector",
    "create_component_selector",
    # Critic schemas and helpers
    "CriticScorer",
    "LabelAgreementScorer",
    "RequireToolScorer",
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
    "RegressionStopper",
    "TimeoutStopper",
    # Trial building
    "TrialBuilder",
    # Video blob service
    "VideoBlobService",
    "MAX_VIDEO_SIZE_BYTES",
]
