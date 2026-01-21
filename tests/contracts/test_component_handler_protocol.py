"""Contract tests for ComponentHandler protocol compliance.

This module verifies that all ComponentHandler implementations satisfy
the protocol contract, ensuring consistent behavior across handlers.

Contract Requirements:
    - Protocol must be runtime-checkable (isinstance works)
    - serialize() must return str, never raise for missing components
    - apply() then restore() must leave agent unchanged (idempotent)
    - apply() must not raise on invalid values (log and skip instead)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

    from gepa_adk.ports.component_handler import ComponentHandler


class TestComponentHandlerProtocolCompliance:
    """Contract tests for ComponentHandler protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify protocol can be used with isinstance().

        This is required per FR-011: The protocol MUST be runtime-checkable.
        """
        from gepa_adk.ports.component_handler import ComponentHandler

        # Create a mock implementation
        class MockHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = MockHandler()
        assert isinstance(handler, ComponentHandler)

    def test_non_compliant_class_fails_isinstance(self) -> None:
        """Verify classes missing methods don't pass isinstance check."""
        from gepa_adk.ports.component_handler import ComponentHandler

        class IncompleteHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            # Missing apply and restore

        handler = IncompleteHandler()
        assert not isinstance(handler, ComponentHandler)

    def test_protocol_has_required_methods(self) -> None:
        """Verify protocol defines all required methods."""
        from gepa_adk.ports.component_handler import ComponentHandler

        # Protocol should have these method signatures
        assert hasattr(ComponentHandler, "serialize")
        assert hasattr(ComponentHandler, "apply")
        assert hasattr(ComponentHandler, "restore")


@pytest.mark.contract
class TestInstructionHandlerProtocolCompliance:
    """Contract tests for InstructionHandler.

    Tests are marked as expected to fail until implementation exists.
    """

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create InstructionHandler instance."""
        from gepa_adk.adapters.component_handlers import InstructionHandler

        return InstructionHandler()

    @pytest.fixture
    def agent(self) -> "LlmAgent":
        """Create test agent with instruction."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Original instruction",
        )

    def test_isinstance_protocol(self, handler: "ComponentHandler") -> None:
        """InstructionHandler must pass isinstance(ComponentHandler)."""
        from gepa_adk.ports.component_handler import ComponentHandler

        assert isinstance(handler, ComponentHandler)

    def test_serialize_returns_string(
        self, handler: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """serialize() must return str."""
        result = handler.serialize(agent)
        assert isinstance(result, str)
        assert result == "Original instruction"

    def test_apply_restore_idempotent(
        self, handler: "ComponentHandler", agent: "LlmAgent"
    ) -> None:
        """apply() then restore() must leave agent unchanged."""
        original_value = handler.serialize(agent)

        # Apply new value
        returned_original = handler.apply(agent, "New instruction")

        # Verify agent was modified
        assert handler.serialize(agent) == "New instruction"

        # Restore original
        handler.restore(agent, returned_original)

        # Verify agent is back to original state
        assert handler.serialize(agent) == original_value


@pytest.mark.contract
class TestOutputSchemaHandlerProtocolCompliance:
    """Contract tests for OutputSchemaHandler.

    Tests are marked as expected to fail until implementation exists.
    """

    @pytest.fixture
    def handler(self) -> "ComponentHandler":
        """Create OutputSchemaHandler instance."""
        from gepa_adk.adapters.component_handlers import OutputSchemaHandler

        return OutputSchemaHandler()

    @pytest.fixture
    def agent_with_schema(self) -> "LlmAgent":
        """Create test agent with output schema."""
        from google.adk.agents import LlmAgent
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            result: str
            value: int

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
            output_schema=TestSchema,
        )

    @pytest.fixture
    def agent_without_schema(self) -> "LlmAgent":
        """Create test agent without output schema."""
        from google.adk.agents import LlmAgent

        return LlmAgent(
            name="test_agent",
            model="gemini-2.0-flash",
            instruction="Test",
        )

    def test_isinstance_protocol(self, handler: "ComponentHandler") -> None:
        """OutputSchemaHandler must pass isinstance(ComponentHandler)."""
        from gepa_adk.ports.component_handler import ComponentHandler

        assert isinstance(handler, ComponentHandler)

    def test_serialize_returns_string(
        self, handler: "ComponentHandler", agent_with_schema: "LlmAgent"
    ) -> None:
        """serialize() must return str."""
        result = handler.serialize(agent_with_schema)
        assert isinstance(result, str)
        assert "TestSchema" in result or "class" in result

    def test_serialize_empty_for_no_schema(
        self, handler: "ComponentHandler", agent_without_schema: "LlmAgent"
    ) -> None:
        """serialize() must return empty string if no schema."""
        result = handler.serialize(agent_without_schema)
        assert isinstance(result, str)
        assert result == ""

    def test_apply_restore_idempotent(
        self, handler: "ComponentHandler", agent_with_schema: "LlmAgent"
    ) -> None:
        """apply() then restore() must leave agent unchanged."""
        original_schema = agent_with_schema.output_schema

        # Apply new value (valid schema text)
        new_schema_text = '''
class NewSchema(BaseModel):
    output: str
'''
        returned_original = handler.apply(agent_with_schema, new_schema_text)

        # Verify agent was modified
        assert agent_with_schema.output_schema is not None
        assert agent_with_schema.output_schema.__name__ == "NewSchema"

        # Restore original
        handler.restore(agent_with_schema, returned_original)

        # Verify agent is back to original state
        assert agent_with_schema.output_schema is original_schema
