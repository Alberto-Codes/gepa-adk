"""Pytest fixtures for engine tests."""

import pytest

from gepa_adk.domain.models import Candidate, EvolutionConfig
from tests.fixtures.adapters import (
    MockAdapter,
)


@pytest.fixture
def mock_adapter() -> MockAdapter:
    """Provide a mock adapter for tests."""
    return MockAdapter()


@pytest.fixture
def sample_config() -> EvolutionConfig:
    """Provide a sample evolution configuration."""
    return EvolutionConfig(max_iterations=50, patience=5)


@pytest.fixture
def sample_candidate() -> Candidate:
    """Provide a sample initial candidate."""
    return Candidate(components={"instruction": "Be helpful"}, generation=0)


@pytest.fixture
def sample_batch() -> list[dict[str, str]]:
    """Provide a sample evaluation batch."""
    return [{"input": "Hello", "expected": "Hi"}]
