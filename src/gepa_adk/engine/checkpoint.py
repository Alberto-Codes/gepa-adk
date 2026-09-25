"""Pure serialisation helpers for engine checkpoints.

The engine writes its own state to one JSON file after the baseline and
after every recorded iteration, and reads it back when ``resume=True``.
This module holds the parts that need no engine: converting evaluation
batches, trajectories and random states to JSON-safe values and back,
writing the file atomically, and refusing a file that does not belong to
the current run.

Attributes:
    CHECKPOINT_VERSION (int): Version written to ``checkpoint_version``.
        A file with any other version is refused on resume.
    batch_to_dict (function): Serialise an ``EvaluationBatch``.
    batch_from_dict (function): Rebuild an ``EvaluationBatch``.
    rng_state_to_json (function): Serialise a ``random.Random`` state.
    rng_state_from_json (function): Rebuild a ``random.Random`` state.
    write_checkpoint (function): Write a checkpoint dict atomically.
    read_checkpoint (function): Read a checkpoint and check its version.
    check_run_matches (function): Refuse a checkpoint from a different run.

Examples:
    Writing and reading a checkpoint:

    ```python
    from pathlib import Path

    from gepa_adk.engine.checkpoint import read_checkpoint, write_checkpoint

    path = Path("runs/checkpoint.json")
    write_checkpoint(path, {"checkpoint_version": 1, "iteration": 3})
    data = read_checkpoint(path)
    assert data["iteration"] == 3
    ```

See Also:
    - [`gepa_adk.engine.async_engine`][gepa_adk.engine.async_engine]: The
      engine that builds the checkpoint dict and restores from it.
    - [`gepa_adk.domain.trajectory`][gepa_adk.domain.trajectory]: Trajectory
      types whose ``to_dict()`` output is stored in the reflection batch.

Notes:
    Pareto state, genealogy and merge-proposer random state are not
    serialised; the engine refuses a checkpoint path together with a
    candidate selector.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.trajectory import ADKTrajectory, MultiAgentTrajectory
from gepa_adk.ports.adapter import EvaluationBatch

CHECKPOINT_VERSION = 1

_TRAJECTORY_TYPES: dict[str, type[ADKTrajectory] | type[MultiAgentTrajectory]] = {
    "ADKTrajectory": ADKTrajectory,
    "MultiAgentTrajectory": MultiAgentTrajectory,
}


def _trajectory_to_json(trajectory: Any) -> Any:
    """Convert one trajectory to a JSON-safe value.

    Args:
        trajectory: A domain trajectory, a dict, None or any other value.

    Returns:
        A domain trajectory's ``to_dict()`` tagged with ``"__type__"``, a
        dict unchanged, None as JSON ``null``, and anything else as its
        ``str()``.
    """
    if isinstance(trajectory, (ADKTrajectory, MultiAgentTrajectory)):
        return {"__type__": type(trajectory).__name__, **trajectory.to_dict()}
    if trajectory is None or isinstance(trajectory, dict):
        return trajectory
    return str(trajectory)


def _trajectory_from_json(value: Any) -> Any:
    """Rebuild one trajectory from its JSON-safe value.

    Args:
        value: Output of ``_trajectory_to_json``.

    Returns:
        The domain trajectory when ``value`` carries a known ``"__type__"``
        tag, otherwise ``value`` unchanged.
    """
    if isinstance(value, dict) and value.get("__type__") in _TRAJECTORY_TYPES:
        fields = {k: v for k, v in value.items() if k != "__type__"}
        return _TRAJECTORY_TYPES[value["__type__"]].from_dict(fields)
    return value


def batch_to_dict(batch: EvaluationBatch | None) -> dict[str, Any] | None:
    """Serialise an evaluation batch for a checkpoint.

    Args:
        batch: The best candidate's reflection batch, or None.

    Returns:
        Dict with ``outputs``, ``scores``, ``inputs``, ``metadata``,
        ``failed_indices``, ``objective_scores`` and ``trajectories``, or
        None when ``batch`` is None. Each trajectory goes through the
        tagging rule of ``_trajectory_to_json``, so a ``None`` entry is
        stored as ``null``. ``outputs`` and ``metadata`` are stored as
        given; a value JSON cannot encode makes the later write raise.

    Examples:
        ```python
        data = batch_to_dict(EvaluationBatch(outputs=["o"], scores=[1.0]))
        assert data["scores"] == [1.0]
        ```
    """
    if batch is None:
        return None
    trajectories = batch.trajectories
    return {
        "outputs": list(batch.outputs),
        "scores": list(batch.scores),
        "inputs": None if batch.inputs is None else list(batch.inputs),
        "metadata": None if batch.metadata is None else list(batch.metadata),
        "failed_indices": (
            None if batch.failed_indices is None else list(batch.failed_indices)
        ),
        "objective_scores": (
            None if batch.objective_scores is None else list(batch.objective_scores)
        ),
        "trajectories": (
            None
            if trajectories is None
            else [_trajectory_to_json(t) for t in trajectories]
        ),
    }


def batch_from_dict(data: dict[str, Any] | None) -> EvaluationBatch | None:
    """Rebuild an evaluation batch from ``batch_to_dict()`` output.

    Args:
        data: Serialised batch, or None.

    Returns:
        The rebuilt batch with tagged trajectories turned back into domain
        trajectories, or None when ``data`` is None.

    Raises:
        KeyError: If ``outputs`` or ``scores`` is missing.

    Examples:
        ```python
        batch = batch_from_dict({"outputs": ["o"], "scores": [1.0]})
        assert batch is not None and batch.outputs == ["o"]
        ```
    """
    if data is None:
        return None
    trajectories = data.get("trajectories")
    return EvaluationBatch(
        outputs=list(data["outputs"]),
        scores=list(data["scores"]),
        trajectories=(
            None
            if trajectories is None
            else [_trajectory_from_json(t) for t in trajectories]
        ),
        objective_scores=data.get("objective_scores"),
        metadata=data.get("metadata"),
        inputs=data.get("inputs"),
        failed_indices=data.get("failed_indices"),
    )


def rng_state_to_json(state: tuple[Any, ...]) -> list[Any]:
    """Convert a ``random.Random.getstate()`` value to JSON-safe lists.

    Args:
        state: The ``(version, internal_state, gauss_next)`` tuple.

    Returns:
        The same three values as a list, with the internal state a list.
    """
    version, internal, gauss_next = state
    return [version, list(internal), gauss_next]


def rng_state_from_json(data: list[Any]) -> tuple[Any, ...]:
    """Rebuild a ``random.Random`` state from ``rng_state_to_json()`` output.

    Args:
        data: The three-item list written to the checkpoint.

    Returns:
        A tuple accepted by ``random.Random.setstate``.
    """
    version, internal, gauss_next = data
    return (version, tuple(internal), gauss_next)


def write_checkpoint(path: Path, data: dict[str, Any]) -> None:
    """Write a checkpoint dict to ``path`` atomically.

    Writes the JSON to ``path.with_name(path.name + ".tmp")`` and then
    replaces ``path`` with it through ``os.replace``, creating the parent
    directory first. A reader sees either the previous file or the new
    one, never a partial write.

    Args:
        path: Checkpoint file to write.
        data: JSON-serialisable checkpoint dict.

    Raises:
        TypeError: If ``data`` holds a value JSON cannot encode.
        OSError: If the directory, the temporary file or the replace fails.
            The temporary file is removed and the previous checkpoint is
            left as it was.

    Examples:
        ```python
        write_checkpoint(Path("runs/checkpoint.json"), {"checkpoint_version": 1})
        ```
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    text = json.dumps(data, ensure_ascii=False)
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def read_checkpoint(path: Path) -> dict[str, Any]:
    """Read a checkpoint file and check its version.

    Args:
        path: Checkpoint file to read.

    Returns:
        The decoded checkpoint dict.

    Raises:
        ConfigurationError: If the file does not exist (the message names
            the path) or its ``checkpoint_version`` is not
            ``CHECKPOINT_VERSION``.
        json.JSONDecodeError: If the file is not valid JSON.

    Examples:
        ```python
        data = read_checkpoint(Path("runs/checkpoint.json"))
        print(data["iteration"])
        ```
    """
    if not path.exists():
        raise ConfigurationError(
            f"resume=True but no checkpoint exists at {path}",
            field="checkpoint_path",
            value=str(path),
            constraint="existing checkpoint file when resume=True",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("checkpoint_version")
    if version != CHECKPOINT_VERSION:
        raise ConfigurationError(
            f"checkpoint at {path} has version {version!r}; this gepa-adk "
            f"reads checkpoint version {CHECKPOINT_VERSION}",
            field="checkpoint_version",
            value=version,
            constraint=f"== {CHECKPOINT_VERSION}",
        )
    return data


def check_run_matches(
    data: dict[str, Any],
    *,
    initial_candidate_id: str,
    trainset_size: int,
    valset_size: int | None,
) -> None:
    """Refuse a checkpoint written by a different run.

    Args:
        data: Checkpoint dict from ``read_checkpoint``.
        initial_candidate_id: ``Candidate.id`` of the engine's initial
            candidate.
        trainset_size: Number of trainset rows the engine was given.
        valset_size: Number of valset rows, or None when the valset is the
            trainset.

    Raises:
        ConfigurationError: If the initial candidate, the trainset size or
            the valset size differs from the checkpoint's.

    Examples:
        ```python
        check_run_matches(
            data, initial_candidate_id="3f2a9c1b0d4e", trainset_size=4, valset_size=None
        )
        ```
    """
    checks = (
        ("initial_candidate_id", "initial candidate", initial_candidate_id),
        ("trainset_size", "trainset size", trainset_size),
        ("valset_size", "valset size", valset_size),
    )
    for key, label, current in checks:
        stored = data.get(key)
        if stored != current:
            raise ConfigurationError(
                f"checkpoint {label} {stored!r} does not match this run's "
                f"{label} {current!r}",
                field=key,
                value=stored,
                constraint=f"== {current!r}",
            )
