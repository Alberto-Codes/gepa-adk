"""Unit tests for component-aware reflection agent factories.

Tests the factory functions and registry that create reflection agents
with appropriate tools and instructions based on component type.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from gepa_adk.engine.reflection_agents import (
    SCHEMA_REFLECTION_INSTRUCTION,
    ComponentReflectionRegistry,
    create_schema_reflection_agent,
    create_text_reflection_agent,
    get_reflection_agent,
)
from gepa_adk.utils.schema_tools import validate_output_schema


class TestCreateSchemaReflectionAgent:
    """Tests for create_schema_reflection_agent factory (US1 - T005)."""

    def test_creates_llm_agent(self):
        """Factory returns a configured LlmAgent."""
        agent = create_schema_reflection_agent(model="gemini-2.0-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.0-flash"
        assert agent.name == "schema_reflector"

    def test_has_validation_tool(self):
        """Agent has validate_output_schema tool."""
        agent = create_schema_reflection_agent(model="gemini-2.0-flash")

        assert agent.tools is not None
        assert len(agent.tools) == 1
        tool = agent.tools[0]
        assert isinstance(tool, FunctionTool)
        assert tool.func == validate_output_schema

    def test_has_schema_instruction(self):
        """Agent uses schema-focused reflection instruction."""
        agent = create_schema_reflection_agent(model="gemini-2.0-flash")

        assert agent.instruction == SCHEMA_REFLECTION_INSTRUCTION

    def test_has_output_key(self):
        """Agent has output_key configured for session state extraction."""
        agent = create_schema_reflection_agent(model="gemini-2.0-flash")

        assert agent.output_key == "proposed_component_text"


class TestCreateTextReflectionAgent:
    """Tests for create_text_reflection_agent factory (US1 - T006)."""

    def test_creates_llm_agent(self):
        """Factory returns a configured LlmAgent."""
        agent = create_text_reflection_agent(model="gemini-2.0-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.0-flash"
        assert agent.name == "text_reflector"

    def test_has_no_tools(self):
        """Text reflection agent has no validation tools."""
        agent = create_text_reflection_agent(model="gemini-2.0-flash")

        assert agent.tools is None or len(agent.tools) == 0

    def test_has_text_instruction(self):
        """Agent uses general text reflection instruction."""
        agent = create_text_reflection_agent(model="gemini-2.0-flash")

        # Should NOT be the schema instruction
        assert agent.instruction != SCHEMA_REFLECTION_INSTRUCTION
        # Should contain template placeholders
        assert "{component_text}" in agent.instruction
        assert "{trials}" in agent.instruction

    def test_has_output_key(self):
        """Agent has output_key configured."""
        agent = create_text_reflection_agent(model="gemini-2.0-flash")

        assert agent.output_key == "proposed_component_text"


class TestSchemaReflectionInstruction:
    """Tests for SCHEMA_REFLECTION_INSTRUCTION constant (US1 - T007)."""

    def test_contains_template_placeholders(self):
        """Instruction has placeholders for ADK template substitution."""
        assert "{component_text}" in SCHEMA_REFLECTION_INSTRUCTION
        assert "{trials}" in SCHEMA_REFLECTION_INSTRUCTION

    def test_mentions_validation_tool(self):
        """Instruction guides agent to use validation tool."""
        instruction_lower = SCHEMA_REFLECTION_INSTRUCTION.lower()
        assert "validate" in instruction_lower
        assert (
            "tool" in instruction_lower or "validate_output_schema" in instruction_lower
        )

    def test_instructs_return_format(self):
        """Instruction specifies what to return."""
        instruction_lower = SCHEMA_REFLECTION_INSTRUCTION.lower()
        assert "return" in instruction_lower or "provide" in instruction_lower


class TestComponentReflectionRegistry:
    """Tests for ComponentReflectionRegistry (US2 - T012)."""

    def test_can_register_factory(self):
        """Registry accepts new factory registrations."""
        registry = ComponentReflectionRegistry()

        def mock_factory(model: str) -> LlmAgent:
            return LlmAgent(name="mock", model=model, instruction="test")

        registry.register("test_component", mock_factory)
        factory = registry.get_factory("test_component")

        assert factory == mock_factory

    def test_returns_default_for_unknown_component(self):
        """Registry returns default factory for unregistered components."""
        registry = ComponentReflectionRegistry()
        factory = registry.get_factory("unknown_component")

        # Should return the default factory (text reflection)
        assert factory is not None

    def test_get_agent_creates_agent(self):
        """get_agent convenience method creates agent."""
        registry = ComponentReflectionRegistry()
        registry.register("output_schema", create_schema_reflection_agent)

        agent = registry.get_agent("output_schema", "gemini-2.0-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.0-flash"


class TestGetReflectionAgent:
    """Tests for get_reflection_agent convenience function (US2 - T013)."""

    def test_returns_schema_agent_for_output_schema(self):
        """Function returns schema reflection agent for 'output_schema'."""
        agent = get_reflection_agent("output_schema", "gemini-2.0-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_returns_text_agent_for_instruction(self):
        """Function returns text reflection agent for 'instruction'."""
        agent = get_reflection_agent("instruction", "gemini-2.0-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.tools is None or len(agent.tools) == 0

    def test_returns_text_agent_for_unknown(self):
        """Function returns text agent for unknown components (fallback)."""
        agent = get_reflection_agent("unknown_component", "gemini-2.0-flash")

        assert isinstance(agent, LlmAgent)
        # Should be text agent (no tools)
        assert agent.tools is None or len(agent.tools) == 0


class TestRegistryExtension:
    """Tests for registry extensibility (US4 - T024, T025)."""

    def test_can_add_custom_factory(self):
        """Registry supports adding custom validators for new components."""
        registry = ComponentReflectionRegistry()

        def custom_factory(model: str) -> LlmAgent:
            return LlmAgent(
                name="custom_reflector",
                model=model,
                instruction="Custom: {component_text}",
            )

        registry.register("my_custom_component", custom_factory)
        agent = registry.get_agent("my_custom_component", "test-model")

        assert agent.name == "custom_reflector"
        assert "Custom:" in agent.instruction

    def test_multiple_custom_registrations(self):
        """Registry handles multiple custom component types."""
        registry = ComponentReflectionRegistry()

        registry.register(
            "comp1", lambda m: LlmAgent(name="comp1", model=m, instruction="1")
        )
        registry.register(
            "comp2", lambda m: LlmAgent(name="comp2", model=m, instruction="2")
        )

        agent1 = registry.get_agent("comp1", "model")
        agent2 = registry.get_agent("comp2", "model")

        assert agent1.name == "comp1"
        assert agent2.name == "comp2"
