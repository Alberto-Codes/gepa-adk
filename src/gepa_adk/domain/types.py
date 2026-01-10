"""Type aliases for the domain layer.

This module defines semantic type aliases used throughout the gepa-adk
domain models. These aliases provide documentation and clarity without
runtime overhead.

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
