"""Acceptance tests for issue 395: ``reflection_model`` accepts a ``BaseLlm``.

A ``LiteLlm`` (or any ``BaseLlm``) instance on
``EvolutionConfig.reflection_model`` passes through ``_resolve_model_for_agent``
unchanged, so a custom ``api_base`` or temperature needs no hand-built
reflection agent. The string path and the default are unchanged.

Notes:
    The wiring tests patch ``gepa_adk.api.create_adk_reflection_fn`` and read
    the reflection agent's ``model`` from its first positional argument; the
    engine and adapters are patched so no LLM is built or called.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from gepa_adk import evolve, evolve_group
from gepa_adk.api import _resolve_model_for_agent
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionConfig, EvolutionResult
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


@pytest.fixture
def custom_llm() -> LiteLlm:
    """A LiteLlm pointed at a private server.

    Returns:
        A LiteLlm with an api_base and temperature set.
    """
    return LiteLlm(
        model="ollama_chat/qwen3:27b", api_base="http://h:1", temperature=0.2
    )


def _result() -> EvolutionResult:
    return EvolutionResult(
        original_score=0.5,
        final_score=0.5,
        evolved_components={"instruction": "Answer."},
        iteration_history=[],
        total_iterations=0,
    )


class TestResolveModelForAgent:
    """A BaseLlm passes through; strings resolve as before."""

    def test_base_llm_instance_is_returned_unchanged(self, custom_llm: LiteLlm) -> None:
        """The very same object comes back, so its api_base survives."""
        assert _resolve_model_for_agent(custom_llm) is custom_llm

    def test_string_path_is_unchanged(self) -> None:
        """Gemini strings stay strings; other strings are wrapped in LiteLlm."""
        assert _resolve_model_for_agent("gemini-3.8-flash") == "gemini-3.8-flash"
        wrapped = _resolve_model_for_agent("ollama_chat/gpt-oss:20b")
        assert isinstance(wrapped, LiteLlm)
        assert wrapped.model == "ollama_chat/gpt-oss:20b"

    def test_other_types_are_rejected(self) -> None:
        """Neither str nor BaseLlm is a configuration error naming the field."""
        with pytest.raises(ConfigurationError, match="reflection_model"):
            _resolve_model_for_agent(42)  # type: ignore[arg-type]


class TestEvolutionConfigAcceptsBaseLlm:
    """The config keeps rejecting empty values and accepts an instance."""

    def test_instance_is_stored_as_is(self, custom_llm: LiteLlm) -> None:
        """The config holds the instance the caller gave it."""
        assert (
            EvolutionConfig(reflection_model=custom_llm).reflection_model is custom_llm
        )

    def test_default_is_unchanged(self) -> None:
        """The default model string is the documented local model."""
        assert EvolutionConfig().reflection_model == "ollama_chat/gpt-oss:20b"

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_values_still_raise(self, value: Any) -> None:
        """An empty string and None are still rejected."""
        with pytest.raises(ConfigurationError, match="reflection_model"):
            EvolutionConfig(reflection_model=value)


class TestEvolveBuildsDefaultReflectorWithTheInstance:
    """Both entry points hand the instance to the default reflection agent."""

    @pytest.mark.asyncio
    async def test_evolve_uses_the_instance(self, custom_llm: LiteLlm) -> None:
        """The default reflection agent's model is the caller's LiteLlm."""
        agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="Answer.")
        engine = MagicMock()
        engine.run = AsyncMock(return_value=_result())
        reflection_fn = MagicMock()

        with (
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.ADKAdapter", return_value=MagicMock()),
            patch(
                "gepa_adk.api.create_adk_reflection_fn", return_value=reflection_fn
            ) as factory,
        ):
            await evolve(
                agent,
                [{"input": "q"}],
                config=EvolutionConfig(reflection_model=custom_llm),
                scorer=MockScorer(),
            )

        factory.assert_called_once()
        reflection_agent = factory.call_args.args[0]
        assert isinstance(reflection_agent, LlmAgent)
        assert reflection_agent.model is custom_llm

    @pytest.mark.asyncio
    async def test_evolve_group_uses_the_instance(self, custom_llm: LiteLlm) -> None:
        """The multi-agent entry point does the same."""
        generator = LlmAgent(
            name="generator", model="gemini-3.8-flash", instruction="Write."
        )
        critic = LlmAgent(name="critic", model="gemini-3.8-flash", instruction="Judge.")
        engine = MagicMock()
        engine.run = AsyncMock(return_value=_result())

        with (
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.MultiAgentAdapter", return_value=MagicMock()),
            patch(
                "gepa_adk.api.create_adk_reflection_fn", return_value=MagicMock()
            ) as factory,
        ):
            await evolve_group(
                agents={"generator": generator, "critic": critic},
                primary="generator",
                trainset=[{"input": "q"}],
                config=EvolutionConfig(reflection_model=custom_llm),
                scorer=MockScorer(),
            )

        factory.assert_called_once()
        assert factory.call_args.args[0].model is custom_llm

    @pytest.mark.asyncio
    async def test_explicit_reflection_agent_still_wins(
        self, custom_llm: LiteLlm
    ) -> None:
        """A caller-built reflection_agent is used verbatim, config model ignored."""
        agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="Answer.")
        mine = LlmAgent(
            name="mine",
            model="gemini-3.8-flash",
            instruction="Improve {component_text} {trials}",
        )
        engine = MagicMock()
        engine.run = AsyncMock(return_value=_result())

        with (
            patch("gepa_adk.api.AsyncGEPAEngine", return_value=engine),
            patch("gepa_adk.api.ADKAdapter", return_value=MagicMock()),
            patch(
                "gepa_adk.api.create_adk_reflection_fn", return_value=MagicMock()
            ) as factory,
        ):
            await evolve(
                agent,
                [{"input": "q"}],
                config=EvolutionConfig(reflection_model=custom_llm),
                scorer=MockScorer(),
                reflection_agent=mine,
            )

        assert factory.call_args.args[0] is mine
