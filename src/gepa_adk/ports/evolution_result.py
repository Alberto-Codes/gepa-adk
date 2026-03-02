"""Protocol definition for evolution result types.

Defines a shared protocol that both ``EvolutionResult`` and
``MultiAgentEvolutionResult`` satisfy structurally, enabling engine and
utility code to accept either result type without type unions.

This is the project's first data-attribute protocol. Existing protocols in
``ports/`` are method-only. Data annotations were chosen here because the
shared surface consists of frozen dataclass fields — data annotations match
the structural reality exactly.

Attributes:
    EvolutionResultProtocol (protocol): Protocol for evolution result types
        that both single-agent and multi-agent results satisfy.

Examples:
    Type-annotate a function that accepts any result type:

    ```python
    from gepa_adk.ports import EvolutionResultProtocol


    def summarize(result: EvolutionResultProtocol) -> str:
        pct = result.improvement * 100
        return f"Improved by {pct:.1f}% over {result.total_iterations} iterations"
    ```

    Verify protocol compliance at runtime:

    ```python
    from gepa_adk.domain.models import EvolutionResult
    from gepa_adk.ports import EvolutionResultProtocol

    result = EvolutionResult(
        original_score=0.5,
        final_score=0.8,
        evolved_components={"instruction": "Be helpful"},
        iteration_history=[],
        total_iterations=5,
    )
    assert isinstance(result, EvolutionResultProtocol)
    ```

See Also:
    - [`gepa_adk.domain.models.EvolutionResult`][gepa_adk.domain.models.EvolutionResult]:
        Single-agent evolution result (frozen dataclass).
    - [`gepa_adk.domain.models.MultiAgentEvolutionResult`]\
[gepa_adk.domain.models.MultiAgentEvolutionResult]:
        Multi-agent evolution result (frozen dataclass).
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: Adapter protocol
        that produces evolution results.

Note:
    The protocol deliberately excludes mode-specific fields
    (``valset_score``, ``primary_agent``) and ``stop_reason`` (deferred
    to Epic 2, Story 2.1). Consumers needing those fields should use the
    concrete result types directly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gepa_adk.domain.models import IterationRecord


@runtime_checkable
class EvolutionResultProtocol(Protocol):
    """Protocol for evolution result types.

    Both ``EvolutionResult`` and ``MultiAgentEvolutionResult`` satisfy this
    protocol structurally. Consumers that need the common shape program
    against this protocol; consumers that need mode-specific data
    (``valset_score``, ``primary_agent``) use the concrete type.

    Attributes:
        original_score (float): Starting performance score (baseline).
        final_score (float): Ending performance score (best achieved).
        evolved_components (dict[str, str]): Maps component names to their
            final evolved text values.
        iteration_history (list[IterationRecord]): Chronological list of
            iteration records.
        total_iterations (int): Number of iterations performed.

    Examples:
        Accept any evolution result type:

        ```python
        from gepa_adk.ports import EvolutionResultProtocol


        def log_result(result: EvolutionResultProtocol) -> None:
            print(f"Score: {result.original_score} -> {result.final_score}")
            print(f"Improved: {result.improved} ({result.improvement:+.2f})")
        ```

        Runtime isinstance check:

        ```python
        from gepa_adk.domain.models import MultiAgentEvolutionResult
        from gepa_adk.ports import EvolutionResultProtocol

        result = MultiAgentEvolutionResult(
            evolved_components={"agent.instruction": "Be precise"},
            original_score=0.4,
            final_score=0.7,
            primary_agent="agent",
            iteration_history=[],
            total_iterations=8,
        )
        assert isinstance(result, EvolutionResultProtocol)
        ```

    Note:
        ``stop_reason`` is intentionally excluded from this protocol
        definition. It will be added in Epic 2, Story 2.1 when the field
        is added to both result types.
    """

    original_score: float
    final_score: float
    evolved_components: dict[str, str]
    iteration_history: list[IterationRecord]
    total_iterations: int

    @property
    def improvement(self) -> float:
        """Calculate score improvement from original to final.

        Returns:
            Difference between final_score and original_score.
        """
        ...

    @property
    def improved(self) -> bool:
        """Check if the final score is better than the original.

        Returns:
            True if final_score > original_score.
        """
        ...


__all__ = ["EvolutionResultProtocol"]
