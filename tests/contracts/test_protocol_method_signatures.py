"""Protocol method signature drift guard.

Validates that shared mock implementations match their Protocol method
signatures using ``inspect.signature()``. The Protocol definition is the
single source of truth — no snapshot or hardcoded expectation needed.

``isinstance()`` on ``@runtime_checkable`` Protocols only verifies that
methods *exist*. It does **not** verify parameter names, count, order, or
defaults. This test closes that gap for the three shared mocks
(MockScorer, MockExecutor, MockAdapter) that are used 900+ times across
the test suite. A silent drift here undermines the entire test foundation.

For ``EvolutionResultProtocol`` (data-attribute protocol),
``typing.get_type_hints()`` is used instead since it has no methods.

Attributes:
    PROTOCOL_MOCK_PAIRS (list): Mapping of Protocol classes to their shared
        mock implementations and method names.

Examples:
    Run only these tests:

    ```bash
    pytest tests/contracts/test_protocol_method_signatures.py -v
    ```

See Also:
    - [`test_shared_mock_protocol_compliance`]\
[tests.contracts.test_shared_mock_protocol_compliance]: Behavioral
        compliance tests (isinstance + return types).

Note:
    This test is complementary to ``test_shared_mock_protocol_compliance``
    which verifies behavioral correctness. This test verifies structural
    correctness (parameter names and defaults).
"""

from __future__ import annotations

import asyncio
import inspect
from typing import get_type_hints

import pytest

from gepa_adk.domain.models import EvolutionResult, MultiAgentEvolutionResult
from gepa_adk.ports.adapter import AsyncGEPAAdapter
from gepa_adk.ports.agent_executor import AgentExecutorProtocol
from gepa_adk.ports.evolution_result import EvolutionResultProtocol
from gepa_adk.ports.scorer import Scorer
from tests.conftest import MockExecutor, MockScorer
from tests.fixtures.adapters import MockAdapter

pytestmark = pytest.mark.contract

# --- Protocol-to-Mock mapping ---
# Each entry: (Protocol class, Mock class, list of method names to compare)
PROTOCOL_MOCK_PAIRS: list[tuple[type, type, list[str]]] = [
    (Scorer, MockScorer, ["score", "async_score"]),
    (AgentExecutorProtocol, MockExecutor, ["execute_agent"]),
    (
        AsyncGEPAAdapter,
        MockAdapter,
        ["evaluate", "make_reflective_dataset", "propose_new_texts"],
    ),
]


def _param_names(sig: inspect.Signature) -> list[str]:
    """Extract ordered parameter names, excluding 'self'."""
    return [name for name in sig.parameters if name != "self"]


def _param_defaults(sig: inspect.Signature) -> dict[str, object]:
    """Extract parameter defaults, excluding 'self' and params without defaults."""
    return {
        name: param.default
        for name, param in sig.parameters.items()
        if name != "self" and param.default is not inspect.Parameter.empty
    }


class TestProtocolMethodSignatures:
    """Verify shared mock method signatures match their Protocol definitions."""

    @pytest.mark.parametrize(
        ("protocol_cls", "mock_cls", "methods"),
        PROTOCOL_MOCK_PAIRS,
        ids=[p[0].__name__ for p in PROTOCOL_MOCK_PAIRS],
    )
    def test_method_parameter_names_match(
        self,
        protocol_cls: type,
        mock_cls: type,
        methods: list[str],
    ) -> None:
        """Mock method parameters must match Protocol parameter names and order."""
        for method_name in methods:
            proto_method = getattr(protocol_cls, method_name)
            mock_method = getattr(mock_cls, method_name)

            proto_sig = inspect.signature(proto_method)
            mock_sig = inspect.signature(mock_method)

            proto_params = _param_names(proto_sig)
            mock_params = _param_names(mock_sig)

            # MockExecutor uses **kwargs instead of explicit params — that's OK,
            # but the positional params before **kwargs must match.
            mock_has_var_keyword = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in mock_sig.parameters.values()
            )
            if mock_has_var_keyword:
                # Compare only up to the **kwargs boundary
                positional_count = len(
                    [
                        p
                        for p in mock_sig.parameters.values()
                        if p.kind
                        not in (
                            inspect.Parameter.VAR_KEYWORD,
                            inspect.Parameter.VAR_POSITIONAL,
                        )
                        and p.name != "self"
                    ]
                )
                assert (
                    proto_params[:positional_count] == mock_params[:positional_count]
                ), (
                    f"{mock_cls.__name__}.{method_name} positional params "
                    f"{mock_params[:positional_count]} != "
                    f"{protocol_cls.__name__}.{method_name} params "
                    f"{proto_params[:positional_count]}"
                )
            else:
                assert proto_params == mock_params, (
                    f"{mock_cls.__name__}.{method_name} params {mock_params} != "
                    f"{protocol_cls.__name__}.{method_name} params {proto_params}"
                )

    @pytest.mark.parametrize(
        ("protocol_cls", "mock_cls", "methods"),
        PROTOCOL_MOCK_PAIRS,
        ids=[p[0].__name__ for p in PROTOCOL_MOCK_PAIRS],
    )
    def test_method_defaults_match(
        self,
        protocol_cls: type,
        mock_cls: type,
        methods: list[str],
    ) -> None:
        """Mock method defaults must match Protocol defaults."""
        for method_name in methods:
            proto_method = getattr(protocol_cls, method_name)
            mock_method = getattr(mock_cls, method_name)

            proto_sig = inspect.signature(proto_method)
            mock_sig = inspect.signature(mock_method)

            proto_defaults = _param_defaults(proto_sig)
            mock_defaults = _param_defaults(mock_sig)

            # Only check defaults that exist in both (mock may use **kwargs)
            shared_params = set(proto_defaults) & set(mock_defaults)
            for param in shared_params:
                assert proto_defaults[param] == mock_defaults[param], (
                    f"{mock_cls.__name__}.{method_name} default for '{param}' "
                    f"is {mock_defaults[param]!r}, expected "
                    f"{proto_defaults[param]!r} from {protocol_cls.__name__}"
                )

    @pytest.mark.parametrize(
        ("protocol_cls", "mock_cls", "methods"),
        PROTOCOL_MOCK_PAIRS,
        ids=[p[0].__name__ for p in PROTOCOL_MOCK_PAIRS],
    )
    def test_async_sync_match(
        self,
        protocol_cls: type,
        mock_cls: type,
        methods: list[str],
    ) -> None:
        """If Protocol method is async, mock method must also be async (and vice versa)."""
        for method_name in methods:
            proto_method = getattr(protocol_cls, method_name)
            mock_method = getattr(mock_cls, method_name)

            proto_is_async = asyncio.iscoroutinefunction(proto_method)
            mock_is_async = asyncio.iscoroutinefunction(mock_method)

            assert proto_is_async == mock_is_async, (
                f"{mock_cls.__name__}.{method_name} async mismatch: "
                f"Protocol is {'async' if proto_is_async else 'sync'}, "
                f"mock is {'async' if mock_is_async else 'sync'}"
            )


class TestEvolutionResultProtocolAttributes:
    """Verify concrete result types expose all EvolutionResultProtocol attributes."""

    EXPECTED_ATTRIBUTES = [
        "original_score",
        "final_score",
        "evolved_components",
        "iteration_history",
        "total_iterations",
    ]

    EXPECTED_PROPERTIES = [
        "improvement",
        "improved",
    ]

    @pytest.mark.parametrize(
        "concrete_cls",
        [EvolutionResult, MultiAgentEvolutionResult],
        ids=["EvolutionResult", "MultiAgentEvolutionResult"],
    )
    def test_data_attributes_present(self, concrete_cls: type) -> None:
        """Concrete result types must have all protocol data attributes."""
        hints = get_type_hints(concrete_cls)
        for attr in self.EXPECTED_ATTRIBUTES:
            assert attr in hints, (
                f"{concrete_cls.__name__} missing attribute '{attr}' "
                f"required by EvolutionResultProtocol"
            )

    @pytest.mark.parametrize(
        "concrete_cls",
        [EvolutionResult, MultiAgentEvolutionResult],
        ids=["EvolutionResult", "MultiAgentEvolutionResult"],
    )
    def test_properties_present(self, concrete_cls: type) -> None:
        """Concrete result types must have all protocol properties."""
        for prop_name in self.EXPECTED_PROPERTIES:
            assert hasattr(concrete_cls, prop_name), (
                f"{concrete_cls.__name__} missing property '{prop_name}' "
                f"required by EvolutionResultProtocol"
            )
            assert isinstance(getattr(concrete_cls, prop_name), property), (
                f"{concrete_cls.__name__}.{prop_name} must be a property, "
                f"got {type(getattr(concrete_cls, prop_name))}"
            )

    def test_protocol_type_hints_match_expectations(self) -> None:
        """EvolutionResultProtocol must define exactly the expected attributes."""
        proto_hints = get_type_hints(EvolutionResultProtocol)
        for attr in self.EXPECTED_ATTRIBUTES:
            assert attr in proto_hints, (
                f"EvolutionResultProtocol missing attribute '{attr}'"
            )


__all__: list[str] = []
