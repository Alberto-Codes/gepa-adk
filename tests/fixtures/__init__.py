"""Test fixtures for gepa-adk tests.

This package provides reusable test fixtures including configurable mock adapters
for testing the evolution engine without requiring real evaluation systems.
"""

from tests.fixtures.adapters import (
    AdapterConfig,
    ConfigurableMockAdapter,
    MockAdapter,
    OutputMode,
    create_mock_adapter,
)

__all__ = [
    "AdapterConfig",
    "ConfigurableMockAdapter",
    "MockAdapter",
    "OutputMode",
    "create_mock_adapter",
]
