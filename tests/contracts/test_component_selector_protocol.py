"""Contract tests for ComponentSelectorProtocol."""

from typing import Protocol

import pytest

from gepa_adk.adapters.selection.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
)
from gepa_adk.ports import ComponentSelectorProtocol

pytestmark = pytest.mark.contract


class TestComponentSelectorProtocolRuntimeCheckable:
    """Positive compliance: isinstance checks for implementations."""

    def test_import_path_equivalence(self) -> None:
        """ComponentSelectorProtocol is accessible from both import paths."""
        from gepa_adk.ports import ComponentSelectorProtocol as from_init
        from gepa_adk.ports.component_selector import (
            ComponentSelectorProtocol as from_module,
        )

        assert from_init is from_module

    def test_is_protocol(self) -> None:
        """ComponentSelectorProtocol is a Protocol."""
        assert issubclass(ComponentSelectorProtocol, Protocol)

    def test_is_runtime_checkable(self) -> None:
        """ComponentSelectorProtocol supports isinstance checks."""

        class ImplementsProtocol:
            async def select_components(
                self, components: list[str], iteration: int, candidate_idx: int
            ) -> list[str]:
                return []

        assert isinstance(ImplementsProtocol(), ComponentSelectorProtocol)

    def test_round_robin_selector_satisfies_protocol(self) -> None:
        """RoundRobinComponentSelector satisfies ComponentSelectorProtocol."""
        selector = RoundRobinComponentSelector()
        assert isinstance(selector, ComponentSelectorProtocol)

    def test_all_component_selector_satisfies_protocol(self) -> None:
        """AllComponentSelector satisfies ComponentSelectorProtocol."""
        selector = AllComponentSelector()
        assert isinstance(selector, ComponentSelectorProtocol)


class TestComponentSelectorProtocolBehavior:
    """Behavioral expectations: return types, method contracts."""

    @pytest.mark.asyncio
    async def test_select_components_returns_list(self) -> None:
        """select_components returns a list of strings."""
        selector = AllComponentSelector()
        result = await selector.select_components(
            components=["instruction", "schema"], iteration=0, candidate_idx=0
        )
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    @pytest.mark.asyncio
    async def test_select_components_returns_subset(self) -> None:
        """select_components returns a subset of the input components."""
        selector = RoundRobinComponentSelector()
        components = ["instruction", "schema", "examples"]
        result = await selector.select_components(
            components=components, iteration=0, candidate_idx=0
        )
        assert all(c in components for c in result)


class TestComponentSelectorProtocolNonCompliance:
    """Negative cases: objects missing required methods are not instances."""

    def test_missing_method_not_isinstance(self) -> None:
        """Class without select_components fails isinstance check."""

        class MissingMethod:
            pass

        assert not isinstance(MissingMethod(), ComponentSelectorProtocol)

    def test_runtime_checkable_limitation_documented(self) -> None:
        """@runtime_checkable only checks method existence, not signatures."""

        class WrongSignature:
            async def select_components(self, components: list[str]) -> list[str]:
                return []

        # runtime_checkable only checks for presence of method, not signature
        assert isinstance(WrongSignature(), ComponentSelectorProtocol)
