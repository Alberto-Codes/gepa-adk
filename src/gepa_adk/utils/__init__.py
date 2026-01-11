"""Utility functions for trajectory extraction and processing.

This module provides utilities for extracting, redacting, and truncating
trajectory data from ADK agent execution events.

The primary function is `extract_trajectory()` which orchestrates the complete
extraction pipeline: raw data extraction → redaction → truncation → trajectory
construction. Configuration is provided via `TrajectoryConfig` from the domain
layer.

Typical usage:
    ```python
    from gepa_adk.utils import extract_trajectory
    from gepa_adk.domain.types import TrajectoryConfig

    # Extract with default configuration (redaction + truncation enabled)
    trajectory = extract_trajectory(events, final_output="Response text")

    # Custom configuration
    config = TrajectoryConfig(
        include_tool_calls=True,
        redact_sensitive=True,
        sensitive_keys=("password", "api_key", "secret"),
        max_string_length=5000,
    )
    trajectory = extract_trajectory(events, config=config)
    ```

See Also:
    - `gepa_adk.utils.events`: Implementation of extraction utilities
    - `gepa_adk.domain.types.TrajectoryConfig`: Configuration dataclass
    - `gepa_adk.domain.trajectory`: Trajectory domain models

Note:
    Utilities in this module are infrastructure concerns, not domain logic.
    They consume domain models but don't define them.
"""

from gepa_adk.utils.events import extract_trajectory

__all__ = ["extract_trajectory"]
