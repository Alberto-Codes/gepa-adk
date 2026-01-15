"""Type aliases and configuration types for the domain layer.

This module defines semantic type aliases and configuration dataclasses
used throughout the gepa-adk domain models. These types provide documentation
and clarity without runtime overhead.

Attributes:
    Score (type): Type alias for normalized scores (typically [0.0, 1.0]).
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.
    TrajectoryConfig (class): Configuration for trajectory extraction behavior.

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

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

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
    """Supported frontier tracking strategies for Pareto selection."""

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

__all__ = [
    "Score",
    "ComponentName",
    "ModelName",
    "TrajectoryConfig",
    "MultiAgentCandidate",
    "FrontierType",
]
