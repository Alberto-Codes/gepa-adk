"""Acceptance tests for the ``registry=`` keyword on the public entry points.

Two rounds in one process each register a mapping under the same component
name into their own ``ComponentHandlerRegistry`` and pass it to the entry
point, so neither round's handler replaces the other's and each round
writes into its own mapping. Without the keyword the default registry is
consulted as before (GitHub issue 451).

Notes:
    The executor stub answers the target agent from the mapping the round
    owns and scripts the reflection, so the value the tool saw during
    evaluation is observable without an LLM.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from google.adk.agents import LlmAgent, SequentialAgent

from gepa_adk import (
    EvolutionConfig,
    LabelAgreementScorer,
    evolve,
    evolve_group,
    evolve_workflow,
)
from gepa_adk.adapters.components import (
    ComponentHandlerRegistry,
    component_handlers,
    register_mapping_components,
)
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _restore_default_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore the default handler registry after each test.

    Args:
        monkeypatch: Pytest fixture that undoes the attribute swap afterwards.
    """
    snapshot = dict(component_handlers._handlers)
    monkeypatch.setattr(component_handlers, "_handlers", snapshot)


class MappingExecutor:
    """Executor stub that answers from one mapping and scripts the reflection.

    Attributes:
        mapping (dict[str, str]): The mapping whose ``greeting`` answers the
            target agent.
        proposal (str): Text the reflection agent returns for every call.
        outputs (list[str]): Every target-agent output, in call order.
    """

    def __init__(self, mapping: dict[str, str], proposal: str) -> None:
        """Store the mapping and the scripted proposal.

        Args:
            mapping: The mapping the target agent reads.
            proposal: Text the reflection agent returns for every call.
        """
        self.mapping = mapping
        self.proposal = proposal
        self.outputs: list[str] = []

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Answer from the mapping for the target agent, else return the proposal.

        Args:
            agent: The agent being run; a reflection call carries
                ``component_text`` in its session state.
            input_text: The row input or reflection prompt.
            **kwargs: The executor keyword arguments.

        Returns:
            A successful ExecutionResult carrying the answer.
        """
        state = kwargs.get("session_state") or {}
        if "component_text" in state:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                session_id="stub",
                extracted_value=self.proposal,
            )
        answer = self.mapping["greeting"]
        self.outputs.append(answer)
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS, session_id="stub", extracted_value=answer
        )


def _agent(name: str = "forwarder") -> LlmAgent:
    """Build the target agent.

    Args:
        name: The agent name.

    Returns:
        An LlmAgent whose answers the executor stub provides.
    """
    return LlmAgent(
        name=name,
        model="ollama_chat/gpt-oss:20b",
        instruction="Forward the question to the tool.",
    )


def _reflector() -> LlmAgent:
    """Build the reflection agent.

    Returns:
        An LlmAgent the executor stub answers with the scripted proposal.
    """
    return LlmAgent(
        name="reflector",
        model="ollama_chat/gpt-oss:20b",
        instruction="{component_text}\n{trials}",
    )


def _trainset(expected: str) -> list[dict[str, str]]:
    """Build two rows that expect the proposed greeting.

    Args:
        expected: The label both rows expect.

    Returns:
        Two labelled rows.
    """
    return [
        {"input": "greet me", "expected": expected},
        {"input": "greet me again", "expected": expected},
    ]


def _config() -> EvolutionConfig:
    """Return a two-iteration config with mean acceptance.

    Returns:
        The evolution config.
    """
    return EvolutionConfig(max_iterations=2, patience=5, acceptance_metric="mean")


class TestEvolveWithOwnRegistry:
    """Two rounds in one process each evolve their own mapping."""

    @pytest.mark.asyncio
    async def test_each_round_writes_into_its_own_mapping(self) -> None:
        """Same component name, two registries, two mappings, no cross-talk."""
        first = {"greeting": "hello"}
        second = {"greeting": "hi"}
        first_registry = ComponentHandlerRegistry()
        second_registry = ComponentHandlerRegistry()
        first_names = register_mapping_components(first, registry=first_registry)
        second_names = register_mapping_components(second, registry=second_registry)
        first_executor = MappingExecutor(first, proposal="hola")
        second_executor = MappingExecutor(second, proposal="salut")

        first_result = await evolve(
            _agent(),
            _trainset("hola"),
            scorer=LabelAgreementScorer(),
            components=first_names,
            reflection_agent=_reflector(),
            executor=first_executor,
            config=_config(),
            registry=first_registry,
        )

        assert first_result.original_components == {"greeting": "hello"}
        assert first_result.evolved_components["greeting"] == "hola"
        assert first_result.final_score == 1.0
        assert "hola" in first_executor.outputs
        assert first == {"greeting": "hello"}
        assert second == {"greeting": "hi"}
        assert second_executor.outputs == []

        second_result = await evolve(
            _agent(),
            _trainset("salut"),
            scorer=LabelAgreementScorer(),
            components=second_names,
            reflection_agent=_reflector(),
            executor=second_executor,
            config=_config(),
            registry=second_registry,
        )

        assert second_result.original_components == {"greeting": "hi"}
        assert second_result.evolved_components["greeting"] == "salut"
        assert "salut" in second_executor.outputs
        assert "salut" not in first_executor.outputs
        assert first == {"greeting": "hello"}
        assert second == {"greeting": "hi"}
        assert not component_handlers.has("greeting")

    @pytest.mark.asyncio
    async def test_default_registry_is_used_when_omitted(self) -> None:
        """Without ``registry=`` the default registry resolves the name."""
        prompts = {"greeting": "hello"}
        names = register_mapping_components(prompts)
        executor = MappingExecutor(prompts, proposal="hola")

        result = await evolve(
            _agent(),
            _trainset("hola"),
            scorer=LabelAgreementScorer(),
            components=names,
            reflection_agent=_reflector(),
            executor=executor,
            config=_config(),
        )

        assert component_handlers.has("greeting")
        assert result.evolved_components["greeting"] == "hola"
        assert "hola" in executor.outputs
        assert prompts == {"greeting": "hello"}

    @pytest.mark.asyncio
    async def test_name_missing_from_the_given_registry_is_a_configuration_error(
        self,
    ) -> None:
        """A name registered only in the default registry is not found."""
        from gepa_adk.domain.exceptions import ConfigurationError

        prompts = {"greeting": "hello"}
        names = register_mapping_components(prompts)
        empty = ComponentHandlerRegistry()

        with pytest.raises(ConfigurationError, match="greeting"):
            await evolve(
                _agent(),
                _trainset("hola"),
                scorer=LabelAgreementScorer(),
                components=names,
                reflection_agent=_reflector(),
                executor=MappingExecutor(prompts, proposal="hola"),
                config=_config(),
                registry=empty,
            )


class TestGroupAndWorkflowWithOwnRegistry:
    """The group and workflow entry points take the same keyword."""

    @pytest.mark.asyncio
    async def test_evolve_group_uses_the_given_registry(self) -> None:
        """A mapping component on one agent resolves through the registry."""
        prompts = {"greeting": "hello"}
        registry = ComponentHandlerRegistry()
        names = register_mapping_components(prompts, registry=registry)
        executor = MappingExecutor(prompts, proposal="hola")
        agent = _agent()

        with patch("gepa_adk.api.AgentExecutor", return_value=executor):
            result = await evolve_group(
                {"forwarder": agent},
                "forwarder",
                _trainset("hola"),
                components={"forwarder": names},
                scorer=LabelAgreementScorer(),
                reflection_agent=_reflector(),
                config=_config(),
                registry=registry,
            )

        assert result.evolved_components["forwarder.greeting"] == "hola"
        assert "hola" in executor.outputs
        assert prompts == {"greeting": "hello"}
        assert not component_handlers.has("greeting")

    @pytest.mark.asyncio
    async def test_evolve_workflow_uses_the_given_registry(self) -> None:
        """The workflow entry point forwards the registry to the group path."""
        prompts = {"greeting": "hello"}
        registry = ComponentHandlerRegistry()
        names = register_mapping_components(prompts, registry=registry)
        executor = MappingExecutor(prompts, proposal="hola")
        agent = _agent()
        workflow = SequentialAgent(name="pipeline", sub_agents=[agent])

        with patch("gepa_adk.api.AgentExecutor", return_value=executor):
            result = await evolve_workflow(
                workflow,
                _trainset("hola"),
                scorer=LabelAgreementScorer(),
                primary="forwarder",
                components={"forwarder": names},
                config=_config(),
                registry=registry,
            )

        assert result.evolved_components["forwarder.greeting"] == "hola"
        assert "hola" in executor.outputs
        assert prompts == {"greeting": "hello"}
        assert not component_handlers.has("greeting")
