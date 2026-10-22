"""Assemble single-agent evaluation results with complete objective metadata.

Notes:
    Scorer dimension dictionaries remain in metadata and are also forwarded
    to objective scores when present for every example. Partial dimensional
    batches fail before reaching Pareto tracking.

Examples:
    Build a scalar-only evaluation batch:

    ```python
    batch = build_evaluation_batch(
        outputs=["answer"],
        scores=[0.8],
        trajectories=None,
        metadata=[{}],
        inputs=["question"],
        failed_indices=[],
    )
    assert batch.objective_scores is None
    ```

See Also:
    [gepa_adk.ports.adapter.EvaluationBatch][]: Ordered evaluation container.
"""

from typing import Any

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.trajectory import ADKTrajectory
from gepa_adk.ports.adapter import EvaluationBatch


def build_evaluation_batch(
    *,
    outputs: list[str],
    scores: list[float],
    trajectories: list[ADKTrajectory] | None,
    metadata: list[dict[str, Any]],
    inputs: list[str],
    failed_indices: list[int],
) -> EvaluationBatch[ADKTrajectory, str]:
    """Build an ordered batch with optional metadata and objective scores.

    Args:
        outputs: Agent outputs in input order.
        scores: Scalar scores aligned with outputs.
        trajectories: Captured trajectories when requested.
        metadata: Scorer metadata aligned with outputs.
        inputs: Original example input strings.
        failed_indices: Indices whose evaluation failed.

    Returns:
        The assembled batch, omitting metadata when every entry is empty.

    Raises:
        ConfigurationError: If only some examples provide non-empty dimensions.
    """
    has_metadata = any(meta and isinstance(meta, dict) for meta in metadata)
    return EvaluationBatch(
        outputs=outputs,
        scores=scores,
        trajectories=trajectories,
        metadata=metadata if has_metadata else None,
        objective_scores=_objective_scores(metadata),
        inputs=inputs,
        failed_indices=failed_indices,
    )


def _objective_scores(
    metadata: list[dict[str, Any]],
) -> list[dict[str, float]] | None:
    """Collect complete per-example dimensions in evaluation order.

    Args:
        metadata: Scorer metadata for every example in the batch.

    Returns:
        Non-empty dimension dictionaries, or None when no example has one.

    Raises:
        ConfigurationError: If an example lacks dimensions while another
            example supplies them.
    """
    dimensions = [
        meta.get("dimension_scores") if isinstance(meta, dict) else None
        for meta in metadata
    ]
    present = [isinstance(value, dict) and bool(value) for value in dimensions]
    if not any(present):
        return None
    if not all(present):
        index = present.index(False)
        raise ConfigurationError(
            f"dimension_scores missing or empty for example {index}",
            field="dimension_scores",
            value=index,
            constraint="non-empty dict required for every example or none",
        )
    return [value for value in dimensions if isinstance(value, dict)]
