"""Contract tests for acceptance scoring configuration.

Note:
    Tests acceptance_metric configuration validation only.
    Behavior tests are in unit/ and integration/ test suites.
"""

from __future__ import annotations

import pytest

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionConfig

pytestmark = pytest.mark.contract


class TestAcceptanceScoringContract:
    """Contract tests for acceptance scoring configuration."""

    def test_acceptance_metric_defaults_to_sum(self) -> None:
        """acceptance_metric should default to 'sum'."""
        config = EvolutionConfig()
        assert config.acceptance_metric == "sum"

    def test_acceptance_metric_accepts_sum(self) -> None:
        """acceptance_metric should accept 'sum' value."""
        config = EvolutionConfig(acceptance_metric="sum")
        assert config.acceptance_metric == "sum"

    def test_acceptance_metric_accepts_mean(self) -> None:
        """acceptance_metric should accept 'mean' value."""
        config = EvolutionConfig(acceptance_metric="mean")
        assert config.acceptance_metric == "mean"

    def test_acceptance_metric_rejects_invalid_value(self) -> None:
        """acceptance_metric should reject invalid values."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(acceptance_metric="invalid")  # type: ignore[arg-type]
        assert exc_info.value.field == "acceptance_metric"
        assert exc_info.value.constraint == "sum|mean"
