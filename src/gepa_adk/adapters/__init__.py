"""Adapters layer - External implementations of ports.

Adapters connect the domain logic to external systems (Google ADK, LiteLLM, etc.).
Each adapter implements one or more protocol interfaces from the ports layer.

Note:
    Adapters ONLY live here - they import from ports/ and domain/ but never
    the reverse. This maintains hexagonal architecture boundaries.

Exports:
    ADKAdapter: AsyncGEPAAdapter implementation for Google ADK agents.
"""

from gepa_adk.adapters.adk_adapter import ADKAdapter

__all__ = [
    "ADKAdapter",
]
