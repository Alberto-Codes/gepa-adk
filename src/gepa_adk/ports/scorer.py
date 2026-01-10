"""Protocol definition for scoring agent outputs.

This module defines the Scorer protocol that enables custom scoring logic
for evaluating agent outputs in the evolution engine. The protocol provides
both synchronous and asynchronous methods, returning a tuple of score and
metadata.

Attributes:
    Scorer (protocol): Protocol for scoring agent outputs.

Examples:
    Implement a simple exact-match scorer:

    ```python
    from gepa_adk.ports import Scorer


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

Note:
    The protocol defines both synchronous and asynchronous scoring methods
    to support various use cases. Score values should be normalized between
    0.0 and 1.0 by convention, with higher values indicating better performance.
    The protocol does not enforce this range.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


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
        from gepa_adk.ports import Scorer

        scorer = FixedScorer()
        assert isinstance(scorer, Scorer)  # Runtime check works
        ```

    Note:
        All implementations must provide both score() and async_score()
        methods to satisfy the protocol. Score values should be normalized
        between 0.0 and 1.0 by convention, with higher values indicating
        better performance. The protocol does not enforce this range.
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

        Note:
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

        Note:
            Operations run asynchronously and can be executed concurrently.
            Prefer this method for I/O-bound scoring operations such as
            LLM-based evaluation or external API calls.
        """
        ...
