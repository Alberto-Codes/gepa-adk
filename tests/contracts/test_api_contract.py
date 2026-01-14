"""Contract tests for evolve() and evolve_sync() API functions.

These tests ensure the API functions have correct signatures, return types,
and are properly exported from the package. These are contract tests that
verify interface compliance without requiring actual evolution execution.

Note:
    These tests use introspection to verify function signatures and imports.
    Unit tests (in tests/unit/) verify actual behavior with mocks.
    Integration tests (in tests/integration/) verify real ADK integration.
"""

from __future__ import annotations

import inspect

import pytest

import gepa_adk

pytestmark = pytest.mark.contract


class TestEvolveContract:
    """Contract tests for evolve() function."""

    def test_evolve_exists(self):
        """Evolve must be importable from gepa_adk."""
        assert hasattr(gepa_adk, "evolve")
        assert gepa_adk.evolve is not None

    def test_evolve_is_async(self):
        """Evolve must be an async function."""
        assert inspect.iscoroutinefunction(gepa_adk.evolve)

    def test_evolve_signature_has_required_params(self):
        """Evolve must have agent and trainset as required."""
        sig = inspect.signature(gepa_adk.evolve)
        params = sig.parameters

        assert "agent" in params
        assert "trainset" in params
        assert params["agent"].default is inspect.Parameter.empty
        assert params["trainset"].default is inspect.Parameter.empty

    def test_evolve_signature_has_optional_params(self):
        """Evolve must have optional config parameters."""
        sig = inspect.signature(gepa_adk.evolve)
        params = sig.parameters

        optional = [
            "valset",
            "critic",
            "reflection_agent",
            "config",
            "trajectory_config",
            "state_guard",
        ]
        for param in optional:
            assert param in params
            assert params[param].default is None

    def test_evolve_return_annotation(self):
        """Evolve must return EvolutionResult."""
        sig = inspect.signature(gepa_adk.evolve)
        # Handle both string annotations and class types
        annotation = sig.return_annotation
        expected = "EvolutionResult"
        if isinstance(annotation, str):
            assert annotation == expected
        else:
            assert annotation.__name__ == expected


class TestEvolveSyncContract:
    """Contract tests for evolve_sync() function."""

    def test_evolve_sync_exists(self):
        """evolve_sync must be importable from gepa_adk."""
        assert hasattr(gepa_adk, "evolve_sync")
        assert gepa_adk.evolve_sync is not None

    def test_evolve_sync_is_not_async(self):
        """evolve_sync must NOT be an async function."""
        assert not inspect.iscoroutinefunction(gepa_adk.evolve_sync)

    def test_evolve_sync_has_required_params(self):
        """evolve_sync must have agent and trainset as required."""
        sig = inspect.signature(gepa_adk.evolve_sync)
        params = sig.parameters

        assert "agent" in params
        assert "trainset" in params
        assert params["agent"].default is inspect.Parameter.empty
        assert params["trainset"].default is inspect.Parameter.empty

    def test_evolve_sync_has_kwargs(self):
        """evolve_sync must accept **kwargs for evolve params."""
        sig = inspect.signature(gepa_adk.evolve_sync)
        # Check for VAR_KEYWORD parameter
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        assert has_kwargs

    def test_evolve_sync_return_annotation(self):
        """evolve_sync must return EvolutionResult."""
        sig = inspect.signature(gepa_adk.evolve_sync)
        # Handle both string annotations and class types
        annotation = sig.return_annotation
        expected = "EvolutionResult"
        if isinstance(annotation, str):
            assert annotation == expected
        else:
            assert annotation.__name__ == expected


class TestPackageExports:
    """Contract tests for package exports."""

    def test_evolve_exported_from_package(self):
        """Evolve must be exported from gepa_adk package."""
        assert hasattr(gepa_adk, "evolve")
        # Verify it's callable
        assert callable(gepa_adk.evolve)

    def test_evolve_sync_exported_from_package(self):
        """evolve_sync must be exported from gepa_adk package."""
        assert hasattr(gepa_adk, "evolve_sync")
        # Verify it's callable
        assert callable(gepa_adk.evolve_sync)

    def test_evolve_in_all_list(self):
        """Evolve must be in __all__ list."""
        assert "evolve" in gepa_adk.__all__

    def test_evolve_sync_in_all_list(self):
        """evolve_sync must be in __all__ list."""
        assert "evolve_sync" in gepa_adk.__all__
