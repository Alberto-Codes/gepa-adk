"""Version 2 results load at the current schema with unknown token usage.

The checked-in version 2 fixtures are shaped like ``to_dict()`` output from
gepa-adk 2.4.x. Loading them runs ``_migrate_v2_to_v3()``, which adds
``token_usage: None`` to the result and to each history record, and keeps
every version 2 field.

Examples:
    Run these tests:

    ```bash
    uv run pytest tests/unit/domain/test_schema_v3_migration.py -q
    ```

See Also:
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: ``TokenRollup``,
      ``CURRENT_SCHEMA_VERSION`` and the result migrations.

``TestMigrationStep`` exercises the v2 to v3 step at the dict level, so
removing the step from ``_migrate_result_dict`` fails a test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gepa_adk.domain.models import (
    CURRENT_SCHEMA_VERSION,
    EvolutionResult,
    MultiAgentEvolutionResult,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).parents[2] / "fixtures"


class TestVersionTwoFixtures:
    """The version 2 fixtures migrate to the current version without losing fields."""

    def test_evolution_result_v2_loads_with_unknown_usage(self) -> None:
        """The single-agent v2 fixture loads at version 6 with None usage and its counts kept."""
        data = json.loads((_FIXTURES / "evolution_result_v2.json").read_text())
        assert data["schema_version"] == 2
        assert "token_usage" not in data
        assert all("token_usage" not in r for r in data["iteration_history"])

        result = EvolutionResult.from_dict(data)

        assert result.schema_version == CURRENT_SCHEMA_VERSION == 6
        assert result.token_usage is None
        assert len(result.iteration_history) == 3
        assert all(r.token_usage is None for r in result.iteration_history)
        assert result.baseline_failed_evaluations == 2
        assert result.total_failed_evaluations == 3
        assert [r.failed_evaluations for r in result.iteration_history] == [1, 0, 0]
        assert result.iteration_history[1].skip_reason == "empty_proposal"
        assert result.original_components == {"instruction": "Be helpful"}

    def test_multiagent_result_v2_loads_with_unknown_usage(self) -> None:
        """The multi-agent v2 fixture loads with None usage and its counts kept."""
        data = json.loads((_FIXTURES / "multiagent_result_v2.json").read_text())
        assert data["schema_version"] == 2

        result = MultiAgentEvolutionResult.from_dict(data)

        assert result.schema_version == CURRENT_SCHEMA_VERSION
        assert result.token_usage is None
        assert len(result.iteration_history) == 2
        assert all(r.token_usage is None for r in result.iteration_history)
        assert result.total_failed_evaluations == 1
        assert result.primary_agent == "generator"

    def test_v2_load_does_not_mutate_input(self) -> None:
        """Migration copies the dict and its records instead of editing them."""
        data = json.loads((_FIXTURES / "evolution_result_v2.json").read_text())
        before = json.dumps(data, sort_keys=True)

        EvolutionResult.from_dict(data)

        assert json.dumps(data, sort_keys=True) == before

    def test_v1_fixture_reaches_version_6(self) -> None:
        """A version 1 dict goes through every migration up to version 6."""
        data = json.loads((_FIXTURES / "evolution_result_v1.json").read_text())

        result = EvolutionResult.from_dict(data)

        assert result.schema_version == 6
        assert result.token_usage is None
        assert result.total_failed_evaluations == 0
        assert all(r.token_usage is None for r in result.iteration_history)

    def test_multiagent_round_trip_keeps_usage(self) -> None:
        """A multi-agent result with usage survives to_dict and from_dict."""
        from gepa_adk.domain.models import TokenRollup

        usage = TokenRollup(
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            rows_counted=0,
            rows_unknown=4,
        )
        result = MultiAgentEvolutionResult(
            evolved_components={"a.instruction": "x"},
            original_score=0.1,
            final_score=0.2,
            primary_agent="a",
            iteration_history=[],
            total_iterations=0,
            token_usage=usage,
        )

        data = json.loads(json.dumps(result.to_dict()))

        assert data["token_usage"]["total_tokens"] == "unknown"
        assert MultiAgentEvolutionResult.from_dict(data) == result


class TestMigrationStep:
    """The v2 to v3 step itself adds the usage keys at the dict level."""

    def test_migrate_result_dict_adds_token_usage_everywhere(self) -> None:
        """A version 2 dict gains token_usage on the result and each record."""
        from gepa_adk.domain.models import _migrate_result_dict

        record = {
            "iteration_number": 1,
            "score": 1.0,
            "component_text": "t",
            "evolved_component": "instruction",
            "accepted": True,
        }
        v2 = {
            "schema_version": 2,
            "stop_reason": "completed",
            "original_score": 0.5,
            "final_score": 1.0,
            "evolved_components": {"instruction": "t"},
            "iteration_history": [dict(record), dict(record)],
            "total_iterations": 2,
        }

        migrated = _migrate_result_dict(v2, from_version=2)

        assert migrated["token_usage"] is None
        assert len(migrated["iteration_history"]) == 2
        assert all(r["token_usage"] is None for r in migrated["iteration_history"])
        # The input dict and its records are untouched.
        assert "token_usage" not in v2
        assert all("token_usage" not in r for r in v2["iteration_history"])

    def test_migrate_v2_to_v3_keeps_an_existing_rollup(self) -> None:
        """A record that already carries usage is not overwritten."""
        from gepa_adk.domain.models import _migrate_v2_to_v3

        usage = {
            "input_tokens": 1,
            "output_tokens": 2,
            "total_tokens": 3,
            "rows_counted": 1,
            "rows_unknown": 0,
        }
        data = {"iteration_history": [{"token_usage": usage}, {}]}

        migrated = _migrate_v2_to_v3(dict(data))

        assert migrated["iteration_history"][0]["token_usage"] == usage
        assert migrated["iteration_history"][1]["token_usage"] is None
        assert migrated["token_usage"] is None
