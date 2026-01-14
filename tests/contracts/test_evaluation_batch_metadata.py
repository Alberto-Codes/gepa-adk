"""Contract tests for EvaluationBatch metadata field.

These tests verify the contract for the enhanced EvaluationBatch dataclass
with the new metadata field for passing CriticScorer metadata to reflection.

Run: pytest tests/contracts/test_evaluation_batch_metadata.py -v
"""

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

pytestmark = pytest.mark.contract


class TestEvaluationBatchMetadataContract:
    """Contract tests for EvaluationBatch.metadata field."""

    def test_metadata_field_exists(self) -> None:
        """EvaluationBatch MUST have a metadata field."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(
            outputs=["test"],
            scores=[0.5],
            metadata=[{"feedback": "good"}],
        )
        assert hasattr(batch, "metadata")
        assert batch.metadata is not None

    def test_metadata_defaults_to_none(self) -> None:
        """EvaluationBatch.metadata MUST default to None for backward compatibility."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(outputs=["test"], scores=[0.5])
        assert batch.metadata is None

    def test_metadata_accepts_list_of_dicts(self) -> None:
        """EvaluationBatch.metadata MUST accept list[dict[str, Any]]."""
        from gepa_adk.ports.adapter import EvaluationBatch

        metadata: list[dict[str, Any]] = [
            {"feedback": "Good response", "actionable_guidance": "Be more concise"},
            {"feedback": "Poor response", "dimension_scores": {"accuracy": 0.3}},
        ]
        batch = EvaluationBatch(
            outputs=["output1", "output2"],
            scores=[0.8, 0.3],
            metadata=metadata,
        )
        assert batch.metadata == metadata
        assert batch.metadata is not None
        assert len(batch.metadata) == 2

    def test_metadata_index_alignment_with_scores(self) -> None:
        """metadata[i] MUST correspond to scores[i] (index-aligned)."""
        from gepa_adk.ports.adapter import EvaluationBatch

        outputs = ["a", "b", "c"]
        scores = [0.9, 0.7, 0.5]
        metadata = [
            {"feedback": "excellent"},
            {"feedback": "good"},
            {"feedback": "needs improvement"},
        ]
        batch = EvaluationBatch(outputs=outputs, scores=scores, metadata=metadata)

        # Verify index alignment
        assert batch.metadata is not None
        assert len(batch.metadata) == len(batch.scores) == len(batch.outputs)
        for i in range(len(outputs)):
            # Each index should access corresponding data
            assert batch.outputs[i] == outputs[i]
            assert batch.scores[i] == scores[i]
            assert batch.metadata[i] == metadata[i]

    def test_metadata_preserves_critic_scorer_fields(self) -> None:
        """EvaluationBatch.metadata MUST preserve CriticScorer metadata fields."""
        from gepa_adk.ports.adapter import EvaluationBatch

        critic_metadata = {
            "feedback": "Good response but could be more concise",
            "dimension_scores": {"accuracy": 0.9, "clarity": 0.6, "completeness": 0.8},
            "actionable_guidance": "Reduce response length by 30%",
        }
        batch = EvaluationBatch(
            outputs=["response"],
            scores=[0.75],
            metadata=[critic_metadata],
        )

        assert batch.metadata is not None
        stored = batch.metadata[0]
        assert stored["feedback"] == critic_metadata["feedback"]
        assert stored["dimension_scores"] == critic_metadata["dimension_scores"]
        assert stored["actionable_guidance"] == critic_metadata["actionable_guidance"]

    def test_metadata_allows_partial_fields(self) -> None:
        """EvaluationBatch.metadata MUST allow metadata dicts with partial fields."""
        from gepa_adk.ports.adapter import EvaluationBatch

        # Only feedback, no dimension_scores or actionable_guidance
        partial_metadata = {"feedback": "Good"}
        batch = EvaluationBatch(
            outputs=["test"],
            scores=[0.8],
            metadata=[partial_metadata],
        )

        assert batch.metadata is not None
        assert "feedback" in batch.metadata[0]
        assert "dimension_scores" not in batch.metadata[0]
        assert "actionable_guidance" not in batch.metadata[0]

    def test_metadata_allows_empty_dicts(self) -> None:
        """EvaluationBatch.metadata MUST allow empty dicts (non-critic scorers)."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(
            outputs=["test1", "test2"],
            scores=[0.5, 0.6],
            metadata=[{}, {}],  # Empty metadata from simple scorers
        )

        assert batch.metadata is not None
        assert batch.metadata[0] == {}
        assert batch.metadata[1] == {}

    def test_metadata_immutable_when_frozen(self) -> None:
        """EvaluationBatch MUST remain immutable (frozen=True contract)."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(
            outputs=["test"],
            scores=[0.5],
            metadata=[{"feedback": "good"}],
        )

        with pytest.raises(FrozenInstanceError):
            batch.metadata = [{"feedback": "changed"}]  # type: ignore[misc]

    def test_metadata_with_trajectories_coexistence(self) -> None:
        """EvaluationBatch.metadata MUST coexist with trajectories field."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(
            outputs=["output"],
            scores=[0.75],
            trajectories=[{"trace": "data"}],
            metadata=[{"feedback": "good"}],
        )

        assert batch.trajectories is not None
        assert batch.metadata is not None
        assert len(batch.trajectories) == len(batch.metadata) == 1

    def test_metadata_with_objective_scores_coexistence(self) -> None:
        """EvaluationBatch.metadata MUST coexist with objective_scores field."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(
            outputs=["output"],
            scores=[0.75],
            objective_scores=[{"accuracy": 0.8, "fluency": 0.7}],
            metadata=[{"feedback": "good", "dimension_scores": {"clarity": 0.6}}],
        )

        assert batch.objective_scores is not None
        assert batch.metadata is not None
        # Both can contain dimension-style data without conflict
        assert batch.objective_scores[0]["accuracy"] == 0.8
        assert batch.metadata[0]["dimension_scores"]["clarity"] == 0.6


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing code."""

    def test_existing_code_without_metadata_works(self) -> None:
        """Existing code creating EvaluationBatch without metadata MUST work."""
        from gepa_adk.ports.adapter import EvaluationBatch

        # Simulate existing code pattern
        batch = EvaluationBatch(
            outputs=["a", "b"],
            scores=[0.9, 0.8],
            trajectories=None,
        )
        assert batch.outputs == ["a", "b"]
        assert batch.scores == [0.9, 0.8]
        assert batch.metadata is None  # Default

    def test_existing_code_with_trajectories_works(self) -> None:
        """Existing code with trajectories but no metadata MUST work."""
        from gepa_adk.ports.adapter import EvaluationBatch

        batch = EvaluationBatch(
            outputs=["output"],
            scores=[0.75],
            trajectories=[{"events": []}],
        )
        assert batch.trajectories is not None
        assert batch.metadata is None  # Still defaults to None
