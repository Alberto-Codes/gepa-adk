"""Older results load at the current schema version with unknown genealogy.

Schema version 4 adds ``candidate_id`` and ``parent_ids`` to each
``IterationRecord``. Loading a version 1, 2 or 3 dict runs
``_migrate_v3_to_v4()`` (after the earlier steps), which fills both fields
with None on every history record and keeps every older field. Version 5
then adds ``rejection_reason`` through ``_migrate_v4_to_v5()``, so these
fixtures load at version 5.

Examples:
    Run these tests:

    ```bash
    uv run pytest tests/unit/domain/test_schema_v4_migration.py -q
    ```

See Also:
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: ``IterationRecord``,
      ``CURRENT_SCHEMA_VERSION`` and the result migrations.

``TestMigrationStep`` exercises the v3 to v4 step at the dict level, so
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


def _load(name: str) -> dict:
    """Read a checked-in result fixture.

    Args:
        name: File name under ``tests/fixtures``.

    Returns:
        The parsed JSON dict.
    """
    return json.loads((_FIXTURES / name).read_text())


class TestOlderFixturesLoadAtVersionFive:
    """Every checked-in older fixture loads at the current version with None genealogy.

    Examples:
        ```bash
        uv run pytest tests/unit/domain/test_schema_v4_migration.py -q
        ```
    """

    @pytest.mark.parametrize(
        ("name", "version", "records"),
        [
            ("evolution_result_v1.json", 1, None),
            ("evolution_result_v2.json", 2, 3),
            ("evolution_result_v3.json", 3, 3),
        ],
    )
    def test_single_agent_fixture(
        self, name: str, version: int, records: int | None
    ) -> None:
        """A v1, v2 or v3 fixture loads at version 5 with None in both fields.

        Args:
            name: Fixture file name.
            version: The schema version the fixture was written at.
            records: Expected history length, or None to skip the check.
        """
        data = _load(name)
        assert data["schema_version"] == version
        assert all(
            "candidate_id" not in r and "parent_ids" not in r
            for r in data["iteration_history"]
        )

        result = EvolutionResult.from_dict(data)

        assert result.schema_version == CURRENT_SCHEMA_VERSION == 5
        assert result.iteration_history
        if records is not None:
            assert len(result.iteration_history) == records
        assert all(r.candidate_id is None for r in result.iteration_history)
        assert all(r.parent_ids is None for r in result.iteration_history)

    @pytest.mark.parametrize(
        "name", ["multiagent_result_v1.json", "multiagent_result_v2.json"]
    )
    def test_multiagent_fixture(self, name: str) -> None:
        """A multi-agent v1 or v2 fixture loads at version 5 with None genealogy.

        Args:
            name: Fixture file name.
        """
        result = MultiAgentEvolutionResult.from_dict(_load(name))

        assert result.schema_version == 5
        assert all(r.candidate_id is None for r in result.iteration_history)
        assert all(r.parent_ids is None for r in result.iteration_history)

    def test_v3_fixture_keeps_its_token_usage(self) -> None:
        """Migrating a v3 fixture keeps the usage and the failure counts."""
        result = EvolutionResult.from_dict(_load("evolution_result_v3.json"))

        assert result.token_usage is not None
        assert result.token_usage.total_tokens == 520
        first = result.iteration_history[0].token_usage
        assert first is not None
        assert first.rows_counted == 2
        assert result.baseline_failed_evaluations == 2
        assert [r.failed_evaluations for r in result.iteration_history] == [1, 0, 0]
        assert result.iteration_history[1].skip_reason == "empty_proposal"

    def test_v3_load_does_not_mutate_input(self) -> None:
        """Migration copies the dict and its records instead of editing them."""
        data = _load("evolution_result_v3.json")
        before = json.dumps(data, sort_keys=True)

        EvolutionResult.from_dict(data)

        assert json.dumps(data, sort_keys=True) == before

    def test_loaded_v3_result_writes_version_five(self) -> None:
        """A migrated result serializes at version 5 with both keys present."""
        result = EvolutionResult.from_dict(_load("evolution_result_v3.json"))

        data = result.to_dict()

        assert data["schema_version"] == 5
        for record in data["iteration_history"]:
            assert record["candidate_id"] is None
            assert record["parent_ids"] is None


class TestMigrationStep:
    """The v3 to v4 and v4 to v5 steps add their keys at the dict level.

    Examples:
        ```bash
        uv run pytest tests/unit/domain/test_schema_v4_migration.py -q
        ```
    """

    def test_migrate_result_dict_adds_genealogy_to_every_record(self) -> None:
        """A version 3 dict gains candidate_id and parent_ids and reaches version 5."""
        from gepa_adk.domain.models import _migrate_result_dict

        record = {
            "iteration_number": 1,
            "score": 1.0,
            "component_text": "t",
            "evolved_component": "instruction",
            "accepted": True,
            "token_usage": None,
        }
        v3 = {
            "schema_version": 3,
            "stop_reason": "completed",
            "original_score": 0.5,
            "final_score": 1.0,
            "evolved_components": {"instruction": "t"},
            "iteration_history": [dict(record), dict(record)],
            "total_iterations": 2,
            "token_usage": None,
        }

        migrated = _migrate_result_dict(v3, from_version=3)

        assert migrated["schema_version"] == 5
        assert len(migrated["iteration_history"]) == 2
        assert all(r["candidate_id"] is None for r in migrated["iteration_history"])
        assert all(r["parent_ids"] is None for r in migrated["iteration_history"])
        # The input dict and its records are untouched.
        assert all("candidate_id" not in r for r in v3["iteration_history"])
        assert all("parent_ids" not in r for r in v3["iteration_history"])

    def test_migrate_v3_to_v4_keeps_existing_genealogy(self) -> None:
        """A record that already names its genealogy is not overwritten."""
        from gepa_adk.domain.models import _migrate_v3_to_v4

        data = {
            "iteration_history": [
                {"candidate_id": "abc", "parent_ids": ["seed"]},
                {},
            ]
        }

        migrated = _migrate_v3_to_v4(dict(data))

        assert migrated["iteration_history"][0] == {
            "candidate_id": "abc",
            "parent_ids": ["seed"],
        }
        assert migrated["iteration_history"][1] == {
            "candidate_id": None,
            "parent_ids": None,
        }

    def test_from_dict_does_not_alias_parent_ids(self) -> None:
        """The loaded record's parent_ids is a copy of the input list."""
        from gepa_adk.domain.models import IterationRecord

        parents = ["seed"]
        record = IterationRecord.from_dict(
            {
                "iteration_number": 1,
                "score": 1.0,
                "component_text": "t",
                "evolved_component": "instruction",
                "accepted": True,
                "candidate_id": "abc",
                "parent_ids": parents,
            }
        )
        parents.append("other")

        assert record.parent_ids == ["seed"]

    def test_migrate_v4_to_v5_keeps_an_existing_reason(self) -> None:
        """A record that already carries a rejection reason is not overwritten."""
        from gepa_adk.domain.models import _migrate_v4_to_v5

        data = {"iteration_history": [{"rejection_reason": "refusal"}, {}]}

        migrated = _migrate_v4_to_v5(dict(data))

        assert migrated["iteration_history"] == [
            {"rejection_reason": "refusal"},
            {"rejection_reason": None},
        ]
        assert data["iteration_history"][1] == {}
