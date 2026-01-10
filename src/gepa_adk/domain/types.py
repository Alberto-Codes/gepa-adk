"""Type aliases for domain models.

Note: This module defines semantic type aliases for clarity.
"""

from typing import TypeAlias

Score: TypeAlias = float
"""Normalized score, typically in [0.0, 1.0]."""

ComponentName: TypeAlias = str
"""Name of a candidate component (e.g., 'instruction', 'output_schema')."""

ModelName: TypeAlias = str
"""Model identifier (e.g., 'gemini-2.0-flash', 'gpt-4o')."""
