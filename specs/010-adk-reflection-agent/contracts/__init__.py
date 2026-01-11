"""Contract definitions for ADK reflection feature.

This package contains type contracts and protocol definitions for the
ADK-first reflection agent support feature.
"""

from .reflection_fn import (
    CreateAdkReflectionFnContract,
    ReflectionFn,
    ReflectionFnProtocol,
    SESSION_STATE_KEYS,
)

__all__ = [
    "ReflectionFn",
    "ReflectionFnProtocol",
    "SESSION_STATE_KEYS",
    "CreateAdkReflectionFnContract",
]
