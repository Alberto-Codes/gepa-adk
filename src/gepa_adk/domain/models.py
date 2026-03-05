"""Domain models for the gepa-adk evolution engine.

This module contains the core domain models used throughout the evolution
engine, including result types with schema versioning and serialization
support. Configuration validation enforces field constraints and finite-float
checks. All models are dataclasses following hexagonal architecture
principles with no runtime dependencies beyond structlog and the Python standard library.

Terminology:
    - **component**: An evolvable unit with a name and text (e.g., instruction)
    - **component_text**: The current text content of a component being evolved
    - **trial**: One performance record {feedback, trajectory}
    - **feedback**: Critic evaluation {score, feedback_text, feedback_*} (stochastic)
    - **trajectory**: Execution record {input, output, trace} (deterministic)

Attributes:
    EvolutionConfig (class): Configuration parameters for evolution runs.
    IterationRecord (class): Immutable record of a single iteration.
    EvolutionResult (class): Immutable outcome of a completed evolution run.
    Candidate (class): Mutable candidate holding components being evolved.
    CURRENT_SCHEMA_VERSION (int): Current result schema version constant.

Examples:
    Creating configuration and result objects:

    ```python
    from gepa_adk.domain.models import EvolutionConfig, EvolutionResult

    config = EvolutionConfig(max_iterations=20)
    result = EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "Be helpful"},
        iteration_history=[],
        total_iterations=10,
    )
    assert result.schema_version == 1
    ```

    Serializing and deserializing results:

    ```python
    import json
    from gepa_adk.domain.models import EvolutionResult

    data = result.to_dict()
    json_str = json.dumps(data)
    restored = EvolutionResult.from_dict(json.loads(json_str))
    ```

    Display methods for inspecting results:

    ```python
    from gepa_adk.domain.models import EvolutionResult

    result = EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "Be helpful and concise"},
        original_components={"instruction": "Be helpful"},
        iteration_history=[],
        total_iterations=10,
    )
    print(repr(result))  # narrative summary with improvement %
    print(result.show_diff())  # unified diff of component changes
    ```

See Also:
    - [`gepa_adk.domain.types`][gepa_adk.domain.types]: Type aliases and
      enums (Score, StopReason, FrontierType) used by these models.
    - [`gepa_adk.ports.evolution_result`][gepa_adk.ports.evolution_result]:
      Protocol that EvolutionResult and MultiAgentEvolutionResult satisfy.

Note:
    These models are pure data containers with validation logic. They have
    no knowledge of infrastructure concerns like databases or APIs.
"""

import difflib
import html as html_mod
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import structlog

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.types import FrontierType, StopReason

if TYPE_CHECKING:
    from gepa_adk.ports.stopper import StopperProtocol

logger = structlog.get_logger(__name__)

CURRENT_SCHEMA_VERSION = 1
"""Schema version for evolution result serialization.

Incremented when the result schema changes in a way that requires
migration logic in ``from_dict()``.
"""


def _migrate_result_dict(data: dict[str, Any], *, from_version: int) -> dict[str, Any]:
    """Migrate a serialized result dict to the current schema version.

    Applies per-version migration steps sequentially. Currently a no-op
    for v1 (the only version). Future versions add migration functions:
    ``_migrate_v1_to_v2()``, ``_migrate_v2_to_v3()``, etc.

    Args:
        data: Serialized result dict (will not be mutated).
        from_version: The schema_version of the input data.

    Returns:
        Dict with schema_version set to CURRENT_SCHEMA_VERSION.
    """
    migrated = dict(data)  # shallow copy
    # Future: if from_version < 2: migrated = _migrate_v1_to_v2(migrated)
    migrated["schema_version"] = CURRENT_SCHEMA_VERSION
    return migrated


@dataclass(slots=True, frozen=True)
class VideoFileInfo:
    """Metadata for a validated video file.

    This is an immutable record containing validated metadata about a video
    file. Created by VideoBlobService.validate_video_file() after checking
    that the file exists, is within size limits, and has a valid MIME type.

    Attributes:
        path (str): Absolute path to the video file.
        size_bytes (int): File size in bytes.
        mime_type (str): MIME type of the video (e.g., "video/mp4").

    Examples:
        Creating video file info:

        ```python
        from gepa_adk.domain.models import VideoFileInfo

        info = VideoFileInfo(
            path="/data/video.mp4",
            size_bytes=1024000,
            mime_type="video/mp4",
        )
        print(f"File: {info.path}, Size: {info.size_bytes}, Type: {info.mime_type}")
        ```

    Note:
        A frozen dataclass ensuring immutability after validation.
        Instances cannot be modified once created, guaranteeing
        consistency of validated file metadata.
    """

    path: str
    size_bytes: int
    mime_type: str


@dataclass(slots=True, kw_only=True)
class EvolutionConfig:
    """Configuration parameters for an evolution run.

    Defines the parameters that control how evolution proceeds, including
    iteration limits, concurrency settings, and stopping criteria.

    Attributes:
        max_iterations (int): Maximum number of evolution iterations. 0 means
            just evaluate baseline without evolving.
        max_concurrent_evals (int): Number of concurrent batch evaluations.
            Must be at least 1.
        min_improvement_threshold (float): Minimum score improvement to accept
            a new candidate. Set to 0.0 to accept any improvement.
        patience (int): Number of iterations without improvement before stopping
            early. Set to 0 to disable early stopping.
        reflection_model (str): Model identifier for reflection/mutation
            operations.
        frontier_type (FrontierType): Frontier tracking strategy for Pareto
            selection (default: INSTANCE).
        acceptance_metric (Literal["sum", "mean"]): Aggregation method for
            acceptance decisions on iteration evaluation batches. "sum" uses
            sum of scores (default, aligns with upstream GEPA). "mean" uses
            mean of scores (legacy behavior).
        use_merge (bool): Enable merge proposals for genetic crossover.
            Defaults to False.
        max_merge_invocations (int): Maximum number of merge attempts per run.
            Defaults to 10. Must be non-negative.
        reflection_prompt (str | None): Custom reflection/mutation prompt template.
            If provided, this template is used instead of the default when the
            reflection model proposes improved text. Required placeholders:
            - {component_text}: The current component text being evolved
            - {trials}: Trial data with feedback and trajectory for each test case
            If None or empty string, the default prompt template is used.
        stop_callbacks (list[StopperProtocol]): List of stopper callbacks for
            custom stop conditions. Each callback receives a StopperState and
            returns True to signal stop. Defaults to an empty list.
        seed (int | None): Random seed for deterministic engine decisions.
            When set, a seeded ``random.Random`` is created and shared across
            all stochastic components (candidate selector, merge proposer).
            ``None`` (default) preserves current random behavior.

    Examples:
        Creating a configuration with defaults:

        ```python
        from gepa_adk.domain.models import EvolutionConfig

        config = EvolutionConfig(max_iterations=100, patience=10)
        print(config.max_iterations)  # 100
        print(config.reflection_model)  # ollama_chat/gpt-oss:20b
        ```

    Note:
        All numeric parameters are validated in __post_init__ to ensure
        they meet their constraints. Cross-field consistency is also checked
        (e.g., use_merge requires max_merge_invocations > 0, stop_callbacks
        must be callable). Invalid values raise ConfigurationError.

        Determinism applies to engine decisions only (candidate selection,
        component selection, merge proposals). LLM inference is inherently
        stochastic and not covered by the seed guarantee.
    """

    max_iterations: int = 50
    max_concurrent_evals: int = 5
    min_improvement_threshold: float = 0.01
    patience: int = 5
    reflection_model: str = "ollama_chat/gpt-oss:20b"
    frontier_type: FrontierType = FrontierType.INSTANCE
    acceptance_metric: Literal["sum", "mean"] = "sum"
    use_merge: bool = False
    max_merge_invocations: int = 10
    reflection_prompt: str | None = None
    stop_callbacks: list["StopperProtocol"] = field(default_factory=list)
    seed: int | None = None

    def __post_init__(self) -> None:
        """Validate configuration parameters after initialization.

        Raises:
            ConfigurationError: If any parameter violates its constraints,
                including non-finite floats (NaN, Inf), cross-field consistency
                rules (e.g., use_merge requires max_merge_invocations > 0,
                stop_callbacks must be callable).

        Note:
            Operates automatically after dataclass __init__ completes. Validates
            all fields including finite-float checks, cross-field consistency,
            and raises ConfigurationError with context on failure.
        """
        if self.max_iterations < 0:
            raise ConfigurationError(
                "max_iterations must be non-negative",
                field="max_iterations",
                value=self.max_iterations,
                constraint=">= 0",
            )

        if self.max_concurrent_evals < 1:
            raise ConfigurationError(
                "max_concurrent_evals must be at least 1",
                field="max_concurrent_evals",
                value=self.max_concurrent_evals,
                constraint=">= 1",
            )

        if not math.isfinite(self.min_improvement_threshold):
            raise ConfigurationError(
                "min_improvement_threshold must be a finite number",
                field="min_improvement_threshold",
                value=self.min_improvement_threshold,
                constraint="finite float",
            )

        if self.min_improvement_threshold < 0.0:
            raise ConfigurationError(
                "min_improvement_threshold must be non-negative",
                field="min_improvement_threshold",
                value=self.min_improvement_threshold,
                constraint=">= 0.0",
            )

        if self.patience < 0:
            raise ConfigurationError(
                "patience must be non-negative",
                field="patience",
                value=self.patience,
                constraint=">= 0",
            )

        if not self.reflection_model:
            raise ConfigurationError(
                "reflection_model must be a non-empty string",
                field="reflection_model",
                value=self.reflection_model,
                constraint="non-empty string",
            )

        if not isinstance(self.frontier_type, FrontierType):
            try:
                self.frontier_type = FrontierType(self.frontier_type)
            except ValueError as exc:
                raise ConfigurationError(
                    "frontier_type must be a supported FrontierType value",
                    field="frontier_type",
                    value=self.frontier_type,
                    constraint=", ".join(t.value for t in FrontierType),
                ) from exc

        if self.acceptance_metric not in ("sum", "mean"):
            raise ConfigurationError(
                "acceptance_metric must be 'sum' or 'mean'",
                field="acceptance_metric",
                value=self.acceptance_metric,
                constraint="sum|mean",
            )

        if self.max_merge_invocations < 0:
            raise ConfigurationError(
                "max_merge_invocations must be non-negative",
                field="max_merge_invocations",
                value=self.max_merge_invocations,
                constraint=">= 0",
            )

        # Cross-field consistency checks
        self._validate_consistency()

        # Validate reflection_prompt if provided
        self._validate_reflection_prompt()

    def _validate_consistency(self) -> None:
        """Validate cross-field consistency rules.

        Raises:
            ConfigurationError: If use_merge is True but max_merge_invocations
                is zero, or if stop_callbacks contains non-callable items.

        Note:
            Hard errors raise ConfigurationError; soft issues log warnings.
            Called from __post_init__ after individual field validation.
        """
        if self.use_merge and self.max_merge_invocations == 0:
            raise ConfigurationError(
                "use_merge=True requires max_merge_invocations > 0",
                field="max_merge_invocations",
                value=self.max_merge_invocations,
                constraint="> 0 when use_merge=True",
            )

        if (
            self.patience > 0
            and self.max_iterations > 0
            and self.patience > self.max_iterations
        ):
            logger.warning(
                "config.patience.exceeds_max_iterations",
                patience=self.patience,
                max_iterations=self.max_iterations,
                message="patience exceeds max_iterations; early stopping will never trigger",
            )

        for i, callback in enumerate(self.stop_callbacks):
            if not callable(callback):
                raise ConfigurationError(
                    f"stop_callbacks[{i}] is not callable",
                    field=f"stop_callbacks[{i}]",
                    value=type(callback).__name__,
                    constraint="must be callable",
                )

    def _validate_reflection_prompt(self) -> None:
        """Validate reflection_prompt and handle empty string.

        Converts empty string to None with info log. Warns if required
        placeholders are missing but allows the config to be created.

        Note:
            Soft validation approach - missing placeholders trigger warnings
            but don't prevent config creation for maximum flexibility.
        """
        # Handle empty string as "use default"
        if self.reflection_prompt == "":
            logger.info(
                "config.reflection_prompt.empty",
                message="Empty reflection_prompt provided, using default template",
            )
            # Use object.__setattr__ because slots=True prevents direct assignment
            object.__setattr__(self, "reflection_prompt", None)
            return

        # Skip validation if None
        if self.reflection_prompt is None:
            return

        # Warn about missing placeholders
        if "{component_text}" not in self.reflection_prompt:
            logger.warning(
                "config.reflection_prompt.missing_placeholder",
                placeholder="component_text",
                message="reflection_prompt is missing {component_text} placeholder",
            )

        if "{trials}" not in self.reflection_prompt:
            logger.warning(
                "config.reflection_prompt.missing_placeholder",
                placeholder="trials",
                message="reflection_prompt is missing {trials} placeholder",
            )


@dataclass(slots=True, frozen=True, kw_only=True)
class IterationRecord:
    """Captures metrics for a single evolution iteration.

    This is an immutable record of what happened during one iteration
    of the evolution process. Records are created by the engine and
    stored in EvolutionResult.iteration_history.

    Attributes:
        iteration_number (int): 1-indexed iteration number for human
            readability.
        score (float): Score achieved in this iteration (typically in
            [0.0, 1.0]).
        component_text (str): The component_text that was evaluated in this
            iteration (e.g., the instruction text for the "instruction" component).
        evolved_component (str): The name of the component that was evolved
            in this iteration (e.g., "instruction", "output_schema"). Used for
            tracking which component changed in round-robin evolution strategies.
        accepted (bool): Whether this proposal was accepted as the new best.
        objective_scores (list[dict[str, float]] | None): Optional per-example
            multi-objective scores from the valset evaluation. None when adapter
            does not provide objective scores. Each dict maps objective name to
            score value. Index-aligned with evaluation batch examples.

    Examples:
        Creating an iteration record:

        ```python
        from gepa_adk.domain.models import IterationRecord

        record = IterationRecord(
            iteration_number=1,
            score=0.85,
            component_text="Be helpful",
            evolved_component="instruction",
            accepted=True,
        )
        print(record.score)  # 0.85
        print(record.evolved_component)  # "instruction"
        print(record.accepted)  # True
        ```

        Serialization round-trip:

        ```python
        d = record.to_dict()
        restored = IterationRecord.from_dict(d)
        assert restored.score == record.score
        ```

    Note:
        An immutable record that captures iteration metrics. Once created,
        IterationRecord instances cannot be modified, ensuring historical
        accuracy of the evolution trace.
    """

    iteration_number: int
    score: float
    component_text: str
    evolved_component: str
    accepted: bool
    objective_scores: list[dict[str, float]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this record to a stdlib-only dict.

        Returns:
            Dict containing all 6 fields. Output is directly
            ``json.dumps()``-compatible.
        """
        return {
            "iteration_number": self.iteration_number,
            "score": self.score,
            "component_text": self.component_text,
            "evolved_component": self.evolved_component,
            "accepted": self.accepted,
            "objective_scores": self.objective_scores,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IterationRecord":
        """Reconstruct an IterationRecord from a dict.

        Unknown keys are silently ignored for forward compatibility,
        allowing older code to load records produced by newer versions.

        Args:
            data: Dict containing iteration record fields.

        Returns:
            Reconstructed IterationRecord instance.

        Raises:
            KeyError: If a required field is missing from the dict.
        """
        return cls(
            iteration_number=data["iteration_number"],
            score=data["score"],
            component_text=data["component_text"],
            evolved_component=data["evolved_component"],
            accepted=data["accepted"],
            objective_scores=data.get("objective_scores"),
        )


def _truncate(text: str, max_len: int = 80) -> str:
    """Collapse multi-line text to single line and truncate.

    Args:
        text: Text to truncate.
        max_len: Maximum length before truncation.

    Returns:
        Single-line text, truncated with ``...`` if exceeding max_len.
    """
    single_line = text.replace("\n", " ")
    if len(single_line) <= max_len:
        return single_line
    return single_line[: max_len - 3] + "..."


def _build_diff(
    evolved_components: dict[str, str],
    original_components: dict[str, str],
) -> str:
    """Build unified diff output for component changes.

    Args:
        evolved_components: Final evolved component values.
        original_components: Original component values before evolution.

    Returns:
        Unified diff string for all changed components, or
        ``"No changes detected."`` if nothing changed.
    """
    # Invariant: the engine never removes component keys during evolution,
    # so evolved_components always contains all original keys.  Only new or
    # changed components produce diff output.
    diffs: list[str] = []
    for key, evolved_val in evolved_components.items():
        original_val = original_components.get(key)
        if original_val is None:
            # New component — show as all additions
            added_lines = [f"+{line}" for line in evolved_val.splitlines()]
            section = f"--- /dev/null\n+++ {key} (evolved)\n" + "\n".join(added_lines)
            diffs.append(section)
        elif original_val != evolved_val:
            diff_lines = list(
                difflib.unified_diff(
                    original_val.splitlines(keepends=True),
                    evolved_val.splitlines(keepends=True),
                    fromfile=f"{key} (original)",
                    tofile=f"{key} (evolved)",
                    lineterm="",
                )
            )
            if diff_lines:
                diffs.append("\n".join(diff_lines))
    if not diffs:
        return "No changes detected."
    return "\n\n".join(diffs)


@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    """Outcome of a completed evolution run.

    Contains the final results after evolution completes, including
    all evolved component values, performance metrics, and full history.

    Attributes:
        schema_version (int): Schema version for forward-compatible serialization.
            Always ``CURRENT_SCHEMA_VERSION`` for newly created results.
        stop_reason (StopReason): Why the evolution run terminated. Defaults to
            ``StopReason.COMPLETED``.
        original_score (float): Starting performance score (baseline).
        final_score (float): Ending performance score (best achieved).
        evolved_components (dict[str, str]): Dictionary mapping component names
            to their final evolved text values. Keys include "instruction" and
            optionally "output_schema" or other components. Access individual
            components via ``result.evolved_components["instruction"]``.
        iteration_history (list[IterationRecord]): Chronological list of
            iteration records.
        total_iterations (int): Number of iterations performed.
        valset_score (float | None): Score on validation set used for
            acceptance decisions. None if no validation set was used.
        trainset_score (float | None): Score on trainset used for reflection
            diagnostics. None if not computed.
        objective_scores (list[dict[str, float]] | None): Optional per-example
            multi-objective scores from the best candidate's final evaluation.
            None when no objective scores were tracked. Each dict maps objective
            name to score value. Index-aligned with evaluation batch examples.
        original_components (dict[str, str] | None): Optional snapshot of
            pre-evolution component values. When present, enables zero-arg
            ``show_diff()`` calls. None for results created before this field
            was added or when originals were not captured.

    Examples:
        Creating and analyzing a result:

        ```python
        from gepa_adk.domain.models import EvolutionResult, IterationRecord

        result = EvolutionResult(
            original_score=0.60,
            final_score=0.85,
            evolved_components={"instruction": "Be helpful and concise"},
            original_components={"instruction": "Be helpful"},
            iteration_history=[],
            total_iterations=10,
        )
        print(result.improvement)  # 0.25
        print(result.show_diff())  # unified diff of instruction changes
        ```

        Serialization round-trip:

        ```python
        import json

        d = result.to_dict()
        json_str = json.dumps(d)
        restored = EvolutionResult.from_dict(json.loads(json_str))
        ```

    Note:
        As a frozen dataclass, EvolutionResult instances cannot be modified.
    """

    schema_version: int = CURRENT_SCHEMA_VERSION
    stop_reason: StopReason = StopReason.COMPLETED
    original_score: float
    final_score: float
    evolved_components: dict[str, str]
    iteration_history: list[IterationRecord]
    total_iterations: int
    valset_score: float | None = None
    trainset_score: float | None = None
    objective_scores: list[dict[str, float]] | None = None
    original_components: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this result to a stdlib-only dict.

        Returns:
            Dict containing all fields. ``stop_reason`` is serialized
            as its string value. ``iteration_history`` is serialized as a
            list of dicts. Output is directly ``json.dumps()``-compatible.
        """
        return {
            "schema_version": self.schema_version,
            "stop_reason": self.stop_reason.value,
            "original_score": self.original_score,
            "final_score": self.final_score,
            "evolved_components": self.evolved_components,
            "iteration_history": [r.to_dict() for r in self.iteration_history],
            "total_iterations": self.total_iterations,
            "valset_score": self.valset_score,
            "trainset_score": self.trainset_score,
            "objective_scores": self.objective_scores,
            "original_components": self.original_components,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvolutionResult":
        """Reconstruct an EvolutionResult from a dict.

        Validates schema version, applies migration if needed, and
        reconstructs all nested objects including optional
        original_components.

        Args:
            data: Dict containing evolution result fields.

        Returns:
            Reconstructed EvolutionResult instance.

        Raises:
            ConfigurationError: If ``schema_version`` exceeds the current
                version or ``stop_reason`` is not a valid enum value.
            KeyError: If a required field is missing from the dict.
        """
        version = data.get("schema_version", 1)
        if version > CURRENT_SCHEMA_VERSION:
            raise ConfigurationError(
                f"Cannot deserialize result with schema_version {version} "
                f"(current version is {CURRENT_SCHEMA_VERSION}). "
                f"Upgrade gepa-adk to load this result.",
                field="schema_version",
                value=version,
                constraint=f"<= {CURRENT_SCHEMA_VERSION}",
            )
        migrated = _migrate_result_dict(data, from_version=version)
        try:
            stop_reason = StopReason(migrated.get("stop_reason", "completed"))
        except ValueError:
            raw = migrated.get("stop_reason")
            raise ConfigurationError(
                f"Invalid stop_reason value: {raw!r}",
                field="stop_reason",
                value=raw,
                constraint=("one of: " + ", ".join(sr.value for sr in StopReason)),
            ) from None
        return cls(
            schema_version=migrated["schema_version"],
            stop_reason=stop_reason,
            original_score=migrated["original_score"],
            final_score=migrated["final_score"],
            evolved_components=migrated["evolved_components"],
            iteration_history=[
                IterationRecord.from_dict(r)
                for r in migrated.get("iteration_history", [])
            ],
            total_iterations=migrated["total_iterations"],
            valset_score=migrated.get("valset_score"),
            trainset_score=migrated.get("trainset_score"),
            objective_scores=migrated.get("objective_scores"),
            original_components=migrated.get("original_components"),
        )

    @property
    def improvement(self) -> float:
        """Calculate the score improvement from original to final.

        Returns:
            The difference between final_score and original_score.
            Positive values indicate improvement, negative indicates degradation.

        Note:
            Override is not needed since frozen dataclasses support properties.
        """
        return self.final_score - self.original_score

    @property
    def improved(self) -> bool:
        """Check if the final score is better than the original.

        Returns:
            True if final_score > original_score, False otherwise.

        Note:
            Only returns True for strict improvement, not equal scores.
        """
        return self.final_score > self.original_score

    def __repr__(self) -> str:
        """Narrative summary of the evolution result.

        Returns:
            Human-readable multi-line summary with improvement percentage,
            iterations, stop reason, component names, and acceptance rate.
            Uses 2-space indent, no box-drawing characters, every line
            greppable.
        """
        if abs(self.original_score) < 1e-9:
            imp_str = f"{self.improvement:+.4f} improvement"
        else:
            pct = self.improvement * 100 / abs(self.original_score)
            sign = "+" if pct > 0 else ""
            imp_str = f"{sign}{pct:.1f}% improvement"
        lines = [
            f"EvolutionResult: {imp_str} "
            f"({self.original_score:.2f} \u2192 {self.final_score:.2f})",
            f"  iterations: {self.total_iterations}, "
            f"stop_reason: {self.stop_reason.value}",
            f"  components: {', '.join(sorted(self.evolved_components))}",
        ]
        if self.total_iterations > 0:
            accepted = sum(1 for r in self.iteration_history if r.accepted)
            lines.append(f"  acceptance_rate: {accepted}/{self.total_iterations}")
        return "\n".join(lines)

    def show_diff(self, original_components: dict[str, str] | None = None) -> str:
        """Show unified diff between original and evolved components.

        Uses stored ``original_components`` if no explicit argument is
        provided. Produces git-diff-style output (``---``/``+++``/``@@``)
        for each component that changed.

        Args:
            original_components: Pre-evolution component values. If None,
                falls back to ``self.original_components``.

        Returns:
            Unified diff string, or ``"No changes detected."`` if all
            components are identical.

        Raises:
            ValueError: If both the argument and ``self.original_components``
                are None.
        """
        originals = (
            original_components
            if original_components is not None
            else self.original_components
        )
        if originals is None:
            raise ValueError(
                "No original components available. "
                "Pass original_components or use a result that stores them."
            )
        return _build_diff(self.evolved_components, originals)

    def _repr_html_(self) -> str:
        """Render an HTML summary for Jupyter notebooks.

        Returns:
            HTML string with summary and components tables. Uses semantic
            ``<th>`` header elements and inline CSS for portability across
            JupyterLab, Colab, and VS Code. Iteration history is wrapped
            in a collapsible ``<details>``/``<summary>`` block.
        """
        if abs(self.original_score) < 1e-9:
            imp_html = f"{self.improvement:+.4f}"
        else:
            pct = self.improvement * 100 / abs(self.original_score)
            sign = "+" if pct > 0 else ""
            imp_html = f"{sign}{pct:.1f}%"
        style = (
            'style="border-collapse:collapse;'
            "font-family:monospace;font-size:13px;"
            'margin:8px 0"'
        )
        td = 'style="padding:4px 12px;border:1px solid #ddd"'
        th = 'style="padding:4px 12px;border:1px solid #ddd;background:#f5f5f5"'

        rows = [
            f"<tr><th {th}>Improvement</th><td {td}>{imp_html}</td></tr>",
            f"<tr><th {th}>Original Score</th>"
            f"<td {td}>{self.original_score:.4f}</td></tr>",
            f"<tr><th {th}>Final Score</th><td {td}>{self.final_score:.4f}</td></tr>",
            f"<tr><th {th}>Iterations</th><td {td}>{self.total_iterations}</td></tr>",
            f"<tr><th {th}>Stop Reason</th>"
            f"<td {td}>{html_mod.escape(self.stop_reason.value)}</td></tr>",
        ]
        summary_table = f"<table {style}>{''.join(rows)}</table>"

        comp_rows = []
        for name in sorted(self.evolved_components):
            val = html_mod.escape(_truncate(self.evolved_components[name], 200))
            comp_rows.append(
                f"<tr><td {td}>{html_mod.escape(name)}</td><td {td}>{val}</td></tr>"
            )
        comp_header = f"<tr><th {th}>Component</th><th {th}>Evolved Value</th></tr>"
        comp_table = f"<table {style}>{comp_header}{''.join(comp_rows)}</table>"

        history_rows = []
        for rec in self.iteration_history:
            accepted_mark = "\u2713" if rec.accepted else ""
            history_rows.append(
                f"<tr><td {td}>{rec.iteration_number}</td>"
                f"<td {td}>{rec.score:.4f}</td>"
                f"<td {td}>{html_mod.escape(rec.evolved_component)}</td>"
                f"<td {td}>{accepted_mark}</td></tr>"
            )
        history_header = (
            f"<tr><th {th}>#</th><th {th}>Score</th>"
            f"<th {th}>Component</th><th {th}>Accepted</th></tr>"
        )
        history_table = (
            f"<table {style}>{history_header}{''.join(history_rows)}</table>"
        )
        history_section = (
            "<details><summary>Iteration History "
            f"({len(self.iteration_history)} records)</summary>"
            f"{history_table}</details>"
        )

        return (
            "<div>"
            "<strong>EvolutionResult</strong>"
            f"{summary_table}{comp_table}{history_section}"
            "</div>"
        )


@dataclass(slots=True, kw_only=True)
class Candidate:
    """Represents an instruction candidate being evolved.

    Unlike GEPA's simple `dict[str, str]` type alias, this class provides
    richer state tracking for async scenarios including lineage and metadata.

    Attributes:
        components (dict[str, str]): Component name to text value mapping.
            Common keys include 'instruction' (main agent prompt) and
            'output_schema'.
        generation (int): Generation number in the evolution lineage
            (0 = initial).
        parent_id (str | None): ID of the parent candidate for lineage
            tracking (legacy field, retained for compatibility).
        parent_ids (list[int] | None): Multi-parent indices for merge operations.
            None for seed candidates, [single_idx] for mutations, [idx1, idx2] for merges.
        metadata (dict[str, Any]): Extensible metadata dict for async tracking
            and debugging.

    Examples:
        Creating a candidate:

        ```python
        from gepa_adk.domain.models import Candidate

        candidate = Candidate(
            components={"instruction": "Be helpful"},
            generation=0,
        )
        print(candidate.components["instruction"])  # Be helpful
        print(candidate.generation)  # 0
        ```

    Note:
        A mutable candidate representation with richer state tracking than
        GEPA's simple dict. Components and metadata can be modified during
        the evolution process. Use generation and parent_id to track lineage.
    """

    components: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    parent_id: str | None = None
    parent_ids: list[int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True, kw_only=True)
class MultiAgentEvolutionResult:
    """Outcome of a completed multi-agent evolution run.

    Contains evolved component_text for all agents in the group,
    along with performance metrics and evolution history.

    Attributes:
        schema_version (int): Schema version for forward-compatible serialization.
        stop_reason (StopReason): Why the evolution run terminated.
        evolved_components (dict[str, str]): Mapping of agent name to evolved
            component_text.
        original_score (float): Starting performance score (baseline).
        final_score (float): Ending performance score (best achieved).
        primary_agent (str): Name of the agent whose output was used for scoring.
        iteration_history (list[IterationRecord]): Chronological list of iteration records.
        total_iterations (int): Number of iterations performed.
        original_components (dict[str, str] | None): Optional snapshot of
            pre-evolution component values. When present, enables zero-arg
            ``show_diff()`` calls. None for results created before this field
            was added or when originals were not captured.

    Examples:
        Creating and analyzing a multi-agent result:

        ```python
        from gepa_adk.domain.models import MultiAgentEvolutionResult, IterationRecord

        result = MultiAgentEvolutionResult(
            evolved_components={
                "generator": "Generate high-quality code",
                "critic": "Review code thoroughly",
            },
            original_components={
                "generator": "Generate code",
                "critic": "Review code",
            },
            original_score=0.60,
            final_score=0.85,
            primary_agent="generator",
            iteration_history=[],
            total_iterations=10,
        )
        print(result.improvement)  # 0.25
        print(result.show_diff())  # unified diff of component changes
        print(result.agent_names)  # ["critic", "generator"]
        assert result.schema_version == 1
        ```

        Serialization round-trip:

        ```python
        import json

        d = result.to_dict()
        restored = MultiAgentEvolutionResult.from_dict(json.loads(json.dumps(d)))
        ```

    Note:
        An immutable result container for multi-agent evolution. Once created,
        MultiAgentEvolutionResult instances cannot be modified. Use computed
        properties like `improvement`, `improved`, and `agent_names` to analyze
        results without modifying the underlying data.
    """

    schema_version: int = CURRENT_SCHEMA_VERSION
    stop_reason: StopReason = StopReason.COMPLETED
    evolved_components: dict[str, str]
    original_score: float
    final_score: float
    primary_agent: str
    iteration_history: list[IterationRecord]
    total_iterations: int
    original_components: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize this result to a stdlib-only dict.

        Returns:
            Dict containing all 9 fields. ``stop_reason`` is serialized
            as its string value. ``iteration_history`` is serialized as a
            list of dicts. Output is directly ``json.dumps()``-compatible.
        """
        return {
            "schema_version": self.schema_version,
            "stop_reason": self.stop_reason.value,
            "evolved_components": self.evolved_components,
            "original_score": self.original_score,
            "final_score": self.final_score,
            "primary_agent": self.primary_agent,
            "iteration_history": [r.to_dict() for r in self.iteration_history],
            "total_iterations": self.total_iterations,
            "original_components": self.original_components,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MultiAgentEvolutionResult":
        """Reconstruct a MultiAgentEvolutionResult from a dict.

        Validates schema version, applies migration if needed, and
        reconstructs all nested objects including optional
        original_components.

        Args:
            data: Dict containing multi-agent evolution result fields.

        Returns:
            Reconstructed MultiAgentEvolutionResult instance.

        Raises:
            ConfigurationError: If ``schema_version`` exceeds the current
                version or ``stop_reason`` is not a valid enum value.
            KeyError: If a required field is missing from the dict.
        """
        version = data.get("schema_version", 1)
        if version > CURRENT_SCHEMA_VERSION:
            raise ConfigurationError(
                f"Cannot deserialize result with schema_version {version} "
                f"(current version is {CURRENT_SCHEMA_VERSION}). "
                f"Upgrade gepa-adk to load this result.",
                field="schema_version",
                value=version,
                constraint=f"<= {CURRENT_SCHEMA_VERSION}",
            )
        migrated = _migrate_result_dict(data, from_version=version)
        try:
            stop_reason = StopReason(migrated.get("stop_reason", "completed"))
        except ValueError:
            raw = migrated.get("stop_reason")
            raise ConfigurationError(
                f"Invalid stop_reason value: {raw!r}",
                field="stop_reason",
                value=raw,
                constraint=("one of: " + ", ".join(sr.value for sr in StopReason)),
            ) from None
        return cls(
            schema_version=migrated["schema_version"],
            stop_reason=stop_reason,
            evolved_components=migrated["evolved_components"],
            original_score=migrated["original_score"],
            final_score=migrated["final_score"],
            primary_agent=migrated["primary_agent"],
            iteration_history=[
                IterationRecord.from_dict(r)
                for r in migrated.get("iteration_history", [])
            ],
            total_iterations=migrated["total_iterations"],
            original_components=migrated.get("original_components"),
        )

    @property
    def improvement(self) -> float:
        """Calculate the score improvement from original to final.

        Returns:
            The difference between final_score and original_score.
            Positive values indicate improvement, negative indicates degradation.

        Note:
            Override is not needed since frozen dataclasses support properties.
        """
        return self.final_score - self.original_score

    @property
    def improved(self) -> bool:
        """Check if the final score is better than the original.

        Returns:
            True if final_score > original_score, False otherwise.

        Note:
            Only returns True for strict improvement, not equal scores.
        """
        return self.final_score > self.original_score

    @property
    def agent_names(self) -> list[str]:
        """Get sorted list of evolved agent names.

        Returns:
            Sorted list of agent names from evolved_components keys.

        Note:
            Outputs a new list each time, sorted alphabetically for
            consistent ordering regardless of insertion order.
        """
        return sorted(self.evolved_components.keys())

    def __repr__(self) -> str:
        """Narrative summary of the multi-agent evolution result.

        Returns:
            Human-readable multi-line summary with improvement percentage,
            iterations, stop reason, primary agent, agent names, and
            acceptance rate. Uses 2-space indent, no box-drawing characters,
            every line greppable.
        """
        if abs(self.original_score) < 1e-9:
            imp_str = f"{self.improvement:+.4f} improvement"
        else:
            pct = self.improvement * 100 / abs(self.original_score)
            sign = "+" if pct > 0 else ""
            imp_str = f"{sign}{pct:.1f}% improvement"
        lines = [
            f"MultiAgentEvolutionResult: {imp_str} "
            f"({self.original_score:.2f} \u2192 {self.final_score:.2f})",
            f"  iterations: {self.total_iterations}, "
            f"stop_reason: {self.stop_reason.value}",
            f"  primary_agent: {self.primary_agent}",
            f"  agents: {', '.join(sorted(self.evolved_components))}",
        ]
        if self.total_iterations > 0:
            accepted = sum(1 for r in self.iteration_history if r.accepted)
            lines.append(f"  acceptance_rate: {accepted}/{self.total_iterations}")
        return "\n".join(lines)

    def show_diff(self, original_components: dict[str, str] | None = None) -> str:
        """Show unified diff between original and evolved components.

        Uses stored ``original_components`` if no explicit argument is
        provided. Produces git-diff-style output (``---``/``+++``/``@@``)
        for each component that changed.

        Args:
            original_components: Pre-evolution component values. If None,
                falls back to ``self.original_components``.

        Returns:
            Unified diff string, or ``"No changes detected."`` if all
            components are identical.

        Raises:
            ValueError: If both the argument and ``self.original_components``
                are None.
        """
        originals = (
            original_components
            if original_components is not None
            else self.original_components
        )
        if originals is None:
            raise ValueError(
                "No original components available. "
                "Pass original_components or use a result that stores them."
            )
        return _build_diff(self.evolved_components, originals)

    def _repr_html_(self) -> str:
        """Render an HTML summary for Jupyter notebooks.

        Returns:
            HTML string with summary and components tables. Uses semantic
            ``<th>`` header elements and inline CSS for portability across
            JupyterLab, Colab, and VS Code. Iteration history is wrapped
            in a collapsible ``<details>``/``<summary>`` block.
        """
        if abs(self.original_score) < 1e-9:
            imp_html = f"{self.improvement:+.4f}"
        else:
            pct = self.improvement * 100 / abs(self.original_score)
            sign = "+" if pct > 0 else ""
            imp_html = f"{sign}{pct:.1f}%"
        style = (
            'style="border-collapse:collapse;'
            "font-family:monospace;font-size:13px;"
            'margin:8px 0"'
        )
        td = 'style="padding:4px 12px;border:1px solid #ddd"'
        th = 'style="padding:4px 12px;border:1px solid #ddd;background:#f5f5f5"'

        rows = [
            f"<tr><th {th}>Improvement</th><td {td}>{imp_html}</td></tr>",
            f"<tr><th {th}>Original Score</th>"
            f"<td {td}>{self.original_score:.4f}</td></tr>",
            f"<tr><th {th}>Final Score</th><td {td}>{self.final_score:.4f}</td></tr>",
            f"<tr><th {th}>Iterations</th><td {td}>{self.total_iterations}</td></tr>",
            f"<tr><th {th}>Stop Reason</th>"
            f"<td {td}>{html_mod.escape(self.stop_reason.value)}</td></tr>",
            f"<tr><th {th}>Primary Agent</th>"
            f"<td {td}>{html_mod.escape(self.primary_agent)}</td></tr>",
        ]
        summary_table = f"<table {style}>{''.join(rows)}</table>"

        comp_rows = []
        for name in sorted(self.evolved_components):
            val = html_mod.escape(_truncate(self.evolved_components[name], 200))
            comp_rows.append(
                f"<tr><td {td}>{html_mod.escape(name)}</td><td {td}>{val}</td></tr>"
            )
        comp_header = f"<tr><th {th}>Agent</th><th {th}>Evolved Value</th></tr>"
        comp_table = f"<table {style}>{comp_header}{''.join(comp_rows)}</table>"

        history_rows = []
        for rec in self.iteration_history:
            accepted_mark = "\u2713" if rec.accepted else ""
            history_rows.append(
                f"<tr><td {td}>{rec.iteration_number}</td>"
                f"<td {td}>{rec.score:.4f}</td>"
                f"<td {td}>{html_mod.escape(rec.evolved_component)}</td>"
                f"<td {td}>{accepted_mark}</td></tr>"
            )
        history_header = (
            f"<tr><th {th}>#</th><th {th}>Score</th>"
            f"<th {th}>Component</th><th {th}>Accepted</th></tr>"
        )
        history_table = (
            f"<table {style}>{history_header}{''.join(history_rows)}</table>"
        )
        history_section = (
            "<details><summary>Iteration History "
            f"({len(self.iteration_history)} records)</summary>"
            f"{history_table}</details>"
        )

        return (
            "<div>"
            "<strong>MultiAgentEvolutionResult</strong>"
            f"{summary_table}{comp_table}{history_section}"
            "</div>"
        )


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "EvolutionConfig",
    "IterationRecord",
    "EvolutionResult",
    "Candidate",
    "MultiAgentEvolutionResult",
    "VideoFileInfo",
]
