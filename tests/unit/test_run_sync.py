"""Tests for run_sync() universal wrapper and evolve_sync() deprecation.

Attributes:
    pytestmark: All tests in this module are unit tests.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import patch

import pytest

from gepa_adk.api import evolve, evolve_group, evolve_sync, evolve_workflow, run_sync

pytestmark = pytest.mark.unit


class TestRunSync:
    """Tests for the run_sync() universal wrapper mechanics."""

    async def _async_return_value(self, value: str) -> str:
        """Helper async function returning a known value."""
        return value

    def test_run_sync_returns_coroutine_result(self) -> None:
        """run_sync executes a coroutine and returns its result."""
        result = run_sync(self._async_return_value("hello"))
        assert result == "hello"

    def test_run_sync_with_typed_return(self) -> None:
        """run_sync preserves the generic return type."""

        async def typed_async() -> int:
            return 42

        result = run_sync(typed_async())
        assert result == 42
        assert isinstance(result, int)

    def test_run_sync_propagates_exceptions(self) -> None:
        """run_sync propagates exceptions from the coroutine."""

        async def failing_async() -> None:
            msg = "test error"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="test error"):
            run_sync(failing_async())

    def test_run_sync_rejects_non_coroutine(self) -> None:
        """run_sync raises TypeError for non-coroutine arguments."""
        with pytest.raises(TypeError, match="coroutine"):
            run_sync(42)  # type: ignore[arg-type]

    def test_run_sync_rejects_function_not_call(self) -> None:
        """run_sync raises TypeError when passed a function instead of a call."""

        async def some_func() -> str:
            return "ok"

        with pytest.raises(TypeError, match="coroutine"):
            run_sync(some_func)  # type: ignore[arg-type]


class TestRunSyncErrorHandling:
    """Tests for run_sync error handling paths."""

    def test_run_sync_without_nest_asyncio_raises_informative_error(self) -> None:
        """When nest_asyncio is unavailable and event loop is running, error is clear."""

        async def dummy() -> str:
            return "ok"

        coro = dummy()
        with (
            patch(
                "asyncio.run",
                side_effect=RuntimeError(
                    "asyncio.run() cannot be called from a running event loop"
                ),
            ),
            patch.dict("sys.modules", {"nest_asyncio": None}),
            pytest.raises(RuntimeError, match="nest.asyncio"),
        ):
            run_sync(coro)

    def test_run_sync_propagates_non_event_loop_runtime_errors(self) -> None:
        """RuntimeErrors not about event loops propagate unchanged."""

        async def dummy() -> str:
            return "ok"

        coro = dummy()
        with (
            patch("asyncio.run", side_effect=RuntimeError("some other error")),
            pytest.raises(RuntimeError, match="some other error"),
        ):
            run_sync(coro)


class TestRunSyncNestedLoop:
    """Tests for the nest_asyncio fallback path."""

    def test_run_sync_fallback_with_running_event_loop(self) -> None:
        """run_sync falls back to nest_asyncio when event loop is running."""

        async def dummy() -> str:
            return "nested_ok"

        coro = dummy()

        # Simulate: first asyncio.run fails, then nest_asyncio path succeeds
        call_count = 0
        original_run = asyncio.run

        def patched_run(c: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError(
                    "asyncio.run() cannot be called from a running event loop"
                )
            return original_run(c, **kwargs)  # type: ignore[arg-type]

        with patch("asyncio.run", side_effect=patched_run):
            result = run_sync(coro)

        assert result == "nested_ok"


class TestEvolveSyncDeprecation:
    """Tests for evolve_sync() deprecation warning."""

    def test_evolve_sync_emits_deprecation_warning(self) -> None:
        """evolve_sync emits DeprecationWarning pointing to run_sync."""
        with pytest.warns(DeprecationWarning, match="run_sync"):
            try:
                # Will fail due to invalid args, but warning should fire first
                evolve_sync(None, [])  # type: ignore[arg-type]
            except Exception:  # noqa: BLE001
                pass

    def test_evolve_sync_forwards_kwargs_to_evolve(self) -> None:
        """evolve_sync passes all kwargs through to evolve()."""
        captured: dict[str, object] = {}

        async def fake_evolve(*args: object, **kwargs: object) -> str:
            captured["args"] = args
            captured["kwargs"] = kwargs
            return "result"

        with (
            pytest.warns(DeprecationWarning),
            patch("gepa_adk.api.evolve", side_effect=fake_evolve),
        ):
            sentinel_config = object()
            evolve_sync(
                "agent",  # type: ignore[arg-type]
                [{"input": "x"}],
                config=sentinel_config,
                valset=[{"input": "v"}],
            )

        assert captured["kwargs"]["config"] is sentinel_config
        assert captured["kwargs"]["valset"] == [{"input": "v"}]


class TestKeywordOnlySeparator:
    """Tests for keyword-only parameter enforcement on evolve functions."""

    def test_evolve_optional_params_are_keyword_only(self) -> None:
        """All optional params of evolve() after trainset are keyword-only."""
        sig = inspect.signature(evolve)
        params = sig.parameters
        # First two (agent, trainset) are positional-or-keyword
        positional_names = ["agent", "trainset"]
        for name in positional_names:
            assert params[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

        # Everything else must be keyword-only
        optional_names = [n for n in params if n not in positional_names]
        for name in optional_names:
            assert params[name].kind == inspect.Parameter.KEYWORD_ONLY, (
                f"evolve() param '{name}' should be keyword-only"
            )

    def test_evolve_group_optional_params_are_keyword_only(self) -> None:
        """All optional params of evolve_group() after trainset are keyword-only."""
        sig = inspect.signature(evolve_group)
        params = sig.parameters
        positional_names = ["agents", "primary", "trainset"]
        for name in positional_names:
            assert params[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

        optional_names = [n for n in params if n not in positional_names]
        for name in optional_names:
            assert params[name].kind == inspect.Parameter.KEYWORD_ONLY, (
                f"evolve_group() param '{name}' should be keyword-only"
            )

    def test_evolve_workflow_optional_params_are_keyword_only(self) -> None:
        """All optional params of evolve_workflow() after trainset are keyword-only."""
        sig = inspect.signature(evolve_workflow)
        params = sig.parameters
        positional_names = ["workflow", "trainset"]
        for name in positional_names:
            assert params[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD

        optional_names = [n for n in params if n not in positional_names]
        for name in optional_names:
            assert params[name].kind == inspect.Parameter.KEYWORD_ONLY, (
                f"evolve_workflow() param '{name}' should be keyword-only"
            )


__all__ = [
    "TestEvolveSyncDeprecation",
    "TestKeywordOnlySeparator",
    "TestRunSync",
    "TestRunSyncErrorHandling",
    "TestRunSyncNestedLoop",
]
