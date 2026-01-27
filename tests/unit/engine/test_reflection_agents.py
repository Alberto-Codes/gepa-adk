"""Unit tests for component-aware reflection agent factories.

Tests the factory functions and registry that create reflection agents
with appropriate tools and instructions based on component type.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from gepa_adk.engine.reflection_agents import (
    CONFIG_REFLECTION_INSTRUCTION,
    MODEL_REFLECTION_INSTRUCTION,
    SCHEMA_REFLECTION_INSTRUCTION,
    ComponentReflectionRegistry,
    create_config_reflection_agent,
    create_model_reflection_agent,
    create_schema_reflection_agent,
    create_text_reflection_agent,
    get_reflection_agent,
)
from gepa_adk.utils.schema_tools import validate_output_schema


class TestCreateSchemaReflectionAgent:
    """Tests for create_schema_reflection_agent factory (US1 - T005)."""

    def test_creates_llm_agent(self):
        """Factory returns a configured LlmAgent."""
        agent = create_schema_reflection_agent(model="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.5-flash"
        assert agent.name == "schema_reflector"

    def test_has_validation_tool(self):
        """Agent has validate_output_schema tool."""
        agent = create_schema_reflection_agent(model="gemini-2.5-flash")

        assert agent.tools is not None
        assert len(agent.tools) == 1
        tool = agent.tools[0]
        assert isinstance(tool, FunctionTool)
        assert tool.func == validate_output_schema

    def test_has_schema_instruction(self):
        """Agent uses schema-focused reflection instruction."""
        agent = create_schema_reflection_agent(model="gemini-2.5-flash")

        assert agent.instruction == SCHEMA_REFLECTION_INSTRUCTION

    def test_has_output_key(self):
        """Agent has output_key configured for session state extraction."""
        agent = create_schema_reflection_agent(model="gemini-2.5-flash")

        assert agent.output_key == "proposed_component_text"


class TestCreateConfigReflectionAgent:
    """Tests for create_config_reflection_agent factory (T023)."""

    def test_creates_llm_agent(self):
        """Factory returns a configured LlmAgent."""
        agent = create_config_reflection_agent(model="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.5-flash"
        assert agent.name == "config_reflector"

    def test_has_no_tools(self):
        """Config reflection agent has no validation tools (validation in handler)."""
        agent = create_config_reflection_agent(model="gemini-2.5-flash")

        assert agent.tools is None or len(agent.tools) == 0

    def test_has_config_instruction(self):
        """Agent uses config-focused reflection instruction."""
        agent = create_config_reflection_agent(model="gemini-2.5-flash")

        assert agent.instruction == CONFIG_REFLECTION_INSTRUCTION

    def test_has_output_key(self):
        """Agent has output_key configured for session state extraction."""
        agent = create_config_reflection_agent(model="gemini-2.5-flash")

        assert agent.output_key == "proposed_component_text"


class TestConfigReflectionInstruction:
    """Tests for CONFIG_REFLECTION_INSTRUCTION constant (T023)."""

    def test_contains_template_placeholders(self):
        """Instruction has placeholders for ADK template substitution."""
        assert "{component_text}" in CONFIG_REFLECTION_INSTRUCTION
        assert "{trials}" in CONFIG_REFLECTION_INSTRUCTION

    def test_contains_parameter_guidelines(self):
        """Instruction includes parameter range guidelines."""
        instruction_lower = CONFIG_REFLECTION_INSTRUCTION.lower()
        assert "temperature" in instruction_lower
        assert "top_p" in instruction_lower
        assert "top_k" in instruction_lower
        assert "max_output_tokens" in instruction_lower

    def test_instructs_return_format(self):
        """Instruction specifies YAML return format."""
        instruction_lower = CONFIG_REFLECTION_INSTRUCTION.lower()
        assert "yaml" in instruction_lower


class TestCreateTextReflectionAgent:
    """Tests for create_text_reflection_agent factory (US1 - T006)."""

    def test_creates_llm_agent(self):
        """Factory returns a configured LlmAgent."""
        agent = create_text_reflection_agent(model="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.5-flash"
        assert agent.name == "text_reflector"

    def test_has_no_tools(self):
        """Text reflection agent has no validation tools."""
        agent = create_text_reflection_agent(model="gemini-2.5-flash")

        assert agent.tools is None or len(agent.tools) == 0

    def test_has_text_instruction(self):
        """Agent uses general text reflection instruction."""
        agent = create_text_reflection_agent(model="gemini-2.5-flash")

        # Should NOT be the schema instruction
        assert agent.instruction != SCHEMA_REFLECTION_INSTRUCTION
        # Should contain template placeholders
        assert isinstance(agent.instruction, str)
        assert "{component_text}" in agent.instruction
        assert "{trials}" in agent.instruction

    def test_has_output_key(self):
        """Agent has output_key configured."""
        agent = create_text_reflection_agent(model="gemini-2.5-flash")

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

        agent = registry.get_agent("output_schema", "gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.5-flash"


class TestGetReflectionAgent:
    """Tests for get_reflection_agent convenience function (US2 - T013)."""

    def test_returns_schema_agent_for_output_schema(self):
        """Function returns schema reflection agent for 'output_schema'."""
        agent = get_reflection_agent("output_schema", "gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_returns_text_agent_for_instruction(self):
        """Function returns text reflection agent for 'instruction'."""
        agent = get_reflection_agent("instruction", "gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.tools is None or len(agent.tools) == 0

    def test_returns_config_agent_for_generate_content_config(self):
        """Function returns config reflection agent for 'generate_content_config'."""
        agent = get_reflection_agent("generate_content_config", "gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.name == "config_reflector"
        # Config agent has no tools (validation in handler)
        assert agent.tools is None or len(agent.tools) == 0
        # Uses config instruction
        assert agent.instruction == CONFIG_REFLECTION_INSTRUCTION

    def test_returns_text_agent_for_unknown(self):
        """Function returns text agent for unknown components (fallback)."""
        agent = get_reflection_agent("unknown_component", "gemini-2.5-flash")

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
        assert isinstance(agent.instruction, str)
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


# =============================================================================
# Model Reflection Agent Tests (T019)
# =============================================================================


class TestCreateModelReflectionAgent:
    """Tests for create_model_reflection_agent factory (T019)."""

    def test_creates_llm_agent(self):
        """Factory returns a configured LlmAgent."""
        agent = create_model_reflection_agent(model="gemini-2.5-flash")

        assert isinstance(agent, LlmAgent)
        assert agent.model == "gemini-2.5-flash"
        assert agent.name == "model_reflector"

    def test_has_no_tools_without_allowed_models(self):
        """Agent has no tools when no allowed_models specified."""
        agent = create_model_reflection_agent(model="gemini-2.5-flash")

        assert agent.tools is None or len(agent.tools) == 0

    def test_has_validation_tool_with_allowed_models(self):
        """Agent has validation tool when allowed_models specified."""
        agent = create_model_reflection_agent(
            model="gemini-2.5-flash",
            allowed_models=("model-a", "model-b"),
        )

        assert agent.tools is not None
        assert len(agent.tools) == 1
        tool = agent.tools[0]
        assert isinstance(tool, FunctionTool)

    def test_default_model(self):
        """Factory uses default model when not specified."""
        agent = create_model_reflection_agent()

        assert agent.model == "ollama_chat/qwen3:8b"

    def test_has_output_key(self):
        """Agent has output_key configured for session state extraction."""
        agent = create_model_reflection_agent(model="gemini-2.5-flash")

        assert agent.output_key == "proposed_component_text"

    def test_no_output_schema(self):
        """Agent uses output_key, not output_schema (like other reflectors)."""
        agent = create_model_reflection_agent(model="gemini-2.5-flash")

        # Model reflector follows same pattern as schema/config reflectors
        assert agent.output_schema is None

    def test_instruction_contains_allowed_models(self):
        """Instruction includes allowed models when provided."""
        agent = create_model_reflection_agent(
            model="gemini-2.5-flash",
            allowed_models=("model-a", "model-b", "model-c"),
        )

        assert "model-a" in agent.instruction
        assert "model-b" in agent.instruction
        assert "model-c" in agent.instruction

    def test_instruction_shows_any_when_no_allowed_models(self):
        """Instruction shows (any) when no allowed_models provided."""
        agent = create_model_reflection_agent(
            model="gemini-2.5-flash",
            allowed_models=(),
        )

        assert "(any)" in agent.instruction

    def test_uses_partial_with_allowed_models(self):
        """Can use functools.partial to create factory with baked-in models."""
        from functools import partial

        factory = partial(
            create_model_reflection_agent,
            allowed_models=("gpt-4o", "claude-3-sonnet"),
        )

        # Factory signature now matches ReflectionAgentFactory(model: str) -> LlmAgent
        agent = factory("gemini-2.5-flash")

        assert agent.name == "model_reflector"
        assert "gpt-4o" in agent.instruction
        assert "claude-3-sonnet" in agent.instruction


class TestModelReflectionInstruction:
    """Tests for MODEL_REFLECTION_INSTRUCTION constant."""

    def test_contains_template_placeholders(self):
        """Instruction has ADK template placeholders."""
        assert "{component_text}" in MODEL_REFLECTION_INSTRUCTION
        assert "{trials}" in MODEL_REFLECTION_INSTRUCTION

    def test_contains_allowed_models_placeholder(self):
        """Instruction has allowed_models placeholder."""
        assert "{allowed_models}" in MODEL_REFLECTION_INSTRUCTION

    def test_instructs_return_format(self):
        """Instruction specifies plain text output format (like other reflectors)."""
        assert "Return ONLY" in MODEL_REFLECTION_INSTRUCTION
        assert "model name" in MODEL_REFLECTION_INSTRUCTION.lower()
