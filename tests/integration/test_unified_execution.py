"""Integration tests for unified agent execution.

This module tests the AgentExecutor with real ADK agents to verify
feature parity across generator, critic, and reflection agent types.

Tests follow ADR-005 three-layer testing strategy at the integration layer.
"""

import pytest


@pytest.mark.integration
@pytest.mark.slow
class TestUnifiedExecutionFeatureParity:
    """Integration tests verifying feature parity across agent types."""

    # T025: Integration test for session sharing
    # T044-T047: Integration tests for migration
    pass


@pytest.mark.integration
@pytest.mark.slow
class TestBackwardCompatibility:
    """Integration tests verifying backward compatibility."""

    pass
