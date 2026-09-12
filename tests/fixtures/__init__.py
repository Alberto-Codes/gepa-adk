"""Test fixtures for gepa-adk tests.

This package provides reusable test fixtures including configurable mock adapters
for testing the evolution engine without requiring real evaluation systems, and
the canonical Gemini model identifiers used by the live-model test tier.
"""

from tests.fixtures.adapters import (
    AdapterConfig,
    ConfigurableMockAdapter,
    MockAdapter,
    OutputMode,
    create_mock_adapter,
)
from tests.fixtures.models import (
    DEPRECATED_GEMINI_PREFIXES,
    GEMINI_TEST_MODEL,
    is_deprecated_gemini_model,
)

__all__ = [
    "DEPRECATED_GEMINI_PREFIXES",
    "GEMINI_TEST_MODEL",
    "AdapterConfig",
    "ConfigurableMockAdapter",
    "MockAdapter",
    "OutputMode",
    "create_mock_adapter",
    "is_deprecated_gemini_model",
]
