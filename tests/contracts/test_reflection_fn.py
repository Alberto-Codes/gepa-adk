"""Contract tests for ReflectionFn protocol compliance.

Feature: 122-adk-session-state
Task: T006 - Contract test for ReflectionFn signature unchanged

These tests verify that the ReflectionFn signature remains unchanged after
adding session state support. The output_key parameter is added to
create_adk_reflection_fn but does NOT change the ReflectionFn signature.

Contract reference: specs/122-adk-session-state/contracts/reflection-fn.md
"""

import inspect
from collections.abc import Awaitable
from typing import Any

import pytest

from gepa_adk.engine.proposer import ReflectionFn

pytestmark = pytest.mark.contract


class TestReflectionFnSignatureContract:
    """T006: Contract tests verifying ReflectionFn signature.

    The ReflectionFn type alias must be:
    Callable[[str, list[dict[str, Any]], str], Awaitable[tuple[str, str | None]]]

    Three parameters: component_text, trials, component_name.
    """

    def test_reflection_fn_input_parameters(self) -> None:
        """Verify ReflectionFn accepts (str, list[dict[str, Any]], str)."""
        # ReflectionFn is a type alias:
        # Callable[[str, list[dict[str, Any]], str], Awaitable[tuple[str, str | None]]]
        args = getattr(ReflectionFn, "__args__", None)
        assert args is not None, "ReflectionFn must have type arguments"

        # Callable[[A, B, C], R] has args = (A, B, C, R)
        # Parameter types are first N-1 elements, return type is last
        assert len(args) == 4, "ReflectionFn must have 3 params + 1 return type"
        param1 = args[0]
        param2 = args[1]
        param3 = args[2]

        assert param1 is str, "First parameter must be str (component_text)"
        # Second parameter is list[dict[str, Any]]
        assert "list" in str(param2), "Second parameter must be list (trials)"
        assert param3 is str, "Third parameter must be str (component_name)"

    def test_reflection_fn_return_type_is_awaitable_tuple(self) -> None:
        """Verify ReflectionFn returns Awaitable[tuple[str, str | None]]."""
        args = getattr(ReflectionFn, "__args__", None)
        assert args is not None, "ReflectionFn must have type arguments"

        # Return type is the last argument
        return_type = args[-1]

        # Should be Awaitable[tuple[str, str | None]]
        origin = getattr(return_type, "__origin__", None)
        assert origin is Awaitable, f"Return type must be Awaitable, got {origin}"

        # The awaited type should be tuple[str, str | None]
        awaited_args = getattr(return_type, "__args__", None)
        assert awaited_args is not None, "Awaitable must have type argument"
        assert getattr(awaited_args[0], "__origin__", None) is tuple, (
            "Awaitable must wrap tuple"
        )

    def test_mock_reflection_fn_matches_protocol(self) -> None:
        """Verify a mock function matching the expected signature works."""

        async def mock_reflection_fn(
            component_text: str,
            trials: list[dict[str, Any]],
            component_name: str,
        ) -> tuple[str, str | None]:
            """Mock that matches ReflectionFn protocol."""
            return (f"Improved: {component_text}", None)

        # Verify it's async
        assert inspect.iscoroutinefunction(mock_reflection_fn)

        # Verify parameter names
        sig = inspect.signature(mock_reflection_fn)
        params = list(sig.parameters.keys())
        assert params == ["component_text", "trials", "component_name"]

    @pytest.mark.asyncio
    async def test_mock_reflection_fn_execution(self) -> None:
        """Verify mock reflection function can be executed with expected args."""

        async def mock_reflection_fn(
            component_text: str,
            trials: list[dict[str, Any]],
            component_name: str,
        ) -> tuple[str, str | None]:
            """Mock that matches ReflectionFn protocol."""
            return (f"Improved: {component_text}", None)

        # Execute with typical arguments
        result = await mock_reflection_fn(
            "Be helpful and concise",
            [
                {"input": "hi", "output": "hello", "feedback": {"score": 0.8}},
                {"input": "bye", "output": "goodbye", "feedback": {"score": 0.6}},
            ],
            "instruction",
        )

        assert isinstance(result, tuple)
        assert isinstance(result[0], str)
        assert "Improved" in result[0]

    @pytest.mark.asyncio
    async def test_reflection_fn_accepts_empty_trials(self) -> None:
        """Verify ReflectionFn implementation can accept empty trials list."""

        async def mock_reflection_fn(
            component_text: str,
            trials: list[dict[str, Any]],
            component_name: str,
        ) -> tuple[str, str | None]:
            """Mock that handles empty trials."""
            return (component_text, None)  # Return unchanged if no trials

        result = await mock_reflection_fn("Be helpful", [], "instruction")

        assert result == ("Be helpful", None)


class TestCreateAdkReflectionFnContract:
    """Contract tests for create_adk_reflection_fn factory.

    After 122-adk-session-state, the factory accepts an optional output_key
    parameter but the returned function still matches ReflectionFn.
    """

    def test_factory_accepts_output_key_parameter(self) -> None:
        """Verify create_adk_reflection_fn accepts output_key parameter."""
        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        sig = inspect.signature(create_adk_reflection_fn)
        params = list(sig.parameters.keys())

        assert "output_key" in params, "Factory must accept output_key parameter"

    def test_factory_output_key_has_default(self) -> None:
        """Verify output_key has a default value."""
        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        sig = inspect.signature(create_adk_reflection_fn)

        # output_key should have default "proposed_instruction"
        output_key_param = sig.parameters.get("output_key")
        assert output_key_param is not None, "output_key parameter must exist"
        assert output_key_param.default != inspect.Parameter.empty, (
            "output_key must have default value"
        )

    def test_factory_returns_callable(self) -> None:
        """Verify create_adk_reflection_fn returns callable."""
        from unittest.mock import MagicMock

        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_executor = MagicMock()

        result = create_adk_reflection_fn(mock_agent, mock_executor)

        assert callable(result), "Factory must return callable"

    def test_factory_returns_coroutine_function(self) -> None:
        """Verify create_adk_reflection_fn returns async function."""
        from unittest.mock import MagicMock

        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_executor = MagicMock()

        result = create_adk_reflection_fn(mock_agent, mock_executor)

        assert inspect.iscoroutinefunction(result), "Factory must return async function"


class TestBackwardCompatibility:
    """Backward compatibility tests ensuring existing code continues to work."""

    def test_existing_usage_pattern_without_output_key(self) -> None:
        """Verify existing usage without output_key still works."""
        from unittest.mock import MagicMock

        from gepa_adk.engine.adk_reflection import create_adk_reflection_fn

        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"
        mock_executor = MagicMock()

        # Existing usage: no output_key parameter
        reflection_fn = create_adk_reflection_fn(mock_agent, mock_executor)

        assert callable(reflection_fn), "Must return callable without output_key"
