"""Verify backward-compatible re-exports from adapters/__init__.py.

Each old import path (``gepa_adk.adapters.X``) must resolve to the exact
same object as the new sub-package path (``gepa_adk.adapters.subpkg.mod.X``).

Attributes:
    REEXPORT_CASES: Parametrized list of (symbol_name, sub_package_path) tuples.
"""

import importlib

import pytest

from gepa_adk import adapters

pytestmark = pytest.mark.unit

# (attribute_name_on_adapters, fully_qualified_module, attribute_name_in_module)
REEXPORT_CASES: list[tuple[str, str, str]] = [
    # Evolution
    ("ADKAdapter", "gepa_adk.adapters.evolution.adk_adapter", "ADKAdapter"),
    (
        "MultiAgentAdapter",
        "gepa_adk.adapters.evolution.multi_agent",
        "MultiAgentAdapter",
    ),
    # Execution
    ("AgentExecutor", "gepa_adk.adapters.execution.agent_executor", "AgentExecutor"),
    (
        "SessionNotFoundError",
        "gepa_adk.adapters.execution.agent_executor",
        "SessionNotFoundError",
    ),
    ("TrialBuilder", "gepa_adk.adapters.execution.trial_builder", "TrialBuilder"),
    # Scoring
    ("CriticScorer", "gepa_adk.adapters.scoring.critic_scorer", "CriticScorer"),
    (
        "SimpleCriticOutput",
        "gepa_adk.adapters.scoring.critic_scorer",
        "SimpleCriticOutput",
    ),
    ("CriticOutput", "gepa_adk.adapters.scoring.critic_scorer", "CriticOutput"),
    (
        "SIMPLE_CRITIC_INSTRUCTION",
        "gepa_adk.adapters.scoring.critic_scorer",
        "SIMPLE_CRITIC_INSTRUCTION",
    ),
    (
        "ADVANCED_CRITIC_INSTRUCTION",
        "gepa_adk.adapters.scoring.critic_scorer",
        "ADVANCED_CRITIC_INSTRUCTION",
    ),
    (
        "STRUCTURED_OUTPUT_CRITIC_INSTRUCTION",
        "gepa_adk.adapters.scoring.critic_scorer",
        "STRUCTURED_OUTPUT_CRITIC_INSTRUCTION",
    ),
    (
        "ACCURACY_CRITIC_INSTRUCTION",
        "gepa_adk.adapters.scoring.critic_scorer",
        "ACCURACY_CRITIC_INSTRUCTION",
    ),
    (
        "RELEVANCE_CRITIC_INSTRUCTION",
        "gepa_adk.adapters.scoring.critic_scorer",
        "RELEVANCE_CRITIC_INSTRUCTION",
    ),
    (
        "normalize_feedback",
        "gepa_adk.adapters.scoring.critic_scorer",
        "normalize_feedback",
    ),
    (
        "create_critic",
        "gepa_adk.adapters.scoring.critic_scorer",
        "create_critic",
    ),
    (
        "critic_presets",
        "gepa_adk.adapters.scoring.critic_scorer",
        "critic_presets",
    ),
    # Selection — candidate
    (
        "ParetoCandidateSelector",
        "gepa_adk.adapters.selection.candidate_selector",
        "ParetoCandidateSelector",
    ),
    (
        "CurrentBestCandidateSelector",
        "gepa_adk.adapters.selection.candidate_selector",
        "CurrentBestCandidateSelector",
    ),
    (
        "EpsilonGreedyCandidateSelector",
        "gepa_adk.adapters.selection.candidate_selector",
        "EpsilonGreedyCandidateSelector",
    ),
    (
        "create_candidate_selector",
        "gepa_adk.adapters.selection.candidate_selector",
        "create_candidate_selector",
    ),
    # Selection — component
    (
        "RoundRobinComponentSelector",
        "gepa_adk.adapters.selection.component_selector",
        "RoundRobinComponentSelector",
    ),
    (
        "AllComponentSelector",
        "gepa_adk.adapters.selection.component_selector",
        "AllComponentSelector",
    ),
    (
        "create_component_selector",
        "gepa_adk.adapters.selection.component_selector",
        "create_component_selector",
    ),
    # Selection — evaluation policy
    (
        "FullEvaluationPolicy",
        "gepa_adk.adapters.selection.evaluation_policy",
        "FullEvaluationPolicy",
    ),
    (
        "SubsetEvaluationPolicy",
        "gepa_adk.adapters.selection.evaluation_policy",
        "SubsetEvaluationPolicy",
    ),
    # Components
    (
        "ComponentHandlerRegistry",
        "gepa_adk.adapters.components.component_handlers",
        "ComponentHandlerRegistry",
    ),
    (
        "InstructionHandler",
        "gepa_adk.adapters.components.component_handlers",
        "InstructionHandler",
    ),
    (
        "OutputSchemaHandler",
        "gepa_adk.adapters.components.component_handlers",
        "OutputSchemaHandler",
    ),
    (
        "GenerateContentConfigHandler",
        "gepa_adk.adapters.components.component_handlers",
        "GenerateContentConfigHandler",
    ),
    (
        "component_handlers",
        "gepa_adk.adapters.components.component_handlers",
        "component_handlers",
    ),
    ("get_handler", "gepa_adk.adapters.components.component_handlers", "get_handler"),
    (
        "register_handler",
        "gepa_adk.adapters.components.component_handlers",
        "register_handler",
    ),
    # Workflow
    ("is_workflow_agent", "gepa_adk.adapters.workflow.workflow", "is_workflow_agent"),
    ("find_llm_agents", "gepa_adk.adapters.workflow.workflow", "find_llm_agents"),
    (
        "clone_workflow_with_overrides",
        "gepa_adk.adapters.workflow.workflow",
        "clone_workflow_with_overrides",
    ),
    ("WorkflowAgentType", "gepa_adk.adapters.workflow.workflow", "WorkflowAgentType"),
    # Stoppers (unchanged)
    ("RegressionStopper", "gepa_adk.adapters.stoppers", "RegressionStopper"),
    ("TimeoutStopper", "gepa_adk.adapters.stoppers", "TimeoutStopper"),
    # Media
    (
        "VideoBlobService",
        "gepa_adk.adapters.media.video_blob_service",
        "VideoBlobService",
    ),
    (
        "MAX_VIDEO_SIZE_BYTES",
        "gepa_adk.adapters.media.video_blob_service",
        "MAX_VIDEO_SIZE_BYTES",
    ),
]


class TestAdapterReExports:
    """Each old import path resolves to the same object as the new sub-package path."""

    @pytest.mark.parametrize(
        ("symbol", "module_path", "attr"),
        REEXPORT_CASES,
        ids=[c[0] for c in REEXPORT_CASES],
    )
    def test_reexport_identity(self, symbol: str, module_path: str, attr: str) -> None:
        """Verify adapters.X is subpkg.mod.X for every re-exported symbol."""
        reexported = getattr(adapters, symbol)
        module = importlib.import_module(module_path)
        direct = getattr(module, attr)
        assert reexported is direct, (
            f"adapters.{symbol} is not the same object as {module_path}.{attr}"
        )

    def test_all_list_length(self) -> None:
        """Verify __all__ contains exactly the expected number of symbols."""
        assert len(adapters.__all__) == len(REEXPORT_CASES), (
            f"adapters.__all__ has {len(adapters.__all__)} symbols, "
            f"expected {len(REEXPORT_CASES)}"
        )

    def test_all_list_coverage(self) -> None:
        """Verify every symbol in __all__ has a re-export test case."""
        tested_symbols = {c[0] for c in REEXPORT_CASES}
        all_symbols = set(adapters.__all__)
        missing = all_symbols - tested_symbols
        assert not missing, f"Symbols in __all__ without test cases: {missing}"


__all__ = ["TestAdapterReExports"]
