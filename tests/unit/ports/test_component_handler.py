"""Unit tests for ComponentHandler protocol definition.

This module tests the protocol definition itself, verifying that
the protocol is correctly defined with proper method signatures
and runtime checkability.
"""

from __future__ import annotations

from typing import Any


class TestComponentHandlerProtocol:
    """Unit tests for ComponentHandler protocol definition."""

    def test_protocol_exists(self) -> None:
        """Verify ComponentHandler protocol can be imported."""
        from gepa_adk.ports.component_handler import ComponentHandler

        assert ComponentHandler is not None

    def test_protocol_is_runtime_checkable(self) -> None:
        """Verify protocol uses @runtime_checkable decorator."""
        from gepa_adk.ports.component_handler import ComponentHandler

        # Check that isinstance works (indicator of runtime_checkable)
        class ValidHandler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        assert isinstance(ValidHandler(), ComponentHandler)

    def test_protocol_requires_serialize_method(self) -> None:
        """Verify protocol requires serialize method."""
        from gepa_adk.ports.component_handler import ComponentHandler

        class MissingSerialize:
            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        assert not isinstance(MissingSerialize(), ComponentHandler)

    def test_protocol_requires_apply_method(self) -> None:
        """Verify protocol requires apply method."""
        from gepa_adk.ports.component_handler import ComponentHandler

        class MissingApply:
            def serialize(self, agent: Any) -> str:
                return ""

            def restore(self, agent: Any, original: Any) -> None:
                pass

        assert not isinstance(MissingApply(), ComponentHandler)

    def test_protocol_requires_restore_method(self) -> None:
        """Verify protocol requires restore method."""
        from gepa_adk.ports.component_handler import ComponentHandler

        class MissingRestore:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

        assert not isinstance(MissingRestore(), ComponentHandler)

    def test_protocol_exported_from_ports_package(self) -> None:
        """Verify protocol is exported from ports package."""
        from gepa_adk.ports import ComponentHandler

        assert ComponentHandler is not None


class TestComponentHandlerMethodSignatures:
    """Test protocol method signature requirements."""

    def test_serialize_signature(self) -> None:
        """Verify serialize method accepts agent and returns str."""
        from gepa_adk.ports.component_handler import ComponentHandler

        # A compliant class should work with these signatures
        class Handler:
            def serialize(self, agent: Any) -> str:
                return "test"

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = Handler()
        assert isinstance(handler, ComponentHandler)

        # Test actual call
        result = handler.serialize(None)
        assert isinstance(result, str)

    def test_apply_signature(self) -> None:
        """Verify apply method accepts agent and value, returns original."""
        from gepa_adk.ports.component_handler import ComponentHandler

        class Handler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return "original"

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = Handler()
        assert isinstance(handler, ComponentHandler)

        # Test actual call
        result = handler.apply(None, "new_value")
        assert result == "original"

    def test_restore_signature(self) -> None:
        """Verify restore method accepts agent and original, returns None."""
        from gepa_adk.ports.component_handler import ComponentHandler

        class Handler:
            def serialize(self, agent: Any) -> str:
                return ""

            def apply(self, agent: Any, value: str) -> Any:
                return None

            def restore(self, agent: Any, original: Any) -> None:
                pass

        handler = Handler()
        assert isinstance(handler, ComponentHandler)

        # Test actual call - should not raise
        result = handler.restore(None, "original")
        assert result is None
