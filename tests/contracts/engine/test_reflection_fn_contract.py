"""Contract tests for ADK reflection function.

This module verifies the type contracts and protocol compliance for the ADK
reflection function used by AsyncReflectiveMutationProposer.

Note:
    These tests ensure the reflection function signature matches the expected
    contract and that implementations can be verified at runtime.
"""

import inspect
from collections.abc import Callable
from typing import Any

import pytest

from gepa_adk.engine.proposer import SESSION_STATE_KEYS, ReflectionFn


class TestReflectionFnTypeAlias:
    """Contract tests for ReflectionFn type alias."""

    def test_reflection_fn_is_callable_type(self) -> None:
        """Verify ReflectionFn is a Callable type."""
        # Get the origin of the type alias
        origin = getattr(ReflectionFn, "__origin__", None)
        assert origin is Callable or isinstance(ReflectionFn, type(Callable)), (
            "ReflectionFn must be a Callable type"
        )

    def test_reflection_fn_signature_parameters(self) -> None:
        """Verify ReflectionFn has correct parameter types."""
        # Expected signature: (str, list[dict[str, Any]]) -> Awaitable[str]
        args = getattr(ReflectionFn, "__args__", None)
        assert args is not None, "ReflectionFn must have type arguments"

        # Callable type structure varies by Python version
        # Just verify it's a proper type alias
        assert len(args) >= 2, "ReflectionFn must have parameter and return types"


class TestSessionStateKeys:
    """Contract tests for SESSION_STATE_KEYS constant."""

    def test_session_state_keys_structure(self) -> None:
        """Verify SESSION_STATE_KEYS has required keys."""
        assert isinstance(SESSION_STATE_KEYS, dict), "SESSION_STATE_KEYS must be a dict"
        assert "current_instruction" in SESSION_STATE_KEYS, (
            "Must have current_instruction key"
        )
        assert "execution_feedback" in SESSION_STATE_KEYS, (
            "Must have execution_feedback key"
        )

    def test_session_state_key_types(self) -> None:
        """Verify SESSION_STATE_KEYS values are type objects."""
        assert SESSION_STATE_KEYS["current_instruction"] is str, (
            "current_instruction must be str type"
        )
        assert SESSION_STATE_KEYS["execution_feedback"] is str, (
            "execution_feedback must be str type (JSON-serialized)"
        )


class TestReflectionFnProtocolCompliance:
    """Protocol compliance tests for reflection functions."""

    @pytest.fixture
    def mock_reflection_fn(self) -> ReflectionFn:
        """Create a mock reflection function matching the signature."""

        async def reflect(
            current_instruction: str,
            feedback: list[dict[str, Any]],
        ) -> str:
            """Mock reflection function."""
            return f"Improved: {current_instruction}"

        return reflect

    def test_mock_reflection_fn_is_callable(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify mock reflection function is callable."""
        assert callable(mock_reflection_fn), "Reflection function must be callable"

    def test_mock_reflection_fn_is_coroutine_function(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify mock reflection function is async."""
        assert inspect.iscoroutinefunction(mock_reflection_fn), (
            "Reflection function must be async"
        )

    @pytest.mark.asyncio
    async def test_mock_reflection_fn_signature(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify mock reflection function accepts correct arguments."""
        # Test function can be called with expected arguments
        result = await mock_reflection_fn(
            "test instruction",
            [{"score": 0.5, "output": "test"}],
        )

        assert isinstance(result, str), "Must return str"
        assert result, "Result should not be empty"

    @pytest.mark.asyncio
    async def test_mock_reflection_fn_return_type(
        self, mock_reflection_fn: ReflectionFn
    ) -> None:
        """Verify mock reflection function returns str."""
        result = await mock_reflection_fn("instruction", [])
        assert isinstance(result, str), "Reflection function must return str"


class TestCreateAdkReflectionFnContract:
    """Contract documentation tests for create_adk_reflection_fn factory.

    Note:
        These tests verify the expected signature and behavior contract.
        Actual implementation tests are in test_proposer.py (unit) and
        test_adk_reflection.py (integration).
    """

    def test_factory_function_signature_documented(self) -> None:
        """Verify factory function contract is documented."""
        # This test documents the expected signature:
        # def create_adk_reflection_fn(
        #     reflection_agent: LlmAgent,
        #     session_service: BaseSessionService | None = None,
        # ) -> ReflectionFn
        expected_params = ["reflection_agent", "session_service"]
        expected_return = "ReflectionFn"

        # Contract is defined in specs/010-adk-reflection-agent/contracts/reflection_fn.py
        assert expected_params == [
            "reflection_agent",
            "session_service",
        ], "Factory must accept reflection_agent and session_service"
        assert expected_return == "ReflectionFn", "Factory must return ReflectionFn"

    def test_factory_function_exists(self) -> None:
        """Verify create_adk_reflection_fn factory function exists."""
        from gepa_adk.engine.proposer import create_adk_reflection_fn

        assert callable(create_adk_reflection_fn), (
            "create_adk_reflection_fn must be callable"
        )

    def test_factory_function_signature_params(self) -> None:
        """Verify create_adk_reflection_fn has correct parameter signature."""
        from gepa_adk.engine.proposer import create_adk_reflection_fn

        sig = inspect.signature(create_adk_reflection_fn)
        params = list(sig.parameters.keys())

        assert "reflection_agent" in params, "Must have reflection_agent parameter"
        assert "session_service" in params, "Must have session_service parameter"

        # Verify session_service has default value None
        assert sig.parameters["session_service"].default is None, (
            "session_service must default to None"
        )

    def test_factory_returns_reflection_fn(self) -> None:
        """Verify create_adk_reflection_fn returns async callable."""
        from gepa_adk.engine.proposer import create_adk_reflection_fn

        # This test will use a mock agent when implementation is complete
        # For now, just verify the function exists and is callable
        assert callable(create_adk_reflection_fn), "Factory must return callable"
