"""Shared fixtures for adapter unit tests.

This module provides common fixtures used across adapter test files,
including mock proposers and other shared test utilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer


@pytest.fixture
def mock_proposer() -> AsyncMock:
    """Create a mock AsyncReflectiveMutationProposer for testing.

    Returns:
        AsyncMock configured with spec matching AsyncReflectiveMutationProposer.
        The mock's propose() method returns a default successful result by default.
    """
    proposer = AsyncMock(spec=AsyncReflectiveMutationProposer)
    proposer.propose = AsyncMock(return_value={"instruction": "improved text"})
    return proposer
