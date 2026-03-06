"""Utility functions for trajectory extraction and processing.

This module provides utilities for extracting, redacting, and truncating
trajectory data from ADK agent execution events.

The primary function is [`extract_trajectory`][gepa_adk.utils.extract_trajectory]
which orchestrates the complete extraction pipeline: raw data extraction →
redaction → truncation → trajectory construction. Configuration is provided via
[`TrajectoryConfig`][gepa_adk.domain.types.TrajectoryConfig] from the domain
layer.

Attributes:
    extract_trajectory (function): Main trajectory extraction API with
        configuration support for redaction and truncation.

Examples:
    Extract with default configuration (redaction + truncation enabled):

    ```python
    from gepa_adk.utils import extract_trajectory
    from gepa_adk.domain.types import DEFAULT_SENSITIVE_KEYS, TrajectoryConfig

    # Extract with defaults
    trajectory = extract_trajectory(events, final_output="Response text")

    # Custom configuration
    config = TrajectoryConfig(
        include_tool_calls=True,
        redact_sensitive=True,
        sensitive_keys=DEFAULT_SENSITIVE_KEYS + ("custom_key",),
        max_string_length=5000,
    )
    trajectory = extract_trajectory(events, config=config)
    ```

See Also:
    - [`gepa_adk.utils.events`][gepa_adk.utils.events]:
      Implementation of extraction utilities
    - [`gepa_adk.domain.types.TrajectoryConfig`]
      [gepa_adk.domain.types.TrajectoryConfig]: Configuration dataclass
    - [`gepa_adk.domain.trajectory`][gepa_adk.domain.trajectory]:
      Trajectory domain models

Note:
    These utilities are infrastructure concerns, not domain logic.
    They consume domain models but don't define them.
"""

from gepa_adk.utils.encoding import EncodingSafeProcessor
from gepa_adk.utils.events import extract_final_output, extract_trajectory
from gepa_adk.utils.schema_utils import (
    SCHEMA_NAMESPACE,
    SchemaValidationResult,
    deserialize_schema,
    serialize_pydantic_schema,
    validate_schema_text,
)
from gepa_adk.utils.state_guard import StateGuard

__all__ = [
    "EncodingSafeProcessor",
    "extract_final_output",
    "extract_trajectory",
    "StateGuard",
    # Schema utilities
    "SCHEMA_NAMESPACE",
    "SchemaValidationResult",
    "deserialize_schema",
    "serialize_pydantic_schema",
    "validate_schema_text",
]
