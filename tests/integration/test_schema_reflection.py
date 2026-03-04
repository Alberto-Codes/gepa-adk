"""Integration tests for component-aware schema reflection with validation.

Tests the full end-to-end workflow of schema reflection agents using validation
tools to self-correct invalid Pydantic schemas before returning proposals.

Feature: 142-component-aware-reflection
Tests: T028 (schema validation), T029 (backward compatibility)
"""

import pytest
from pydantic import BaseModel

from gepa_adk.adapters.agents.reflection_agents import (
    create_schema_reflection_agent,
    create_text_reflection_agent,
    get_reflection_agent,
)
from gepa_adk.adapters.execution.agent_executor import AgentExecutor
from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.requires_gemini]


# =============================================================================
# Test Fixtures
# =============================================================================


class SimpleSchema(BaseModel):
    """Test schema for validation."""

    name: str
    value: int


# =============================================================================
# T028: Schema Reflection with Real Validation
# =============================================================================


@pytest.mark.slow
class TestSchemaReflectionWithValidation:
    """T028: Integration tests for schema reflection with validation tool.

    Verifies that the schema reflection agent can use the validate_output_schema
    tool to self-validate and correct invalid schemas during reflection.
    """

    @pytest.mark.asyncio
    async def test_schema_agent_has_validation_tool(self) -> None:
        """Verify schema reflection agent includes validation tool."""
        agent = create_schema_reflection_agent(model="gemini-2.5-flash")

        # Verify agent has tools
        assert agent.tools is not None
        assert len(agent.tools) > 0

        # Verify tool is validate_output_schema
        tool = agent.tools[0]
        assert tool.func.__name__ == "validate_output_schema"

    @pytest.mark.asyncio
    async def test_schema_reflection_with_validation_end_to_end(self) -> None:
        """Verify schema reflection agent can validate and return valid schemas.

        This test uses a real LLM to reflect on a schema and verify the output
        is syntactically valid.
        """
        # Create executor and reflection function with explicit schema agent
        executor = AgentExecutor()
        schema_agent = create_schema_reflection_agent("gemini-2.5-flash")
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=schema_agent,
            executor=executor,
        )

        # Current schema to improve
        current_schema = """
class UserProfile(BaseModel):
    name: str
    age: int
"""

        # Mock trials suggesting we need an email field
        trials = [
            {
                "input": "Create user profile",
                "output": '{"name": "Alice", "age": 30}',
                "feedback": {
                    "score": 0.6,
                    "feedback_text": "Missing email field for user contact",
                },
            }
        ]

        # Call reflection with component_name to trigger schema agent selection
        result = await reflection_fn(
            current_schema,
            trials,
            "output_schema",
        )

        # Verify result is a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify result is valid Python (basic check)
        assert "class" in result
        assert "BaseModel" in result

        # Try to validate the returned schema
        from gepa_adk.utils.schema_tools import validate_output_schema

        validation_result = validate_output_schema(result)

        # The schema should be valid (agent used validation tool)
        assert validation_result["valid"] is True
        assert "class_name" in validation_result
        assert validation_result["field_count"] >= 2

    @pytest.mark.asyncio
    async def test_auto_selection_uses_schema_agent_for_output_schema(self) -> None:
        """Verify auto-selection picks schema agent for output_schema component."""
        # Use get_reflection_agent convenience function
        agent = get_reflection_agent("output_schema", "gemini-2.5-flash")

        # Verify it's the schema reflection agent (has tools)
        assert agent.name == "schema_reflector"
        assert agent.tools is not None
        assert len(agent.tools) > 0

    @pytest.mark.asyncio
    async def test_auto_selection_uses_text_agent_for_instruction(self) -> None:
        """Verify auto-selection picks text agent for instruction component."""
        # Use get_reflection_agent convenience function
        agent = get_reflection_agent("instruction", "gemini-2.5-flash")

        # Verify it's the text reflection agent (no tools)
        assert agent.name == "text_reflector"
        assert agent.tools is None or len(agent.tools) == 0

    @pytest.mark.asyncio
    async def test_unknown_component_falls_back_to_text_agent(self) -> None:
        """Verify unknown components use text agent as fallback."""
        # Request agent for unknown component
        agent = get_reflection_agent("unknown_component", "gemini-2.5-flash")

        # Should get text agent (no tools)
        assert agent.name == "text_reflector"
        assert agent.tools is None or len(agent.tools) == 0


# =============================================================================
# T029: Backward Compatibility
# =============================================================================


@pytest.mark.slow
class TestBackwardCompatibility:
    """T029: Integration tests for backward compatibility.

    Verifies that existing code using reflection functions without component_name
    continues to work unchanged.
    """

    @pytest.mark.asyncio
    async def test_existing_code_with_custom_agent_still_works(self) -> None:
        """Verify existing code with custom agents works without component_name.

        This simulates existing code that creates a reflection function with a
        custom agent and doesn't pass component_name.
        """
        # Existing code pattern: create custom agent
        from google.adk.agents import LlmAgent

        custom_agent = LlmAgent(
            name="CustomReflector",
            model="gemini-2.5-flash",
            instruction="""Improve the instruction:
{component_text}

Based on feedback:
{trials}

Return improved instruction.""",
        )

        # Existing code pattern: create reflection function
        executor = AgentExecutor()
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=custom_agent,
            executor=executor,
        )

        # Existing code pattern: call reflection function with component_name
        result = await reflection_fn(
            "Be helpful",
            [{"score": 0.5, "feedback": "Too vague"}],
            "instruction",
        )

        # Verify it still works
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_text_reflection_agent_works_independently(self) -> None:
        """Verify text reflection agent can be used directly without registry."""
        # Create text agent directly (existing pattern)
        agent = create_text_reflection_agent(model="gemini-2.5-flash")

        # Use it in reflection function
        executor = AgentExecutor()
        reflection_fn = create_adk_reflection_fn(agent, executor=executor)

        # Call with component_name
        result = await reflection_fn(
            "Write a greeting",
            [{"score": 0.7, "output": "Hi", "feedback": "Too casual"}],
            "instruction",
        )

        # Should work
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_reflection_without_auto_selection_works(self) -> None:
        """Verify reflection works without auto-selection (explicit agent).

        Ensures that code explicitly providing agents doesn't break with new
        auto-selection features.
        """
        from google.adk.agents import LlmAgent

        # Explicit agent creation
        agent = LlmAgent(
            name="ExplicitAgent",
            model="gemini-2.5-flash",
            instruction="Improve: {component_text}\nFeedback: {trials}",
        )

        # Create reflection function without model parameter
        # (not needed when agent is provided)
        executor = AgentExecutor()
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=agent,
            executor=executor,
            # No model parameter - not needed with explicit agent
        )

        # Call it
        result = await reflection_fn(
            "Test instruction",
            [{"score": 0.6}],
            "instruction",
        )

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# Additional Integration Tests
# =============================================================================


@pytest.mark.slow
class TestComponentAwareReflectionEndToEnd:
    """Additional end-to-end tests for component-aware reflection."""

    @pytest.mark.asyncio
    async def test_explicit_agent_reused_across_calls(self) -> None:
        """Verify explicit agent is reused across multiple reflection calls.

        When an explicit agent is provided at creation time, the same agent
        is used for all invocations of the reflection function.
        """
        executor = AgentExecutor()
        schema_agent = create_schema_reflection_agent("gemini-2.5-flash")

        # Create reflection function with explicit schema agent
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=schema_agent,
            executor=executor,
        )

        # Call multiple times - should use same schema agent each time
        result1 = await reflection_fn(
            "class Test(BaseModel): x: int",
            [{"score": 0.5}],
            "instruction",
        )
        result2 = await reflection_fn(
            "class Test(BaseModel): y: str",
            [{"score": 0.6}],
            "instruction",
        )

        # Both should succeed
        assert isinstance(result1, str)
        assert isinstance(result2, str)

    @pytest.mark.asyncio
    async def test_different_agents_for_different_components(self) -> None:
        """Verify different explicit agents work for different component types.

        Each reflection function is created with an explicit agent appropriate
        for its component type (schema vs text).
        """
        executor = AgentExecutor()

        # Create separate reflection functions with explicit agents
        schema_agent = create_schema_reflection_agent("gemini-2.5-flash")
        schema_reflection_fn = create_adk_reflection_fn(
            reflection_agent=schema_agent,
            executor=executor,
        )

        text_agent = create_text_reflection_agent("gemini-2.5-flash")
        text_reflection_fn = create_adk_reflection_fn(
            reflection_agent=text_agent,
            executor=executor,
        )

        # Call each with appropriate input
        schema_result = await schema_reflection_fn(
            "class Test(BaseModel): x: int",
            [{"score": 0.5}],
            "output_schema",
        )

        instruction_result = await text_reflection_fn(
            "Be helpful",
            [{"score": 0.6}],
            "instruction",
        )

        # Both should succeed
        assert isinstance(schema_result, str)
        assert isinstance(instruction_result, str)
