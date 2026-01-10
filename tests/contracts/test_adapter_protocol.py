"""Contract tests for AsyncGEPAAdapter protocol compliance.

Note:
    These tests ensure adapters implement the required async methods
    with correct signatures and return types for engine compatibility.
"""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

import pytest

from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch


class MockAdapter:
    """Skeleton mock adapter for contract testing.

    Note:
        All methods return minimal valid responses for testing
        protocol compliance without complex business logic.
    """

    async def evaluate(
        self,
        batch: list[dict[str, Any]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Return a minimal evaluation batch for contract checks."""
        outputs = [f"output_{i}" for i in range(len(batch))]
        scores = [1.0 for _ in batch]
        trajectories = (
            [{"trace": i, "candidate": candidate} for i in range(len(batch))]
            if capture_traces
            else None
        )
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Return a minimal reflective dataset for each component."""
        return {
            component: [
                {
                    "Inputs": {"candidate": candidate},
                    "Generated Outputs": eval_batch.outputs,
                    "Feedback": "ok",
                }
            ]
            for component in components_to_update
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Return simple proposal updates for each component."""
        return {
            component: f"Improved {candidate.get(component, component)}"
            for component in components_to_update
        }


@pytest.mark.contract
class TestAsyncGEPAAdapterProtocol:
    """Contract tests for AsyncGEPAAdapter protocol compliance.

    Note:
        All tests use MockAdapter to verify protocol contracts.
        Tests cover method signatures, return types, and async behavior.
    """

    @pytest.mark.asyncio
    async def test_evaluate_returns_correct_structure(self) -> None:
        """Ensure evaluate returns an EvaluationBatch with aligned lengths."""
        adapter = MockAdapter()
        batch = [{"input": "test1"}, {"input": "test2"}]
        candidate = {"instruction": "Be helpful"}

        result = await adapter.evaluate(batch, candidate, capture_traces=True)

        assert len(result.outputs) == len(batch)
        assert len(result.scores) == len(batch)
        assert result.trajectories is not None
        assert len(result.trajectories) == len(batch)

    @pytest.mark.asyncio
    async def test_make_reflective_dataset_structure(self) -> None:
        """Ensure make_reflective_dataset returns per-component examples."""
        adapter = MockAdapter()
        candidate = {"instruction": "Be helpful", "format": "JSON"}
        eval_batch = EvaluationBatch(
            outputs=["out1", "out2"],
            scores=[0.8, 0.9],
            trajectories=[{"trace": 1}, {"trace": 2}],
        )
        components = ["instruction"]

        result = await adapter.make_reflective_dataset(
            candidate, eval_batch, components
        )

        assert "instruction" in result
        assert isinstance(result["instruction"], Sequence)
        for example in result["instruction"]:
            assert isinstance(example, Mapping)

    @pytest.mark.asyncio
    async def test_propose_new_texts_structure(self) -> None:
        """Ensure propose_new_texts returns string updates per component."""
        adapter = MockAdapter()
        candidate = {"instruction": "Be helpful"}
        reflective_dataset = {
            "instruction": [
                {"Inputs": {"prompt": "x"}, "Generated Outputs": "", "Feedback": ""}
            ]
        }
        components = ["instruction"]

        result = await adapter.propose_new_texts(
            candidate, reflective_dataset, components
        )

        assert "instruction" in result
        assert isinstance(result["instruction"], str)

    def test_runtime_checkable(self) -> None:
        """Verify AsyncGEPAAdapter supports runtime isinstance checks."""
        adapter = MockAdapter()
        assert isinstance(adapter, AsyncGEPAAdapter)

    def test_incomplete_implementation_not_recognized(self) -> None:
        """Reject implementations missing required protocol methods."""

        class IncompleteAdapter:
            async def evaluate(self, batch, candidate, capture_traces=False):
                return EvaluationBatch(outputs=[], scores=[])

        adapter = IncompleteAdapter()
        assert not isinstance(adapter, AsyncGEPAAdapter)

    def test_sync_method_rejected(self) -> None:
        """Detect sync methods when coroutines are required."""

        class SyncAdapter:
            def evaluate(self, batch, candidate, capture_traces=False):
                return EvaluationBatch(outputs=[], scores=[])

            def make_reflective_dataset(
                self, candidate, eval_batch, components_to_update
            ):
                return {}

            def propose_new_texts(
                self, candidate, reflective_dataset, components_to_update
            ):
                return {}

        adapter = SyncAdapter()
        assert not asyncio.iscoroutinefunction(adapter.evaluate)
        assert not asyncio.iscoroutinefunction(adapter.make_reflective_dataset)
        assert not asyncio.iscoroutinefunction(adapter.propose_new_texts)

    def test_methods_are_coroutines(self) -> None:
        """Require async coroutine methods for protocol compliance."""
        adapter = MockAdapter()
        assert asyncio.iscoroutinefunction(adapter.evaluate)
        assert asyncio.iscoroutinefunction(adapter.make_reflective_dataset)
        assert asyncio.iscoroutinefunction(adapter.propose_new_texts)

    def test_protocol_with_specific_generic_types(self) -> None:
        """Support adapters with specific generic type arguments."""

        class DictAdapter:
            async def evaluate(
                self,
                batch: list[dict[str, str]],
                candidate: dict[str, str],
                capture_traces: bool = False,
            ) -> EvaluationBatch[dict[str, str], str]:
                """Return a typed evaluation batch for dict inputs."""
                trajectories = batch if capture_traces else None
                return EvaluationBatch(
                    outputs=["ok" for _ in batch],
                    scores=[1.0 for _ in batch],
                    trajectories=trajectories,
                )

            async def make_reflective_dataset(
                self,
                candidate: dict[str, str],
                eval_batch: EvaluationBatch[dict[str, str], str],
                components_to_update: list[str],
            ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
                """Return minimal reflective examples for typed inputs."""
                return {
                    component: [{"Inputs": {}, "Generated Outputs": "", "Feedback": ""}]
                    for component in components_to_update
                }

            async def propose_new_texts(
                self,
                candidate: dict[str, str],
                reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
                components_to_update: list[str],
            ) -> dict[str, str]:
                """Return simple proposals for typed inputs."""
                return {component: "ok" for component in components_to_update}

        adapter: AsyncGEPAAdapter[dict[str, str], dict[str, str], str] = DictAdapter()
        assert isinstance(adapter, AsyncGEPAAdapter)

    def test_multiple_adapters_with_different_generic_types(self) -> None:
        """Allow multiple adapters with distinct generic type parameters."""

        class StringAdapter:
            async def evaluate(
                self,
                batch: list[str],
                candidate: dict[str, str],
                capture_traces: bool = False,
            ) -> EvaluationBatch[str, str]:
                """Return evaluation batch for string inputs."""
                trajectories = batch if capture_traces else None
                return EvaluationBatch(
                    outputs=[item.upper() for item in batch],
                    scores=[1.0 for _ in batch],
                    trajectories=trajectories,
                )

            async def make_reflective_dataset(
                self,
                candidate: dict[str, str],
                eval_batch: EvaluationBatch[str, str],
                components_to_update: list[str],
            ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
                """Return minimal reflective examples for string adapter."""
                return {
                    component: [{"Inputs": {}, "Generated Outputs": "", "Feedback": ""}]
                    for component in components_to_update
                }

            async def propose_new_texts(
                self,
                candidate: dict[str, str],
                reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
                components_to_update: list[str],
            ) -> dict[str, str]:
                """Return simple proposals for string adapter."""
                return {component: "ok" for component in components_to_update}

        class IntAdapter:
            async def evaluate(
                self,
                batch: list[int],
                candidate: dict[str, str],
                capture_traces: bool = False,
            ) -> EvaluationBatch[int, float]:
                """Return evaluation batch for integer inputs."""
                trajectories = batch if capture_traces else None
                return EvaluationBatch(
                    outputs=[float(item) for item in batch],
                    scores=[1.0 for _ in batch],
                    trajectories=trajectories,
                )

            async def make_reflective_dataset(
                self,
                candidate: dict[str, str],
                eval_batch: EvaluationBatch[int, float],
                components_to_update: list[str],
            ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
                """Return minimal reflective examples for int adapter."""
                return {
                    component: [{"Inputs": {}, "Generated Outputs": "", "Feedback": ""}]
                    for component in components_to_update
                }

            async def propose_new_texts(
                self,
                candidate: dict[str, str],
                reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
                components_to_update: list[str],
            ) -> dict[str, str]:
                """Return simple proposals for int adapter."""
                return {component: "ok" for component in components_to_update}

        string_adapter: AsyncGEPAAdapter[str, str, str] = StringAdapter()
        int_adapter: AsyncGEPAAdapter[int, int, float] = IntAdapter()

        assert isinstance(string_adapter, AsyncGEPAAdapter)
        assert isinstance(int_adapter, AsyncGEPAAdapter)
