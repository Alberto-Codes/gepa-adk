"""Unit tests for ADK reflection function factory and component-aware selection.

Tests for feature 142-component-aware-reflection:
- T014: Updated ReflectionFn signature with component_name parameter
- Auto-selection of appropriate reflection agent based on component name

Contract reference: specs/142-component-aware-reflection/contracts/
"""

import pytest
from pytest_mock import MockerFixture

from gepa_adk.engine.adk_reflection import create_adk_reflection_fn
from gepa_adk.ports.agent_executor import ExecutionStatus


def _create_mock_executor(
    mocker: MockerFixture, extracted_value: str = "proposed text"
):
    """Create a mock executor for testing."""
    mock_executor = mocker.MagicMock()
    result_mock = mocker.MagicMock()
    result_mock.status = ExecutionStatus.SUCCESS
    result_mock.extracted_value = extracted_value
    result_mock.session_id = "test_session"
    mock_executor.execute_agent = mocker.AsyncMock(return_value=result_mock)
    return mock_executor


pytestmark = pytest.mark.unit


class TestComponentNameParameter:
    """T014: Unit tests for component_name parameter in reflection function.

    Verify that create_adk_reflection_fn accepts a component_name parameter
    and uses it to auto-select the appropriate reflection agent.
    """

    @pytest.mark.asyncio
    async def test_accepts_component_name_parameter(
        self, mocker: MockerFixture
    ) -> None:
        """Verify create_adk_reflection_fn accepts component_name parameter."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor(mocker)

        # Should accept component_name parameter without error
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
            component_name="output_schema",
        )

        # Verify reflection function is callable
        assert callable(reflection_fn)
        result = await reflection_fn("Be helpful", [])
        assert result == "proposed text"

    @pytest.mark.asyncio
    async def test_component_name_defaults_to_none(self, mocker: MockerFixture) -> None:
        """Verify component_name is optional (defaults to None for backward compat)."""
        mock_agent = mocker.MagicMock()
        mock_agent.name = "TestReflector"
        mock_agent.output_key = None

        mock_executor = _create_mock_executor(mocker)

        # Should work without component_name (backward compatibility)
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=mock_agent,
            executor=mock_executor,
        )

        result = await reflection_fn("Be helpful", [])
        assert result == "proposed text"

    @pytest.mark.asyncio
    async def test_none_agent_with_component_name_uses_auto_selection(
        self, mocker: MockerFixture
    ) -> None:
        """Verify None agent with component_name triggers auto-selection at creation."""
        mock_executor = _create_mock_executor(
            mocker, "class MySchema(BaseModel):\n    pass"
        )

        # Mock the get_reflection_agent function where it's imported
        mock_get_reflection_agent = mocker.patch(
            "gepa_adk.engine.reflection_agents.get_reflection_agent"
        )
        mock_auto_agent = mocker.MagicMock()
        mock_auto_agent.name = "schema_reflector"
        mock_auto_agent.output_key = "proposed_component_text"
        mock_get_reflection_agent.return_value = mock_auto_agent

        # Pass None agent with component_name to trigger creation-time auto-selection
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=None,
            executor=mock_executor,
            component_name="output_schema",
            model="gemini-2.5-flash",
        )

        # Verify get_reflection_agent was called at creation time
        mock_get_reflection_agent.assert_called_once_with(
            "output_schema", "gemini-2.5-flash"
        )

        # Verify reflection function works
        result = await reflection_fn("class OldSchema(BaseModel): pass", [])
        assert result == "class MySchema(BaseModel):\n    pass"

    @pytest.mark.asyncio
    async def test_runtime_auto_selection_with_component_name(
        self, mocker: MockerFixture
    ) -> None:
        """Verify runtime auto-selection when component_name passed at call time."""
        mock_executor = _create_mock_executor(
            mocker, "class MySchema(BaseModel):\n    pass"
        )

        # Mock the get_reflection_agent function for runtime selection
        mock_get_reflection_agent = mocker.patch(
            "gepa_adk.engine.reflection_agents.get_reflection_agent"
        )
        mock_auto_agent = mocker.MagicMock()
        mock_auto_agent.name = "schema_reflector"
        mock_auto_agent.output_key = "proposed_component_text"
        mock_get_reflection_agent.return_value = mock_auto_agent

        # Create reflection function WITHOUT component_name for runtime selection
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=None,
            executor=mock_executor,
            model="gemini-2.5-flash",
            # No component_name at creation - will auto-select at runtime
        )

        # Call with component_name to trigger runtime auto-selection
        result = await reflection_fn(
            "class OldSchema(BaseModel): pass",
            [],
            "output_schema",  # type: ignore[arg-type]
        )

        # Verify get_reflection_agent was called at runtime
        mock_get_reflection_agent.assert_called_once_with(
            "output_schema", "gemini-2.5-flash"
        )
        assert result == "class MySchema(BaseModel):\n    pass"

    @pytest.mark.asyncio
    async def test_custom_agent_overrides_auto_selection(
        self, mocker: MockerFixture
    ) -> None:
        """Verify provided agent is used even when component_name is specified."""
        custom_agent = mocker.MagicMock()
        custom_agent.name = "CustomReflector"
        custom_agent.output_key = "proposed_component_text"

        mock_executor = _create_mock_executor(mocker, "custom output")

        # Mock get_reflection_agent - it should NOT be called
        mock_get_reflection_agent = mocker.patch(
            "gepa_adk.engine.reflection_agents.get_reflection_agent"
        )

        # Pass custom agent with component_name - custom agent should be used
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=custom_agent,
            executor=mock_executor,
            component_name="output_schema",
            model="gemini-2.5-flash",
        )

        # Verify get_reflection_agent was NOT called (custom agent overrides)
        mock_get_reflection_agent.assert_not_called()

        # Verify custom agent is used
        result = await reflection_fn("test", [])
        assert result == "custom output"


class TestAutoSelectionWithModel:
    """Tests for auto-selection requiring model parameter."""

    @pytest.mark.asyncio
    async def test_requires_model_when_agent_is_none(
        self, mocker: MockerFixture
    ) -> None:
        """Verify model parameter is required when agent is None."""
        mock_executor = _create_mock_executor(mocker)

        with pytest.raises(ValueError, match="model.*required.*auto-select"):
            create_adk_reflection_fn(
                reflection_agent=None,
                executor=mock_executor,
                component_name="output_schema",
                # model not provided - should raise
            )

    @pytest.mark.asyncio
    async def test_model_optional_when_agent_provided(
        self, mocker: MockerFixture
    ) -> None:
        """Verify model parameter is optional when agent is provided."""
        custom_agent = mocker.MagicMock()
        custom_agent.name = "CustomReflector"
        custom_agent.output_key = "proposed_component_text"

        mock_executor = _create_mock_executor(mocker)

        # Should work without model when agent is provided
        reflection_fn = create_adk_reflection_fn(
            reflection_agent=custom_agent,
            executor=mock_executor,
            component_name="output_schema",
            # model not provided - should work because agent is provided
        )

        result = await reflection_fn("test", [])
        assert result == "proposed text"
