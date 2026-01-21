"""Integration tests for ComponentHandler full cycle.

This module tests the complete serialize → apply → evaluate → restore
cycle with real LlmAgent instances, verifying end-to-end behavior.
"""

from __future__ import annotations

from typing import Any

import pytest
from google.adk.agents import LlmAgent
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
            model="gemini-2.0-flash",
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
            model="gemini-2.0-flash",
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
            model="gemini-2.0-flash",
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
            get_handler,
            register_handler,
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
            model="gemini-2.0-flash",
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
            model="gemini-2.0-flash",
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
            result = len(agent.instruction)  # dummy operation

        finally:
            # Always restore
            handler.restore(agent, original)

        # Verify restoration happened
        assert agent.instruction == original_instruction
