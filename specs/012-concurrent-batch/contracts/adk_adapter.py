"""Contract specification for ADKAdapter concurrent batch evaluation.

This module defines the behavioral contracts that the ADKAdapter must satisfy
for concurrent batch evaluation. These contracts serve as the specification
for both implementation and testing.

Note:
    This is a design artifact, not executable code. It documents the expected
    behavior that tests will verify.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConcurrentEvaluationContract(Protocol):
    """Contract for concurrent batch evaluation behavior.

    The ADKAdapter MUST satisfy these behavioral requirements when
    evaluating batches with concurrent execution.
    """

    # ==========================================================================
    # CONCURRENCY CONTROL CONTRACTS
    # ==========================================================================

    def contract_respects_concurrency_limit(self) -> None:
        """FR-002: At most max_concurrent_evals evaluations run simultaneously.

        Given:
            - max_concurrent_evals = N
            - batch_size > N

        When:
            - evaluate() is called

        Then:
            - At any point in time, at most N evaluations are executing
            - Semaphore controls access to evaluation resources
        """
        ...

    def contract_accepts_concurrency_configuration(self) -> None:
        """FR-003: Users can configure maximum concurrent evaluations.

        Given:
            - ADKAdapter constructed with max_concurrent_evals parameter

        When:
            - evaluate() is called

        Then:
            - Concurrency respects the configured limit
            - Default value (5) is used when not specified
        """
        ...

    def contract_validates_concurrency_parameter(self) -> None:
        """Edge case: Invalid concurrency values are rejected.

        Given:
            - max_concurrent_evals <= 0

        When:
            - ADKAdapter is constructed

        Then:
            - ValueError is raised
            - Error message indicates invalid configuration
        """
        ...

    # ==========================================================================
    # PARALLEL EXECUTION CONTRACTS
    # ==========================================================================

    def contract_executes_batch_in_parallel(self) -> None:
        """FR-001: Batch evaluations execute in parallel.

        Given:
            - batch_size = 10
            - max_concurrent_evals = 5
            - Each evaluation takes ~T seconds

        When:
            - evaluate() is called

        Then:
            - Total time is approximately (batch_size / max_concurrent_evals) * T
            - Not batch_size * T (sequential behavior)
        """
        ...

    def contract_preserves_result_ordering(self) -> None:
        """FR-009: Results maintain input order.

        Given:
            - batch = [example_0, example_1, ..., example_N]

        When:
            - evaluate() is called with parallel execution

        Then:
            - outputs[i] corresponds to batch[i]
            - scores[i] corresponds to batch[i]
            - trajectories[i] corresponds to batch[i] (if captured)
        """
        ...

    # ==========================================================================
    # ERROR HANDLING CONTRACTS
    # ==========================================================================

    def contract_continues_on_individual_failure(self) -> None:
        """FR-005: Individual failures don't block other evaluations.

        Given:
            - batch with some examples that will fail
            - Other examples that will succeed

        When:
            - evaluate() is called

        Then:
            - Successful examples complete normally
            - Failed examples don't prevent other completions
            - All results are returned (success and failure)
        """
        ...

    def contract_captures_error_information(self) -> None:
        """FR-006: Failed evaluations include error details.

        Given:
            - An example that fails during evaluation

        When:
            - evaluate() completes

        Then:
            - The corresponding trajectory.error contains error message
            - Error message is actionable (includes exception type/details)
        """
        ...

    def contract_assigns_zero_score_to_failures(self) -> None:
        """FR-007: Failed evaluations receive score of 0.0.

        Given:
            - An example that fails during evaluation

        When:
            - evaluate() completes

        Then:
            - scores[i] == 0.0 for the failed example
        """
        ...

    def contract_returns_empty_output_for_failures(self) -> None:
        """FR-006/FR-008: Failed evaluations have empty output.

        Given:
            - An example that fails during evaluation

        When:
            - evaluate() completes

        Then:
            - outputs[i] == "" for the failed example
        """
        ...

    def contract_returns_complete_result_set(self) -> None:
        """FR-008: Always returns complete result set.

        Given:
            - batch of N examples
            - Some may succeed, some may fail

        When:
            - evaluate() completes

        Then:
            - len(outputs) == N
            - len(scores) == N
            - len(trajectories) == N (if capture_traces=True)
        """
        ...

    # ==========================================================================
    # TRAJECTORY CAPTURE CONTRACTS
    # ==========================================================================

    def contract_supports_trajectory_capture(self) -> None:
        """FR-010: Trajectory capture works in parallel execution.

        Given:
            - capture_traces=True

        When:
            - evaluate() completes with parallel execution

        Then:
            - trajectories is not None
            - Each trajectory contains valid execution trace
            - Failed examples have error trajectories
        """
        ...

    # ==========================================================================
    # EDGE CASE CONTRACTS
    # ==========================================================================

    def contract_handles_empty_batch(self) -> None:
        """Edge case: Empty batch returns empty result.

        Given:
            - batch = []

        When:
            - evaluate() is called

        Then:
            - Returns EvaluationBatch(outputs=[], scores=[], trajectories=None)
            - No errors raised
        """
        ...

    def contract_handles_all_failures(self) -> None:
        """Edge case: All evaluations fail.

        Given:
            - batch where every example will fail

        When:
            - evaluate() completes

        Then:
            - Returns complete result set with all failures
            - All outputs are ""
            - All scores are 0.0
            - All trajectories have error field set
        """
        ...

    def contract_handles_concurrency_larger_than_batch(self) -> None:
        """Edge case: Concurrency limit exceeds batch size.

        Given:
            - max_concurrent_evals = 10
            - batch_size = 3

        When:
            - evaluate() is called

        Then:
            - All 3 examples run concurrently
            - No errors or unexpected behavior
        """
        ...
