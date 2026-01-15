"""Type aliases and configuration types for the domain layer.

This module defines semantic type aliases and configuration dataclasses
used throughout the gepa-adk domain models. These types provide documentation
and clarity without runtime overhead.

Attributes:
    Score (type): Type alias for normalized scores (typically [0.0, 1.0]).
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.
    TrajectoryConfig (class): Configuration for trajectory extraction behavior.
    ProposalResult (class): Result of a successful proposal operation.

Examples:
    Using type aliases for clarity:

    ```python
    from gepa_adk.domain.types import Score, ComponentName

    score: Score = 0.85
    component: ComponentName = "instruction"
    ```

    Configuring trajectory extraction:

    ```python
    from gepa_adk.domain.types import TrajectoryConfig

    config = TrajectoryConfig(
        include_tool_calls=True,
        redact_sensitive=True,
        max_string_length=5000,
    )
    ```

Note:
    Type aliases are lightweight hints that improve code readability
    and IDE support. They do not enforce validation at runtime.
    Configuration types use frozen dataclasses for immutability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeAlias

if TYPE_CHECKING:
    from gepa_adk.domain.models import Candidate

Score: TypeAlias = float
"""Normalized score, typically in [0.0, 1.0]."""

ComponentName: TypeAlias = str
"""Name of a candidate component (e.g., 'instruction', 'output_schema')."""

ModelName: TypeAlias = str
"""Model identifier (e.g., 'gemini-2.0-flash', 'gpt-4o')."""


@dataclass(frozen=True, slots=True)
class TrajectoryConfig:
    """Configuration for trajectory extraction behavior.

    Controls which components are extracted from ADK event streams,
    whether sensitive data should be redacted, and whether large
    values should be truncated.

    Note:
        All configuration fields are immutable after instantiation,
        ensuring consistent extraction behavior throughout evolution.

    Attributes:
        include_tool_calls (bool): Extract tool/function call records.
            Defaults to True.
        include_state_deltas (bool): Extract session state changes.
            Defaults to True.
        include_token_usage (bool): Extract LLM token consumption metrics.
            Defaults to True.
        redact_sensitive (bool): Apply sensitive data redaction. When True,
            fields matching sensitive_keys will be replaced with "[REDACTED]".
            Defaults to True for secure-by-default behavior.
        sensitive_keys (tuple[str, ...]): Field names to redact via exact
            match. Case-sensitive. Defaults to ("password", "api_key", "token").
        max_string_length (int | None): Truncate strings longer than this
            with a marker indicating truncation. None disables truncation.
            Defaults to 10000 characters.

    Examples:
        Default configuration (secure, with truncation):

        ```python
        config = TrajectoryConfig()  # All features enabled, redaction ON
        ```

        Minimal configuration (tool calls only):

        ```python
        config = TrajectoryConfig(
            include_tool_calls=True,
            include_state_deltas=False,
            include_token_usage=False,
            redact_sensitive=False,
        )
        ```

        Custom sensitive keys and truncation:

        ```python
        config = TrajectoryConfig(
            sensitive_keys=("password", "api_key", "token", "ssn"),
            max_string_length=5000,  # Truncate DOM/screenshots earlier
        )
        ```

        Disable truncation (keep full values):

        ```python
        config = TrajectoryConfig(max_string_length=None)
        ```

    Note:
        Redaction takes precedence over truncation. Sensitive values are
        replaced with "[REDACTED]" first, then truncation applies to the
        remaining (non-sensitive) strings.
    """

    include_tool_calls: bool = True
    include_state_deltas: bool = True
    include_token_usage: bool = True
    redact_sensitive: bool = True
    sensitive_keys: tuple[str, ...] = ("password", "api_key", "token")
    max_string_length: int | None = 10000


class FrontierType(str, Enum):
    """Supported frontier tracking strategies for Pareto selection.

    Note:
        All four frontier types enable different Pareto dominance tracking
        strategies for multi-objective optimization.

    Examples:
        ```python
        frontier_type = FrontierType.INSTANCE
        ```
    """

    INSTANCE = "instance"
    OBJECTIVE = "objective"
    HYBRID = "hybrid"
    CARTESIAN = "cartesian"


# Multi-agent candidate: maps "{agent_name}_instruction" -> instruction text
MultiAgentCandidate: TypeAlias = dict[str, str]
"""Type alias for multi-agent candidate structure.

Maps agent names to their instruction text using the convention:
`{agent_name}_instruction` as the key.

Examples:
    Basic multi-agent candidate:

    ```python
    from gepa_adk.domain.types import MultiAgentCandidate

    candidate: MultiAgentCandidate = {
        "generator_instruction": "Generate Python code...",
        "critic_instruction": "Review the code...",
        "validator_instruction": "Validate the code...",
    }
    ```

Note:
    This type alias is compatible with GEPA's `Candidate` type
    (dict[str, str]), enabling seamless integration with existing
    mutation proposers and evolution engine components.
"""

FrontierKey: TypeAlias = (
    int | str | tuple[str, int] | tuple[str, str] | tuple[str, int, str]
)
"""Key type for frontier mappings across all frontier types.

Key structure varies by frontier type:
- int: example_idx for INSTANCE
- str: objective_name for OBJECTIVE
- tuple[str, int]: ("val_id", example_idx) for HYBRID instance-level
- tuple[str, str]: ("objective", objective_name) for HYBRID objective-level
- tuple[str, int, str]: ("cartesian", example_idx, objective_name) for CARTESIAN

Examples:
    ```python
    from gepa_adk.domain.types import FrontierKey

    # INSTANCE frontier key
    instance_key: FrontierKey = 0  # example_idx

    # OBJECTIVE frontier key
    objective_key: FrontierKey = "accuracy"  # objective_name

    # HYBRID frontier key
    hybrid_key: FrontierKey = ("val_id", 0)  # (type_tag, example_idx)

    # CARTESIAN frontier key
    cartesian_key: FrontierKey = (
        "cartesian", 0, "accuracy"
    )  # (type_tag, example_idx, objective_name)
    ```
"""

MergeAttempt: TypeAlias = tuple["Candidate", int, int, int] | None
"""Type alias for merge attempt results.

Represents a successful merge attempt with the merged candidate and parent/ancestor indices,
or None if merge was not possible.

    Type:
        tuple[Candidate, int, int, int] | None: (merged_candidate, parent1_idx,
            parent2_idx, ancestor_idx) or None

Examples:
    ```python
    from gepa_adk.domain.types import MergeAttempt
    from gepa_adk.domain.models import Candidate

    # Successful merge
    attempt: MergeAttempt = (
        Candidate(components={"instruction": "..."}),
        5,  # parent1_idx
        8,  # parent2_idx
        2,  # ancestor_idx
    )

    # Failed merge
    failed: MergeAttempt = None
    ```

Note:
    Used internally by MergeProposer to track merge operation results.
    The tuple format enables efficient tracking of genealogy relationships.
"""

AncestorLog: TypeAlias = tuple[int, int, int]
"""Type alias for tracking attempted merges.

Represents a merge attempt triplet that has been tried, preventing duplicate merges.

Type:
    tuple[int, int, int]: (parent1_idx, parent2_idx, ancestor_idx)

Examples:
    ```python
    from gepa_adk.domain.types import AncestorLog

    # Log of attempted merge
    log: AncestorLog = (5, 8, 2)  # (parent1_idx, parent2_idx, ancestor_idx)
    ```

Note:
    Used by MergeProposer to track which merge combinations have already been attempted,
    preventing redundant merge operations.
"""


@dataclass(frozen=True, slots=True)
class ProposalResult:
    """Result of a successful proposal operation.

    Attributes:
        candidate (Candidate): The proposed candidate with components.
        parent_indices (list[int]): Indices of parent candidate(s) in ParetoState.
        tag (str): Type of proposal ("mutation" or "merge").
        metadata (dict[str, Any]): Additional proposal-specific metadata.

    Examples:
        Creating a mutation proposal result:

        ```python
        from gepa_adk.domain.types import ProposalResult
        from gepa_adk.domain.models import Candidate

        result = ProposalResult(
            candidate=Candidate(components={"instruction": "Be helpful"}),
            parent_indices=[5],
            tag="mutation",
        )
        ```

        Creating a merge proposal result:

        ```python
        result = ProposalResult(
            candidate=Candidate(components={"instruction": "..."}),
            parent_indices=[5, 8],
            tag="merge",
            metadata={"ancestor_idx": 2},
        )
        ```

    Note:
        A frozen dataclass ensures immutability of proposal results.
        Parent indices must be valid indices into the ParetoState.candidates list.
    """

    candidate: "Candidate"  # Forward reference to avoid circular import
    parent_indices: list[int]
    tag: str
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "Score",
    "ComponentName",
    "ModelName",
    "TrajectoryConfig",
    "MultiAgentCandidate",
    "FrontierType",
    "FrontierKey",
    "MergeAttempt",
    "AncestorLog",
    "ProposalResult",
]
