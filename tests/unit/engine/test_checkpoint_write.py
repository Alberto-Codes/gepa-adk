"""Unit tests for the checkpoint file helpers.

``write_checkpoint`` must replace the checkpoint atomically: a failure while
replacing leaves the previous file as it was and propagates the error.

Examples:
    Run these tests:

    ```bash
    uv run pytest tests/unit/engine/test_checkpoint_write.py -q
    ```

See Also:
    - [`gepa_adk.engine.checkpoint`][gepa_adk.engine.checkpoint]: The helpers
      under test.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.engine import checkpoint
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.unit


class TestAtomicWrite:
    """The checkpoint is replaced whole or not at all.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_write.py::TestAtomicWrite" -q
        ```
    """

    def test_failed_replace_keeps_previous_file_and_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A replace that raises leaves the old checkpoint and no temp file."""
        path = tmp_path / "checkpoint.json"
        checkpoint.write_checkpoint(path, {"checkpoint_version": 1, "iteration": 1})
        before = path.read_text(encoding="utf-8")

        def fail_replace(src: object, dst: object) -> None:
            """Stand in for os.replace and fail like a full disk.

            Args:
                src: Ignored source path.
                dst: Ignored destination path.

            Raises:
                OSError: Always.
            """
            raise OSError("disk full")

        monkeypatch.setattr(checkpoint.os, "replace", fail_replace)
        with pytest.raises(OSError, match="disk full"):
            checkpoint.write_checkpoint(path, {"checkpoint_version": 1, "iteration": 2})

        assert path.read_text(encoding="utf-8") == before
        assert json.loads(before)["iteration"] == 1
        assert sorted(p.name for p in tmp_path.iterdir()) == ["checkpoint.json"]

    def test_write_creates_parent_and_replaces(self, tmp_path: Path) -> None:
        """A second write replaces the first; the parent is created."""
        path = tmp_path / "a" / "b" / "checkpoint.json"
        checkpoint.write_checkpoint(path, {"iteration": 1})
        checkpoint.write_checkpoint(path, {"iteration": 2})

        assert json.loads(path.read_text(encoding="utf-8")) == {"iteration": 2}
        assert sorted(p.name for p in path.parent.iterdir()) == ["checkpoint.json"]


class TestBatchSerialization:
    """Reflection batches round-trip, tagging domain trajectories.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_write.py::TestBatchSerialization" -q
        ```
    """

    def test_batch_round_trip_with_mixed_trajectories(self) -> None:
        """Domain, dict, None and other trajectories follow the tagging rule."""
        trajectory = ADKTrajectory(
            tool_calls=(),
            state_deltas=(),
            token_usage=None,
            final_output="o",
            error=None,
        )
        batch = EvaluationBatch(
            outputs=["a", "b", "c", "d"],
            scores=[1.0, 0.0, 0.5, 0.25],
            trajectories=[trajectory, {"k": 1}, None, 42],
            objective_scores=[{"x": 1.0}] * 4,
            metadata=[{"m": i} for i in range(4)],
            inputs=["i0", "i1", "i2", "i3"],
            failed_indices=[1],
        )

        data = json.loads(json.dumps(checkpoint.batch_to_dict(batch)))
        assert data["trajectories"][0]["__type__"] == "ADKTrajectory"
        restored = checkpoint.batch_from_dict(data)

        assert restored is not None
        assert restored.trajectories == [trajectory, {"k": 1}, None, "42"]
        assert restored.outputs == batch.outputs
        assert restored.scores == batch.scores
        assert restored.objective_scores == batch.objective_scores
        assert restored.metadata == batch.metadata
        assert restored.inputs == batch.inputs
        assert restored.failed_indices == [1]

    def test_none_batch(self) -> None:
        """A missing batch stays None both ways."""
        assert checkpoint.batch_to_dict(None) is None
        assert checkpoint.batch_from_dict(None) is None

    def test_rng_state_round_trip(self) -> None:
        """A restored random state draws the same numbers."""
        rng = random.Random(5)
        rng.random()
        data = json.loads(json.dumps(checkpoint.rng_state_to_json(rng.getstate())))
        other = random.Random()
        other.setstate(checkpoint.rng_state_from_json(data))
        assert [other.random() for _ in range(3)] == [rng.random() for _ in range(3)]


class TestRefusals:
    """Refusals name what differs.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_write.py::TestRefusals" -q
        ```
    """

    def test_valset_size_mismatch(self) -> None:
        """A different valset size is refused naming the valset."""
        data = {"initial_candidate_id": "c", "trainset_size": 4, "valset_size": 3}
        with pytest.raises(ConfigurationError, match="valset"):
            checkpoint.check_run_matches(
                data, initial_candidate_id="c", trainset_size=4, valset_size=None
            )

    def test_matching_run_passes(self) -> None:
        """An identical run identity raises nothing."""
        data = {"initial_candidate_id": "c", "trainset_size": 4, "valset_size": None}
        checkpoint.check_run_matches(
            data, initial_candidate_id="c", trainset_size=4, valset_size=None
        )
