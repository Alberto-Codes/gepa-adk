"""Integration tests for ComponentHandler full cycle.

This module tests the complete serialize → apply → evaluate → restore
cycle with real LlmAgent instances, verifying end-to-end behavior.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field


@pytest.mark.integration
class TestComponentHandlerIntegration:
    """Integration tests for full component handler cycle."""

    def test_instruction_handler_full_cycle(self) -> None:
        """Test complete serialize/apply/restore cycle for instruction."""
        from gepa_adk.adapters import get_handler

        # Create agent with instruction
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Original system prompt",
        )

        # Get handler
        handler = get_handler("instruction")

        # Serialize original
        original_text = handler.serialize(agent)
        assert original_text == "Original system prompt"

        # Apply new instruction
        original = handler.apply(agent, "Modified instruction for testing")
        assert agent.instruction == "Modified instruction for testing"
        assert original == "Original system prompt"

        # Restore original
        handler.restore(agent, original)
        assert agent.instruction == "Original system prompt"

        # Verify full round-trip
        assert handler.serialize(agent) == original_text

    def test_output_schema_handler_full_cycle(self) -> None:
        """Test complete serialize/apply/restore cycle for output_schema."""
        from gepa_adk.adapters import get_handler

        # Define test schemas
        class OriginalSchema(BaseModel):
            result: str
            confidence: float = Field(ge=0.0, le=1.0)

        # Create agent with schema
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
            output_schema=OriginalSchema,
        )

        # Get handler
        handler = get_handler("output_schema")

        # Serialize original
        original_text = handler.serialize(agent)
        assert "OriginalSchema" in original_text
        assert "result" in original_text

        # Apply new schema
        new_schema_text = """
class ModifiedSchema(BaseModel):
    output: str
    score: int
"""
        original_schema = handler.apply(agent, new_schema_text)
        assert agent.output_schema is not None
        assert agent.output_schema.__name__ == "ModifiedSchema"
        assert original_schema is OriginalSchema

        # Restore original
        handler.restore(agent, original_schema)
        assert agent.output_schema is OriginalSchema

    def test_multiple_handlers_independent(self) -> None:
        """Test that instruction and schema handlers work independently."""
        from gepa_adk.adapters import get_handler

        class TestSchema(BaseModel):
            value: int

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Original instruction",
            output_schema=TestSchema,
        )

        instruction_handler = get_handler("instruction")
        schema_handler = get_handler("output_schema")

        # Apply changes to both
        orig_instruction = instruction_handler.apply(agent, "New instruction")
        orig_schema = schema_handler.apply(
            agent,
            """
class NewSchema(BaseModel):
    result: str
""",
        )

        # Verify both changed
        assert agent.instruction == "New instruction"
        assert agent.output_schema is not None
        assert agent.output_schema.__name__ == "NewSchema"

        # Restore in reverse order
        schema_handler.restore(agent, orig_schema)
        instruction_handler.restore(agent, orig_instruction)

        # Verify both restored
        assert agent.instruction == "Original instruction"
        assert agent.output_schema is TestSchema

    def test_custom_handler_integration(self) -> None:
        """Test registering and using a custom handler."""
        from gepa_adk.adapters import (
            ComponentHandlerRegistry,
        )

        # Create a custom handler for a hypothetical component
        class NameHandler:
            def serialize(self, agent: LlmAgent) -> str:
                return agent.name

            def apply(self, agent: LlmAgent, value: str) -> str:
                original = agent.name
                # Note: LlmAgent.name is typically immutable, so this is
                # illustrative. In real usage, you'd handle mutable components.
                object.__setattr__(agent, "_name", value)
                return original

            def restore(self, agent: LlmAgent, original: str) -> None:
                object.__setattr__(agent, "_name", original)

        # Register in a fresh registry (not polluting default)
        registry = ComponentHandlerRegistry()
        registry.register("name", NameHandler())

        # Verify registration worked
        assert registry.has("name")
        handler = registry.get("name")
        assert isinstance(handler, NameHandler)

    def test_handler_error_recovery(self) -> None:
        """Test that handlers gracefully handle errors."""
        from gepa_adk.adapters import get_handler

        class TestSchema(BaseModel):
            value: int

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
            output_schema=TestSchema,
        )

        handler = get_handler("output_schema")

        # Try to apply invalid schema
        original = handler.apply(agent, "this is not valid python")

        # Should keep original schema (graceful degradation)
        assert agent.output_schema is TestSchema
        # Should return original for restore
        assert original is TestSchema

    def test_default_handlers_preregistered(self) -> None:
        """Test that default handlers are registered on import."""
        from gepa_adk.adapters import component_handlers

        # Both handlers should be registered
        assert component_handlers.has("instruction")
        assert component_handlers.has("output_schema")

        # Should be correct types
        from gepa_adk.adapters import InstructionHandler, OutputSchemaHandler

        assert isinstance(component_handlers.get("instruction"), InstructionHandler)
        assert isinstance(component_handlers.get("output_schema"), OutputSchemaHandler)

    def test_handler_with_try_finally_pattern(self) -> None:
        """Test handlers in try/finally pattern (typical usage)."""
        from gepa_adk.adapters import get_handler

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Original",
        )

        handler = get_handler("instruction")
        original_instruction = agent.instruction

        try:
            # Apply candidate instruction
            original = handler.apply(agent, "Candidate instruction")
            assert agent.instruction == "Candidate instruction"

            # Simulate evaluation that might fail
            # (in real code, this would be the evaluation logic)
            len(agent.instruction)  # dummy operation

        finally:
            # Always restore
            handler.restore(agent, original)

        # Verify restoration happened
        assert agent.instruction == original_instruction

    def test_generate_content_config_handler_full_cycle(self) -> None:
        """Test complete serialize/apply/restore cycle for generate_content_config.

        T014: Create agent with config → serialize → apply modified → restore → verify original
        """
        from gepa_adk.adapters import get_handler

        # Create agent with generate_content_config
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
            generate_content_config=GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1024,
            ),
        )

        # Get handler
        handler = get_handler("generate_content_config")

        # Serialize original
        original_yaml = handler.serialize(agent)
        assert "temperature: 0.7" in original_yaml
        assert "top_p: 0.9" in original_yaml
        assert "max_output_tokens: 1024" in original_yaml

        # Apply new config
        new_config_yaml = """
temperature: 0.3
top_p: 0.5
max_output_tokens: 512
"""
        original_config = handler.apply(agent, new_config_yaml)

        # Verify config changed
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.3
        assert agent.generate_content_config.top_p == 0.5
        assert agent.generate_content_config.max_output_tokens == 512

        # Verify original returned
        assert original_config.temperature == 0.7
        assert original_config.top_p == 0.9
        assert original_config.max_output_tokens == 1024

        # Restore original
        handler.restore(agent, original_config)

        # Verify restoration
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.7
        assert agent.generate_content_config.top_p == 0.9
        assert agent.generate_content_config.max_output_tokens == 1024

    def test_generate_content_config_handler_with_none_config(self) -> None:
        """Test handler behavior when agent has no config."""
        from gepa_adk.adapters import get_handler

        # Create agent without generate_content_config
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
        )

        handler = get_handler("generate_content_config")

        # Serialize should return empty string
        serialized = handler.serialize(agent)
        assert serialized == ""

        # Apply should work, returning None as original
        original = handler.apply(agent, "temperature: 0.5")
        assert original is None
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.5

        # Restore None
        handler.restore(agent, original)
        assert agent.generate_content_config is None

    def test_generate_content_config_handler_invalid_keeps_original(self) -> None:
        """Test that invalid config keeps original (graceful degradation)."""
        from gepa_adk.adapters import get_handler

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
            generate_content_config=GenerateContentConfig(temperature=0.7),
        )

        handler = get_handler("generate_content_config")

        # Apply invalid config (temperature out of range)
        original = handler.apply(agent, "temperature: 999")

        # Should keep original (graceful degradation)
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.7
        assert original.temperature == 0.7

    def test_generate_content_config_handler_partial_merge(self) -> None:
        """Test that partial config merges with existing values."""
        from gepa_adk.adapters import get_handler

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
            generate_content_config=GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
                max_output_tokens=1024,
            ),
        )

        handler = get_handler("generate_content_config")

        # Apply only temperature change
        original = handler.apply(agent, "temperature: 0.3")

        # Temperature changed, others preserved
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.3
        assert agent.generate_content_config.top_p == 0.9
        assert agent.generate_content_config.max_output_tokens == 1024

        # Restore
        handler.restore(agent, original)
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.7

    def test_generate_content_config_registered_on_import(self) -> None:
        """Test that generate_content_config handler is registered on import."""
        from gepa_adk.adapters import (
            GenerateContentConfigHandler,
            component_handlers,
        )
        from gepa_adk.domain import COMPONENT_GENERATE_CONFIG

        assert component_handlers.has(COMPONENT_GENERATE_CONFIG)
        handler = component_handlers.get(COMPONENT_GENERATE_CONFIG)
        assert isinstance(handler, GenerateContentConfigHandler)

    def test_all_handlers_coexist(self) -> None:
        """Test that instruction, output_schema, and config handlers coexist."""
        from gepa_adk.adapters import get_handler

        class TestSchema(BaseModel):
            value: int

        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Original instruction",
            output_schema=TestSchema,
            generate_content_config=GenerateContentConfig(temperature=0.7),
        )

        instruction_handler = get_handler("instruction")
        schema_handler = get_handler("output_schema")
        config_handler = get_handler("generate_content_config")

        # Apply changes to all three
        orig_instruction = instruction_handler.apply(agent, "New instruction")
        orig_schema = schema_handler.apply(
            agent,
            """
class NewSchema(BaseModel):
    result: str
""",
        )
        orig_config = config_handler.apply(agent, "temperature: 0.3")

        # Verify all changed
        assert agent.instruction == "New instruction"
        assert agent.output_schema is not None
        assert agent.output_schema.__name__ == "NewSchema"
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.3

        # Restore all
        config_handler.restore(agent, orig_config)
        schema_handler.restore(agent, orig_schema)
        instruction_handler.restore(agent, orig_instruction)

        # Verify all restored
        assert agent.instruction == "Original instruction"
        assert agent.output_schema is TestSchema
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.7


@pytest.mark.integration
class TestConfigEvolutionIntegration:
    """Integration tests for config evolution in the evolution loop (T024, T025)."""

    def test_config_component_in_candidate(self) -> None:
        """Test that generate_content_config can be included in Candidate.

        T024: Verify config evolution works as a component.
        """
        from gepa_adk.domain import Candidate
        from gepa_adk.domain.types import COMPONENT_GENERATE_CONFIG

        # Create candidate with config component
        candidate = Candidate(
            components={
                "instruction": "Test instruction",
                COMPONENT_GENERATE_CONFIG: "temperature: 0.7\ntop_p: 0.9",
            },
            generation=0,
        )

        assert COMPONENT_GENERATE_CONFIG in candidate.components
        assert "temperature" in candidate.components[COMPONENT_GENERATE_CONFIG]

    def test_config_and_instruction_in_candidate(self) -> None:
        """Test that both instruction and config can coexist in Candidate.

        T025: Verify config + instruction evolution work together.
        """
        from gepa_adk.domain import Candidate
        from gepa_adk.domain.types import (
            COMPONENT_GENERATE_CONFIG,
            COMPONENT_INSTRUCTION,
        )

        # Create candidate with both components
        candidate = Candidate(
            components={
                COMPONENT_INSTRUCTION: "Be helpful and concise.",
                COMPONENT_GENERATE_CONFIG: "temperature: 0.5\nmax_output_tokens: 1024",
            },
            generation=0,
        )

        assert COMPONENT_INSTRUCTION in candidate.components
        assert COMPONENT_GENERATE_CONFIG in candidate.components

    def test_handler_round_trip_preserves_values(self) -> None:
        """Test full serialize → modify → deserialize → apply round trip.

        T024: Verify config parameters change correctly through evolution.
        """
        from gepa_adk.adapters import get_handler
        from gepa_adk.utils.config_utils import (
            deserialize_generate_config,
            serialize_generate_config,
        )

        # Create agent with initial config
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Test",
            generate_content_config=GenerateContentConfig(
                temperature=0.7,
                top_p=0.9,
            ),
        )

        handler = get_handler("generate_content_config")

        # Serialize current config
        yaml_text = handler.serialize(agent)
        assert "temperature: 0.7" in yaml_text

        # Simulate reflection agent modifying config
        # Parse, modify, re-serialize
        parsed_config = deserialize_generate_config(yaml_text)
        modified_config = GenerateContentConfig(
            temperature=0.5,  # Changed
            top_p=parsed_config.top_p,  # Preserved
            max_output_tokens=2048,  # New
        )
        modified_yaml = serialize_generate_config(modified_config)

        # Apply modified config (simulating evolution acceptance)
        original = handler.apply(agent, modified_yaml)

        # Verify changes applied
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.5
        assert agent.generate_content_config.top_p == 0.9
        assert agent.generate_content_config.max_output_tokens == 2048

        # Restore for cleanup
        handler.restore(agent, original)
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.7

    def test_multi_component_handler_coordination(self) -> None:
        """Test handlers work correctly when evolving multiple components.

        T025: Verify both instruction and config can evolve together.
        """
        from gepa_adk.adapters import get_handler

        class TestSchema(BaseModel):
            result: str

        # Create agent with all three component types
        agent = LlmAgent(
            name="test_agent",
            model="gemini-2.5-flash",
            instruction="Original instruction",
            output_schema=TestSchema,
            generate_content_config=GenerateContentConfig(temperature=0.7),
        )

        # Get handlers
        instruction_handler = get_handler("instruction")
        config_handler = get_handler("generate_content_config")

        # Simulate evolution: apply new values to both
        orig_instruction = instruction_handler.apply(
            agent, "Evolved instruction: be concise"
        )
        orig_config = config_handler.apply(agent, "temperature: 0.3")

        # Verify both changed independently
        assert agent.instruction == "Evolved instruction: be concise"
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.3

        # Simulate rejection: restore both
        config_handler.restore(agent, orig_config)
        instruction_handler.restore(agent, orig_instruction)

        # Verify both restored
        assert agent.instruction == "Original instruction"
        assert agent.generate_content_config is not None
        assert agent.generate_content_config.temperature == 0.7

    def test_config_evolution_with_reflection_agent(self) -> None:
        """Test config reflection agent is selected for config evolution.

        T024/T025: Verify config evolution uses specialized reflection.
        """
        from gepa_adk.engine.reflection_agents import get_reflection_agent

        # Get reflection agent for config evolution
        agent = get_reflection_agent("generate_content_config", "gemini-2.5-flash")

        # Should be config reflector, not text reflector
        assert agent.name == "config_reflector"
        # Should have config-focused instruction with parameter guidelines
        assert isinstance(agent.instruction, str)
        assert "temperature" in agent.instruction.lower()
        assert "top_p" in agent.instruction.lower()
