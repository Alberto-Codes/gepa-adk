"""Type aliases for the domain layer.

This module defines semantic type aliases used throughout the gepa-adk
domain models. These aliases provide documentation and clarity without
runtime overhead.

Attributes:
    Score (type): Type alias for normalized scores (typically [0.0, 1.0]).
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.

Examples:
    Using type aliases for clarity:

    ```python
    from gepa_adk.domain.types import Score, ComponentName

    score: Score = 0.85
    component: ComponentName = "instruction"
    ```

Note:
    Type aliases are lightweight hints that improve code readability
    and IDE support. They do not enforce validation at runtime.
"""

from typing import TypeAlias

Score: TypeAlias = float
"""Normalized score, typically in [0.0, 1.0]."""

ComponentName: TypeAlias = str
"""Name of a candidate component (e.g., 'instruction', 'output_schema')."""

ModelName: TypeAlias = str
"""Model identifier (e.g., 'gemini-2.0-flash', 'gpt-4o')."""

__all__ = ["Score", "ComponentName", "ModelName"]
