"""Protocol definition for scoring agent outputs.

This module defines the Scorer protocol that enables custom scoring logic
for evaluating agent outputs in the evolution engine. The protocol provides
both synchronous and asynchronous methods, returning a tuple of score and
metadata.

Attributes:
    Scorer (protocol): Protocol for scoring agent outputs.
    scorer_accepts_trajectory (function): Report whether a scorer declares
        the optional ``trajectory`` parameter on ``async_score``.

Examples:
    Implement a simple exact-match scorer:

    ```python
    from gepa_adk import Scorer


    class ExactMatchScorer:
        def score(
            self,
            input_text: str,
            output: str,
            expected: str | None = None,
        ) -> tuple[float, dict]:
            if expected is None:
                return 0.0, {"error": "Expected value required"}
            match = output.strip() == expected.strip()
            return (1.0 if match else 0.0), {"exact_match": match}

        async def async_score(
            self,
            input_text: str,
            output: str,
            expected: str | None = None,
        ) -> tuple[float, dict]:
            return self.score(input_text, output, expected)
    ```

    Use the scorer:

    ```python
    scorer = ExactMatchScorer()
    score, metadata = scorer.score("What is 2+2?", "4", "4")
    assert score == 1.0
    assert metadata["exact_match"] is True
    ```

    Opt in to the execution trajectory by declaring ``trajectory``:

    ```python
    from gepa_adk.domain.trajectory import ADKTrajectory


    class UsedSearchScorer:
        def score(
            self,
            input_text: str,
            output: str,
            expected: str | None = None,
            *,
            trajectory: ADKTrajectory | None = None,
        ) -> tuple[float, dict]:
            names = [c.name for c in trajectory.tool_calls] if trajectory else []
            return (1.0 if "search" in names else 0.0), {"tools": names}

        async def async_score(
            self,
            input_text: str,
            output: str,
            expected: str | None = None,
            *,
            trajectory: ADKTrajectory | None = None,
        ) -> tuple[float, dict]:
            return self.score(input_text, output, expected, trajectory=trajectory)
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Scorer implementations
        (e.g., CriticScorer, exact-match scorers).
    - [`gepa_adk.adapters.scoring.require_tool`][gepa_adk.adapters.scoring.require_tool]:
        Wrapper that scores 0.0 when a named tool did not run.

Notes:
    The protocol defines both synchronous and asynchronous scoring methods
    to support various use cases. Score values should be normalized between
    0.0 and 1.0 by convention, with higher values indicating better performance.
    The protocol does not enforce this range.

    A scorer may also declare an optional parameter named ``trajectory``
    (``trajectory: ADKTrajectory | None = None``, keyword-only or
    positional-or-keyword) on ``score`` and ``async_score``. The evolution
    adapters check ``async_score`` with ``scorer_accepts_trajectory`` and send
    the row's ``ADKTrajectory`` as a keyword argument only when the parameter
    is declared. A scorer with the
    three-argument signature is called exactly as before. A ``**kwargs``
    catch-all, a positional-only ``trajectory`` and a ``**trajectory``
    catch-all do not count as a declaration.
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol, runtime_checkable

# Kinds the adapters can fill with ``trajectory=...``.
_KEYWORD_KINDS = (
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.KEYWORD_ONLY,
)


@runtime_checkable
class Scorer(Protocol):
    """Protocol for scoring agent outputs.

    Implementations provide scoring logic that evaluates how well
    an agent's output matches expected results or quality criteria.

    Both synchronous and asynchronous methods are defined. Implementations
    should provide both, though callers may use only one based on context.

    Examples:
        Implement a simple fixed scorer for testing:

        ```python
        class FixedScorer:
            def score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict]:
                return 0.5, {"note": "Fixed score for testing"}

            async def async_score(
                self,
                input_text: str,
                output: str,
                expected: str | None = None,
            ) -> tuple[float, dict]:
                return self.score(input_text, output, expected)
        ```

        Verify protocol compliance:

        ```python
        from gepa_adk import Scorer

        scorer = FixedScorer()
        assert isinstance(scorer, Scorer)  # Runtime check works
        ```

    Notes:
        All implementations must provide both score() and async_score()
        methods to satisfy the protocol. Score values should be normalized
        between 0.0 and 1.0 by convention, with higher values indicating
        better performance. The protocol does not enforce this range.

        An implementation may add an optional parameter named ``trajectory``
        (``trajectory: ADKTrajectory | None = None``, keyword-only or
        positional-or-keyword) to both methods. The
        adapters send the row's trajectory only to a scorer whose
        ``async_score`` declares that parameter by name; see
        ``scorer_accepts_trajectory``.
    """

    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output synchronously.

        Args:
            input_text: The input provided to the agent.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.
                Pass None for open-ended evaluation without expected output.

        Returns:
            A tuple of (score, metadata) where:

            - score: Float value, conventionally 0.0-1.0, higher is better
            - metadata: Dict with arbitrary scoring details (e.g., feedback,
                dimension_scores, reasoning). Should be JSON-serializable.

        Examples:
            Basic usage:

            ```python
            score, meta = scorer.score("What is 2+2?", "4", "4")
            assert score == 1.0
            assert meta.get("exact_match") is True
            ```

            Scoring without expected output:

            ```python
            score, meta = scorer.score("Explain gravity", response)
            # Scorer evaluates based on quality criteria, not exact match
            ```

        Notes:
            Operations complete synchronously and block until scoring finishes.
            Use async_score() for I/O-bound operations like LLM calls.
        """
        ...

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]:
        """Score an agent output asynchronously.

        Args:
            input_text: The input provided to the agent.
            output: The agent's generated output to score.
            expected: Optional expected/reference output for comparison.
                Pass None for open-ended evaluation without expected output.

        Returns:
            A tuple of (score, metadata) where:

            - score: Float value, conventionally 0.0-1.0, higher is better
            - metadata: Dict with arbitrary scoring details (e.g., feedback,
                dimension_scores, reasoning). Should be JSON-serializable.

        Examples:
            Async usage:

            ```python
            score, meta = await scorer.async_score("Explain gravity", response)
            print(f"Quality: {score:.2f} - {meta.get('feedback')}")
            ```

            Concurrent scoring:

            ```python
            import asyncio

            tasks = [
                scorer.async_score(input, output, expected)
                for input, output, expected in batch
            ]
            scores = await asyncio.gather(*tasks)
            ```

        Notes:
            Operations run asynchronously and can be executed concurrently.
            Prefer this method for I/O-bound scoring operations such as
            LLM-based evaluation or external API calls.
        """
        ...


def scorer_accepts_trajectory(scorer: object) -> bool:
    """Report whether a scorer declares a ``trajectory`` parameter.

    Args:
        scorer: Object with an ``async_score`` method.

    Returns:
        True when the signature of ``scorer.async_score`` has a parameter
        named ``trajectory`` that can be passed by keyword (positional-or-
        keyword or keyword-only). False when it does not, when the name
        belongs to a positional-only parameter or a ``**trajectory``
        catch-all, when the only catch-all is ``**kwargs``, when
        ``async_score`` is missing, or when its signature cannot be read.

    Examples:
        ```python
        from gepa_adk.ports.scorer import scorer_accepts_trajectory


        class ThreeArg:
            async def async_score(self, input_text, output, expected=None):
                return 0.0, {}


        class WithTrajectory:
            async def async_score(
                self, input_text, output, expected=None, *, trajectory=None
            ):
                return 0.0, {}


        assert scorer_accepts_trajectory(ThreeArg()) is False
        assert scorer_accepts_trajectory(WithTrajectory()) is True
        ```

    Notes:
        Uses stdlib ``inspect`` only. Adapters call it once per adapter
        instance, not once per evaluated row.
    """
    method = getattr(scorer, "async_score", None)
    if method is None:
        return False
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        return False
    parameter = parameters.get("trajectory")
    return parameter is not None and parameter.kind in _KEYWORD_KINDS
