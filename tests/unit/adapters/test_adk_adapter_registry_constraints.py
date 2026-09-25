"""Schema constraints reach the ``output_schema`` handler of the adapter's registry.

``ADKAdapter`` sets the caller's ``SchemaConstraints`` on the
``OutputSchemaHandler`` it resolves through its registry and clears them
in ``cleanup()``. A registry without an ``output_schema`` handler gets
nothing set and nothing cleared (GitHub issue 451).

Notes:
    The handler is a fresh instance registered into a fresh registry, so
    the default registry's singleton handler is never touched.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters import ADKAdapter
from gepa_adk.adapters.components import (
    ComponentHandlerRegistry,
    InstructionHandler,
    OutputSchemaHandler,
)
from gepa_adk.domain.types import SchemaConstraints
from tests.conftest import MockExecutor, MockScorer

pytestmark = pytest.mark.unit


def _agent() -> LlmAgent:
    """Build a plain agent.

    Returns:
        An LlmAgent with an instruction only.
    """
    return LlmAgent(
        name="plain", model="ollama_chat/gpt-oss:20b", instruction="Answer."
    )


class TestConstraintsFollowTheRegistry:
    """Constraints are set and cleared on the registry's own handler."""

    def test_constraints_set_on_the_registry_handler_and_cleared(self) -> None:
        """The handler in the given registry carries the constraints until cleanup."""
        registry = ComponentHandlerRegistry()
        handler = OutputSchemaHandler()
        registry.register("output_schema", handler)
        constraints = SchemaConstraints(required_fields=("answer",))

        adapter = ADKAdapter(
            agent=_agent(),
            scorer=MockScorer(),
            executor=MockExecutor(),
            proposer=MagicMock(),
            schema_constraints=constraints,
            registry=registry,
        )

        assert handler._constraints is constraints
        adapter.cleanup()
        assert handler._constraints is None

    def test_registry_without_output_schema_handler_sets_nothing(self) -> None:
        """A registry lacking the handler leaves constraints unapplied."""
        registry = ComponentHandlerRegistry()
        registry.register("instruction", InstructionHandler())

        adapter = ADKAdapter(
            agent=_agent(),
            scorer=MockScorer(),
            executor=MockExecutor(),
            proposer=MagicMock(),
            schema_constraints=SchemaConstraints(required_fields=("answer",)),
            registry=registry,
        )
        adapter.cleanup()

        assert not registry.has("output_schema")
