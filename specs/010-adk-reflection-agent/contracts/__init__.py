"""Contract definitions for ADK reflection feature.

This package contains type contracts and protocol definitions for the
ADK-first reflection agent support feature.
"""

from .reflection_fn import (
    SESSION_STATE_KEYS,
    CreateAdkReflectionFnContract,
    ReflectionFn,
    ReflectionFnProtocol,
)

__all__ = [
    "ReflectionFn",
    "ReflectionFnProtocol",
    "SESSION_STATE_KEYS",
    "CreateAdkReflectionFnContract",
]
