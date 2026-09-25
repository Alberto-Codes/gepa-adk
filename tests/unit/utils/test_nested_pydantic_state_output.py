"""Acceptance tests for issue 389: nested pydantic models serialise as JSON.

``extract_output_from_state`` rendered a dict or list with
``json.dumps(value, default=str)``, so a pydantic model nested inside a dict
became a Python repr string inside otherwise valid JSON. It now serialises
through ``pydantic_core.to_jsonable_python`` so nested models, dates and
enums become JSON values.
"""

from __future__ import annotations

import json
from datetime import date
from enum import Enum

import pytest
from pydantic import BaseModel

from gepa_adk.utils.events import extract_output_from_state

pytestmark = pytest.mark.unit


class Verdict(str, Enum):
    """A string enum used as a nested value."""

    PASS = "pass"
    FAIL = "fail"


class Item(BaseModel):
    """A model nested inside the state value."""

    name: str
    score: float
    when: date
    verdict: Verdict


_ITEM = Item(name="a", score=0.5, when=date(2026, 9, 24), verdict=Verdict.PASS)


class TestNestedModelsSerialiseAsJson:
    """Nested models, dates and enums come out as JSON values."""

    def test_model_nested_in_dict(self) -> None:
        """{"result": Model(...)} renders the model as a JSON object."""
        text = extract_output_from_state({"out": {"result": _ITEM}}, "out")

        assert text is not None
        assert json.loads(text)["result"] == _ITEM.model_dump(mode="json")
        assert "Item(" not in text

    def test_models_nested_in_list(self) -> None:
        """A list of models renders each as a JSON object."""
        text = extract_output_from_state({"out": [_ITEM, _ITEM]}, "out")

        assert text is not None
        assert json.loads(text) == [_ITEM.model_dump(mode="json")] * 2

    def test_date_and_enum_inside_dict(self) -> None:
        """Dates become ISO strings and enums their values."""
        text = extract_output_from_state(
            {"out": {"when": date(2026, 9, 24), "verdict": Verdict.FAIL}}, "out"
        )

        assert text is not None
        assert json.loads(text) == {"when": "2026-09-24", "verdict": "fail"}

    def test_top_level_model_and_plain_values_unchanged(self) -> None:
        """A top-level model, a plain dict and a string render as before."""
        assert json.loads(extract_output_from_state({"out": _ITEM}, "out") or "") == (
            _ITEM.model_dump(mode="json")
        )
        assert json.loads(
            extract_output_from_state({"out": {"a": 1}}, "out") or ""
        ) == {"a": 1}
        assert extract_output_from_state({"out": "plain"}, "out") == "plain"

    def test_unserialisable_value_falls_back_to_str(self) -> None:
        """An object with no JSON form still renders instead of raising."""

        class Opaque:
            """A value json cannot encode and pydantic cannot convert."""

            def __repr__(self) -> str:
                """Render as a fixed marker.

                Returns:
                    The marker text.
                """
                return "<opaque>"

        text = extract_output_from_state({"out": {"x": Opaque()}}, "out")

        assert text is not None
        assert json.loads(text) == {"x": "<opaque>"}
