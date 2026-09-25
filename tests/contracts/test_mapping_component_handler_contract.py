"""Contract tests for MappingComponentHandler protocol compliance.

``MappingComponentHandler`` targets a value the caller owns rather than an
agent attribute. It must still satisfy the ComponentHandler contract the
other handlers satisfy.

Contract Requirements:
    - Passes ``isinstance(handler, ComponentHandler)``
    - serialize() returns the key's text as ``str``
    - apply() then restore() leaves the caller's mapping unchanged

Examples:
    Run only these contract tests:

    ```bash
    uv run pytest tests/contracts/test_mapping_component_handler_contract.py -q
    ```

See Also:
    - [`test_component_handler_protocol`][tests.contracts.test_component_handler_protocol]:
      Contract tests for the built-in handlers.
"""

from __future__ import annotations

import pytest

from gepa_adk.adapters.components import MappingComponentHandler
from gepa_adk.ports.component_handler import ComponentHandler

pytestmark = pytest.mark.contract


class TestMappingComponentHandlerProtocolCompliance:
    """Contract tests for MappingComponentHandler.

    Examples:
        ```python
        handler = MappingComponentHandler({"greeting": "hello"}, key="greeting")
        ```
    """

    @pytest.fixture
    def prompts(self) -> dict[str, str]:
        """Provide a fresh caller-owned mapping.

        Returns:
            A two-key mapping of prompt strings.
        """
        return {"greeting": "hello", "farewell": "bye"}

    @pytest.fixture
    def handler(self, prompts: dict[str, str]) -> ComponentHandler:
        """Provide a handler bound to the ``greeting`` key.

        Args:
            prompts: The caller-owned mapping fixture.

        Returns:
            A MappingComponentHandler for ``greeting``.
        """
        return MappingComponentHandler(prompts, key="greeting")

    def test_isinstance_protocol(self, handler: ComponentHandler) -> None:
        """MappingComponentHandler must pass isinstance(ComponentHandler)."""
        assert isinstance(handler, ComponentHandler)

    def test_serialize_returns_string(self, handler: ComponentHandler) -> None:
        """serialize() must return the key's text as str."""
        result = handler.serialize(None)
        assert isinstance(result, str)
        assert result == "hello"

    def test_apply_restore_idempotent(
        self, handler: ComponentHandler, prompts: dict[str, str]
    ) -> None:
        """apply() then restore() must leave the caller's mapping unchanged."""
        before = dict(prompts)

        returned_original = handler.apply(None, "hi")
        assert returned_original == "hello"
        assert prompts == {"greeting": "hi", "farewell": "bye"}

        handler.restore(None, returned_original)
        assert prompts == before
