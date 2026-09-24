"""Label-agreement scorer that compares agent output with a labelled answer.

This module provides ``LabelAgreementScorer``, a deterministic ``Scorer``
for trainsets whose rows carry an ``expected`` label. Pass it to
``evolve()``, ``evolve_group()`` or ``evolve_workflow()`` through the
``scorer=`` keyword instead of a critic agent.

Attributes:
    LabelAgreementScorer (class): Scores 1.0 when the output agrees with
        ``expected`` after whitespace stripping, else 0.0.

Examples:
    Score one output field of a schema agent against its label:

    ```python
    from gepa_adk.adapters.scoring import LabelAgreementScorer

    scorer = LabelAgreementScorer(field="label")
    score, metadata = scorer.score("Buy now!!!", '{"label": "spam"}', "spam")
    assert score == 1.0
    assert metadata["agreement"] is True
    ```

See Also:
    - [`gepa_adk.ports.scorer`][gepa_adk.ports.scorer]: Protocol that
        LabelAgreementScorer implements.
    - [`gepa_adk.adapters.scoring.critic_scorer`][gepa_adk.adapters.scoring.critic_scorer]:
        LLM critic scorer for outputs without a labelled answer.

Notes:
    Comparison is exact after ``str.strip()``. There is no case folding,
    fuzzy matching or numeric tolerance.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["LabelAgreementScorer"]

_MISSING = object()


def _parse_json(text: str) -> Any:
    """Parse text as JSON, returning a sentinel when it is not JSON.

    Args:
        text: Candidate JSON text.

    Returns:
        The parsed document, or the module ``_MISSING`` sentinel when the
        text does not parse.
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return _MISSING


class LabelAgreementScorer:
    """Scorer that measures exact agreement between output and label.

    With ``field`` set, the output is parsed as a JSON object and
    ``str(parsed[field]).strip()`` is compared with ``expected.strip()``.
    Without ``field``, the output and ``expected`` agree when both parse as equal JSON
    documents, or otherwise when their stripped texts are equal.

    Attributes:
        field (str | None): Name of the output JSON field holding the
            label, or ``None`` to compare the whole output.

    Examples:
        Evolve a schema agent against labelled rows:

        ```python
        from gepa_adk import LabelAgreementScorer, evolve, run_sync

        trainset = [{"input": "Buy now!!!", "expected": "spam"}]
        result = run_sync(
            evolve(agent, trainset, scorer=LabelAgreementScorer(field="label"))
        )
        ```

    Notes:
        Adheres to the Scorer protocol. The score is 0.0 with
        ``metadata["reason"]`` set to ``"missing_expected"`` when the row has
        no label, ``"output_not_json"`` when ``field`` is set and the output
        does not parse, and ``"field_missing"`` when the parsed output is not
        an object or lacks ``field``. Metadata always carries ``field``,
        ``actual``, ``expected`` and ``agreement``.
    """

    def __init__(self, field: str | None = None) -> None:
        """Store the output field to compare.

        Args:
            field: Name of the JSON field holding the label, or ``None`` to
                compare the whole output.
        """
        self.field = field

    def _result(
        self,
        *,
        actual: str | None,
        expected: str | None,
        agreement: bool,
        reason: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Build the score and metadata pair.

        Args:
            actual: Extracted value that was compared, if any.
            expected: Label from the trainset row.
            agreement: Whether the value agreed with the label.
            reason: Why no comparison was possible, if applicable.

        Returns:
            The score and its metadata dictionary.
        """
        metadata: dict[str, Any] = {
            "field": self.field,
            "actual": actual,
            "expected": expected,
            "agreement": agreement,
        }
        if reason is not None:
            metadata["reason"] = reason
        return (1.0 if agreement else 0.0), metadata

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score the output by agreement with the expected label.

        Args:
            input_text: Input given to the agent. Not used.
            output: Agent output text.
            expected: Label from the trainset row.

        Returns:
            ``(1.0, metadata)`` on agreement, else ``(0.0, metadata)``.
        """
        if expected is None:
            return self._result(
                actual=None,
                expected=None,
                agreement=False,
                reason="missing_expected",
            )
        if self.field is None:
            return self._score_whole(output, expected)
        parsed = _parse_json(output)
        if parsed is _MISSING:
            return self._result(
                actual=None,
                expected=expected,
                agreement=False,
                reason="output_not_json",
            )
        if not isinstance(parsed, dict) or self.field not in parsed:
            return self._result(
                actual=None,
                expected=expected,
                agreement=False,
                reason="field_missing",
            )
        actual = str(parsed[self.field]).strip()
        return self._result(
            actual=actual,
            expected=expected,
            agreement=actual == expected.strip(),
        )

    def _score_whole(self, output: str, expected: str) -> tuple[float, dict[str, Any]]:
        """Compare the whole output with the label.

        Args:
            output: Agent output text.
            expected: Label from the trainset row.

        Returns:
            The score and its metadata dictionary.
        """
        actual = output.strip()
        parsed_output = _parse_json(output)
        parsed_expected = _parse_json(expected)
        if parsed_output is not _MISSING and parsed_expected is not _MISSING:
            agreement = parsed_output == parsed_expected
        else:
            agreement = actual == expected.strip()
        return self._result(actual=actual, expected=expected, agreement=agreement)

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score asynchronously by delegating to ``score``.

        Args:
            input_text: Input given to the agent. Not used.
            output: Agent output text.
            expected: Label from the trainset row.

        Returns:
            The same result as ``score``.
        """
        return self.score(input_text, output, expected)
