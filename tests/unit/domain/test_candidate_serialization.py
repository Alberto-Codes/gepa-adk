"""Round-trip tests for ``Candidate.to_dict`` and ``Candidate.from_dict``.

The engine checkpoints the best candidate through these two methods, so every
field, including lineage and metadata, must survive a JSON round trip.

Examples:
    Run these tests:

    ```bash
    uv run pytest tests/unit/domain/test_candidate_serialization.py -q
    ```

See Also:
    - [`gepa_adk.domain.models.Candidate`][gepa_adk.domain.models.Candidate]:
      The type under test.
"""

from __future__ import annotations

import json

import pytest

from gepa_adk.domain.models import Candidate

pytestmark = pytest.mark.unit


class TestCandidateRoundTrip:
    """Candidate survives to_dict, JSON and from_dict unchanged.

    Examples:
        ```bash
        uv run pytest "tests/unit/domain/test_candidate_serialization.py::TestCandidateRoundTrip" -q
        ```
    """

    def test_every_field_round_trips(self) -> None:
        """Components, generation, parent_id, parent_ids and metadata survive."""
        candidate = Candidate(
            components={"instruction": "Be terse", "output_schema": "{}"},
            generation=3,
            parent_id="gen-2",
            parent_ids=[1, 4],
            metadata={"source": "merge", "nested": {"k": [1, 2]}},
        )

        data = json.loads(json.dumps(candidate.to_dict()))
        restored = Candidate.from_dict(data)

        assert restored == candidate
        assert restored.parent_ids == [1, 4]
        assert restored.metadata == {"source": "merge", "nested": {"k": [1, 2]}}
        assert restored.id == candidate.id
        assert "id" not in data

    def test_seed_candidate_round_trips_with_none_lineage(self) -> None:
        """A seed candidate keeps parent_ids None and empty metadata."""
        candidate = Candidate(components={"instruction": "seed"})

        restored = Candidate.from_dict(json.loads(json.dumps(candidate.to_dict())))

        assert restored == candidate
        assert restored.parent_ids is None
        assert restored.parent_id is None
        assert restored.metadata == {}

    def test_to_dict_copies_mutable_fields(self) -> None:
        """Mutating the dict does not change the candidate."""
        candidate = Candidate(components={"instruction": "a"}, parent_ids=[0])
        data = candidate.to_dict()
        data["components"]["instruction"] = "b"
        data["parent_ids"].append(9)

        assert candidate.components == {"instruction": "a"}
        assert candidate.parent_ids == [0]
