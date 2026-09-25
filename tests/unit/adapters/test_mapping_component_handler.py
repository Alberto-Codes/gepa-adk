"""Acceptance tests for evolving a caller-owned mapping of named prompt strings.

``MappingComponentHandler`` evolves one key of a mapping the caller owns,
such as the prompt strings a tool sends to an external service. Registering
a mapping makes each key a component name, so ``evolve()`` can be asked to
evolve those names alongside, or instead of, the agent's own attributes.

Notes:
    The executor is a stub that calls the tool's function directly, so no
    agent or LLM runs. The adapter, handlers, engine and reflection wiring
    are real. An autouse fixture restores the default handler registry
    after each test, so the names registered here do not leak.

Examples:
    Run the acceptance tests:

    ```bash
    uv run pytest tests/unit/adapters/test_mapping_component_handler.py -q
    ```

See Also:
    - [`mapping_handler`][gepa_adk.adapters.components.mapping_handler]:
      The handler and registration function under test.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from gepa_adk import EvolutionConfig, LabelAgreementScorer, evolve
from gepa_adk.adapters.components import (
    ComponentHandlerRegistry,
    component_handlers,
)
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus
from gepa_adk.ports.component_handler import ComponentHandler

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _restore_default_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Restore the default handler registry after each test.

    Args:
        monkeypatch: Pytest fixture that undoes the attribute swap afterwards.
    """
    snapshot = dict(component_handlers._handlers)
    monkeypatch.setattr(component_handlers, "_handlers", snapshot)


class ToolFlowExecutor:
    """Executor stub that answers through the tool and scripts the reflection.

    Attributes:
        tool (FunctionTool): The tool whose function answers the target agent.
        proposal (str): Text the reflection agent returns for every call.
        outputs (list[str]): Every target-agent output, in call order.
    """

    def __init__(self, tool: FunctionTool, proposal: str) -> None:
        """Store the tool and the scripted proposal.

        Args:
            tool: The tool whose function answers the target agent.
            proposal: Text the reflection agent returns for every call.
        """
        self.tool = tool
        self.proposal = proposal
        self.outputs: list[str] = []

    async def execute_agent(
        self, agent: Any, input_text: str, **kwargs: Any
    ) -> ExecutionResult:
        """Answer through the tool for the target agent, else return the proposal.

        Args:
            agent: The agent being run; its name selects the behaviour.
            input_text: The row input or reflection prompt.
            **kwargs: Ignored.

        Returns:
            A successful ExecutionResult carrying the answer.
        """
        if agent.name == "reflector":
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                session_id="stub",
                extracted_value=self.proposal,
            )
        answer = self.tool.func(input_text)
        self.outputs.append(answer)
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS, session_id="stub", extracted_value=answer
        )


def _mapping_and_tool() -> tuple[dict[str, str], FunctionTool]:
    """Build a two-key mapping and a tool that answers from one key.

    Returns:
        The caller-owned mapping and a FunctionTool reading its ``greeting``.
    """
    prompts = {"greeting": "hello", "farewell": "bye"}

    def answer(question: str) -> str:
        """Answer a question with the current greeting prompt.

        Args:
            question: Ignored.

        Returns:
            The current ``greeting`` text.
        """
        return prompts["greeting"]

    return prompts, FunctionTool(answer)


class TestMappingComponentHandler:
    """The handler serialises, applies and restores one mapping key."""

    def test_satisfies_component_handler_protocol(self) -> None:
        """The handler passes the runtime protocol check."""
        from gepa_adk.adapters.components import MappingComponentHandler

        handler = MappingComponentHandler({"k": "v"}, key="k")
        assert isinstance(handler, ComponentHandler)

    def test_round_trip_mutates_the_callers_mapping(self) -> None:
        """apply() writes the caller's dict and restore() puts it back."""
        from gepa_adk.adapters.components import MappingComponentHandler

        prompts = {"greeting": "hello", "farewell": "bye"}
        handler = MappingComponentHandler(prompts, key="greeting")
        agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="i")

        assert handler.serialize(agent) == "hello"
        original = handler.apply(agent, "hallå")
        assert original == "hello"
        assert prompts == {"greeting": "hallå", "farewell": "bye"}
        handler.restore(agent, original)
        assert prompts == {"greeting": "hello", "farewell": "bye"}

    def test_agent_argument_is_ignored(self) -> None:
        """A component the caller owns needs no agent."""
        from gepa_adk.adapters.components import MappingComponentHandler

        prompts = {"greeting": "hello"}
        handler = MappingComponentHandler(prompts, key="greeting")
        assert handler.serialize(None) == "hello"
        assert handler.apply(None, "hi") == "hello"
        handler.restore(None, "hello")
        assert prompts["greeting"] == "hello"

    def test_rejects_missing_key(self) -> None:
        """A key absent from the mapping is a ValueError naming the key."""
        from gepa_adk.adapters.components import MappingComponentHandler

        with pytest.raises(ValueError, match="farewell"):
            MappingComponentHandler({"greeting": "hello"}, key="farewell")

    def test_rejects_non_string_value(self) -> None:
        """A mapping value that is not text cannot be evolved."""
        from gepa_adk.adapters.components import MappingComponentHandler

        with pytest.raises(TypeError, match="greeting"):
            MappingComponentHandler({"greeting": 3}, key="greeting")  # type: ignore[dict-item]


class TestRegisterMappingComponents:
    """Registering a mapping makes each key a component name."""

    def test_registers_one_handler_per_key_in_order(self) -> None:
        """Every key gets a handler and the names come back in mapping order."""
        from gepa_adk.adapters.components import (
            MappingComponentHandler,
            register_mapping_components,
        )

        registry = ComponentHandlerRegistry()
        prompts = {"greeting": "hello", "farewell": "bye"}

        names = register_mapping_components(prompts, registry=registry)

        assert names == ["greeting", "farewell"]
        assert len(names) == 2
        for name in names:
            handler = registry.get(name)
            assert isinstance(handler, MappingComponentHandler)
            assert handler.serialize(None) == prompts[name]

    def test_registers_in_default_registry_by_default(self) -> None:
        """Without a registry argument the default registry is used."""
        from gepa_adk.adapters.components import (
            MappingComponentHandler,
            component_handlers,
            register_mapping_components,
        )

        names = register_mapping_components({"zz_default_probe": "x"})

        assert names == ["zz_default_probe"]
        assert isinstance(
            component_handlers.get("zz_default_probe"), MappingComponentHandler
        )

    @pytest.mark.parametrize("key", ["bad key", "1st", "", "ünïcode-x"])
    def test_rejects_non_identifier_key(self, key: str) -> None:
        """A key that is not a Python identifier cannot be a component name."""
        from gepa_adk.adapters.components import register_mapping_components

        with pytest.raises(ValueError, match="identifier"):
            register_mapping_components(
                {"greeting": "hello", key: "x"}, registry=ComponentHandlerRegistry()
            )

    @pytest.mark.parametrize("key", ["instruction", "output_schema"])
    def test_rejects_built_in_component_names(self, key: str) -> None:
        """A key that shadows a built-in component name is refused."""
        from gepa_adk.adapters.components import register_mapping_components

        with pytest.raises(ValueError, match=key):
            register_mapping_components({key: "x"}, registry=ComponentHandlerRegistry())

    def test_rejects_empty_mapping(self) -> None:
        """An empty mapping has nothing to evolve."""
        from gepa_adk.adapters.components import register_mapping_components

        with pytest.raises(ValueError, match="empty"):
            register_mapping_components({}, registry=ComponentHandlerRegistry())


class TestEvolveMappingHeldByTool:
    """evolve() evolves mapping keys and applies them to the tool between runs."""

    @pytest.mark.asyncio
    async def test_evolves_the_key_the_tool_reads(self) -> None:
        """A scripted reflection changes one key and the tool sees it."""
        from gepa_adk.adapters.components import register_mapping_components

        prompts, tool = _mapping_and_tool()
        names = register_mapping_components(prompts)
        agent = LlmAgent(
            name="forwarder",
            model="gemini-3.8-flash",
            instruction="Forward the question to the tool.",
            tools=[tool],
        )
        reflector = LlmAgent(
            name="reflector",
            model="gemini-3.8-flash",
            instruction="{component_text}\n{trials}",
        )
        executor = ToolFlowExecutor(tool, proposal="hola")
        trainset = [
            {"input": "greet me", "expected": "hola"},
            {"input": "greet me again", "expected": "hola"},
        ]

        result = await evolve(
            agent,
            trainset,
            scorer=LabelAgreementScorer(),
            components=names,
            component_selector="round_robin",
            reflection_agent=reflector,
            executor=executor,
            config=EvolutionConfig(
                max_iterations=2, patience=5, acceptance_metric="mean"
            ),
        )

        assert result.original_score == 0.0
        assert result.final_score == 1.0
        assert result.evolved_components["greeting"] == "hola"
        assert result.original_components == {"greeting": "hello", "farewell": "bye"}
        # The evolved text was applied to the tool between evaluations.
        assert "hola" in executor.outputs
        # Evaluation restores the caller's mapping afterwards.
        assert prompts == {"greeting": "hello", "farewell": "bye"}

    @pytest.mark.asyncio
    async def test_unregistered_component_name_is_a_configuration_error(self) -> None:
        """A name with no handler fails before evolution starts, listing the registered names."""
        agent = LlmAgent(name="a", model="gemini-3.8-flash", instruction="i")

        with pytest.raises(
            ConfigurationError,
            match="no_such_component.*Registered components:.*generate_content_config",
        ):
            await evolve(
                agent,
                [{"input": "x", "expected": "y"}],
                scorer=LabelAgreementScorer(),
                components=["no_such_component"],
                executor=ToolFlowExecutor(_mapping_and_tool()[1], proposal="p"),
            )

    @pytest.mark.asyncio
    async def test_registered_generate_content_config_is_accepted(self) -> None:
        """A built-in registry handler other than the two api constants works."""
        from google.genai.types import GenerateContentConfig

        agent = LlmAgent(
            name="a",
            model="gemini-3.8-flash",
            instruction="i",
            generate_content_config=GenerateContentConfig(temperature=0.3),
        )
        reflector = LlmAgent(
            name="reflector",
            model="gemini-3.8-flash",
            instruction="{component_text}\n{trials}",
        )
        _, tool = _mapping_and_tool()

        result = await evolve(
            agent,
            [{"input": "x", "expected": "hello"}],
            scorer=LabelAgreementScorer(),
            components=["generate_content_config"],
            reflection_agent=reflector,
            executor=ToolFlowExecutor(tool, proposal='{"temperature": 0.7}'),
            config=EvolutionConfig(max_iterations=1),
        )

        assert "generate_content_config" in result.evolved_components
