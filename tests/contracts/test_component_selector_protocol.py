"""Contract tests for ComponentSelectorProtocol."""

from typing import Protocol

import pytest

from gepa_adk.ports import ComponentSelectorProtocol

pytestmark = pytest.mark.contract


def test_component_selector_protocol_is_protocol() -> None:
    """Test that ComponentSelectorProtocol is a Protocol."""
    assert issubclass(ComponentSelectorProtocol, Protocol)


def test_component_selector_protocol_is_runtime_checkable() -> None:
    """Test that ComponentSelectorProtocol supports isinstance checks."""

    class ImplementsProtocol:
        async def select_components(
            self, components: list[str], iteration: int, candidate_idx: int
        ) -> list[str]:
            return []

    assert isinstance(ImplementsProtocol(), ComponentSelectorProtocol)


def test_component_selector_protocol_rejects_incomplete_implementation() -> None:
    """Test that incomplete implementation fails isinstance check."""

    class MissingMethod:
        pass

    assert not isinstance(MissingMethod(), ComponentSelectorProtocol)

    class WrongSignature:
        # Missing arguments
        async def select_components(self, components: list[str]) -> list[str]:
            return []

    # Note: runtime_checkable only checks for presence of method, not signature compatibility
    # so we only test method presence here
    assert isinstance(WrongSignature(), ComponentSelectorProtocol)
