"""Async evolution engine implementation.

This module contains the AsyncGEPAEngine class that orchestrates the
core evolution loop for optimizing agent instructions using async-first
design principles.

Attributes:
    AsyncGEPAEngine (class): Main evolution engine class that runs the
        evaluate-reflect-propose-accept loop.
    DataInst (TypeVar): Type variable for data instances in the batch.
    Trajectory (TypeVar): Type variable for execution trajectories.
    RolloutOutput (TypeVar): Type variable for rollout outputs.

Examples:
    Running an evolution loop:

    ```python
    from gepa_adk.engine import AsyncGEPAEngine
    from gepa_adk.domain.models import EvolutionConfig, Candidate

    engine = AsyncGEPAEngine(
        adapter=my_adapter,
        config=EvolutionConfig(max_iterations=50),
        initial_candidate=Candidate(components={"instruction": "Be helpful"}),
        batch=training_data,
    )
    result = await engine.run()
    ```

See Also:
    - [`gepa_adk.engine.proposer`][gepa_adk.engine.proposer]: Reflective mutation
      proposer used for generating candidate text.
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: AsyncGEPAAdapter protocol
      that the engine delegates evaluation to.
    - [`gepa_adk.domain.models`][gepa_adk.domain.models]: Domain models (Candidate,
      EvolutionConfig, EvolutionResult) used throughout the engine.
    - [`gepa_adk.domain.state`][gepa_adk.domain.state]: ParetoState for
      multi-objective candidate tracking.

Notes:
    Tracks separate trainset and valset evaluation flows for evolution.
    When the valset is the trainset (omitted, or the same list object),
    scoring reuses each candidate's reflection batch instead of
    evaluating it a second time.
    A reflection that stays empty after the proposer's retry raises
    ``EmptyProposalError``; the loop records it as a skipped iteration
    instead of aborting the run. A reflection that times out raises
    ``ReflectionTimeoutError``, which the loop records the same way with
    ``skip_reason="reflection_timeout"``. A reflection function that keeps
    raising a retryable provider error after the proposer's retry raises a
    retryable ``ReflectionError``, recorded with
    ``skip_reason="reflection_error"``; a non-retryable one aborts the run.
    An ``EvolutionError`` that aborts the run after the baseline was scored
    carries the partial result (``StopReason.ERROR``) in ``partial_result``.
    A proposal or merge candidate whose ``Candidate.id`` was already scored
    is not evaluated again; merge results are typed as ``ProposalResult``.
    Each appended iteration record, skipped iterations included, is passed
    to ``EvolutionConfig.on_iteration`` (sync or async) with the id of the
    candidate it concerns.
    With ``EvolutionConfig.reflection_minibatch_size`` smaller than the
    trainset, each proposal first runs on a fresh seeded sample of the
    trainset and earns its full evaluation only by beating its parent's
    cached scores on those rows.
    Every adapter evaluation folds the token usage its rows' trajectories
    report into a per-iteration and a run ``TokenRollup``; rows without
    usage are counted as unknown, never as zero.
    Supports optional Pareto-based candidate selection, component-level
    mutation, evaluation policies, merge proposals, custom stoppers,
    stop reason tracking via ``StopReason``, graceful interrupt handling
    that returns partial results on ``KeyboardInterrupt`` or
    ``asyncio.CancelledError``, and seed-based determinism via an
    optional ``rng`` parameter for reproducible evolutionary trajectories.
    An evaluation policy without a candidate selector raises
    ``ConfigurationError`` at construction, because the policy acts only
    through the selector's Pareto state.
    With ``EvolutionConfig.checkpoint_path`` set, the engine writes its state
    atomically after the baseline and after every recorded iteration; with
    ``resume=True`` it restores that state instead of evaluating the
    baseline. A checkpoint path with a candidate selector raises
    ``ConfigurationError`` at construction. The checkpoint carries the run's
    token rollup, so a resumed run reports the whole run's usage; a checkpoint
    without one reads its evaluated rows as unknown.
"""

from __future__ import annotations

import asyncio
import inspect
import math
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

import structlog

from gepa_adk.adapters.selection.component_selector import RoundRobinComponentSelector
from gepa_adk.domain.exceptions import (
    ConfigurationError,
    EmptyProposalError,
    EvolutionError,
    InvalidScoreListError,
    NoCandidateAvailableError,
    ReflectionError,
    ReflectionTimeoutError,
    SchemaValidationError,
)
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
    TokenRollup,
)
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.stopper import StopperState
from gepa_adk.domain.types import (
    DEFAULT_COMPONENT_NAME,
    FrontierType,
    ProposalResult,
    StopReason,
)
from gepa_adk.engine.checkpoint import (
    CHECKPOINT_VERSION,
    batch_from_dict,
    batch_to_dict,
    check_run_matches,
    read_checkpoint,
    rng_state_from_json,
    rng_state_to_json,
    write_checkpoint,
)
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
from gepa_adk.ports.candidate_selector import CandidateSelectorProtocol
from gepa_adk.ports.component_selector import ComponentSelectorProtocol
from gepa_adk.ports.evaluation_policy import EvaluationPolicyProtocol
from gepa_adk.ports.proposer import ProposerProtocol

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")

logger = structlog.get_logger(__name__)

_ZERO_TOKENS = TokenRollup(
    input_tokens=0, output_tokens=0, total_tokens=0, rows_counted=0, rows_unknown=0
)


def _unknown_tokens(rows: int) -> TokenRollup:
    """Build the rollup for evaluated rows whose usage was never recorded.

    Args:
        rows: Number of rows already evaluated, each counted as unknown.

    Returns:
        A rollup with unknown counters and ``rows_unknown=rows``.

    Notes:
        Used when a checkpoint written before token usage was stored is
        resumed, so the pre-resume rows read as unknown rather than free.
    """
    return TokenRollup(
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        rows_counted=0,
        rows_unknown=rows,
    )


def _select_batch_rows(batch: EvaluationBatch, indices: list[int]) -> EvaluationBatch:
    """Build a batch holding only the given rows of an existing batch.

    Args:
        batch: Source batch whose per-example lists are index-aligned.
        indices: Row indices to keep, in the order they should appear.

    Returns:
        A new batch with every present per-example field restricted to
        ``indices``. Fields that are ``None`` on the source stay ``None``.

    Examples:
        ```python
        subset = _select_batch_rows(batch, [0, 2])
        assert subset.scores == [batch.scores[0], batch.scores[2]]
        ```
    """
    trajectories, objective_scores, metadata, inputs = (
        batch.trajectories,
        batch.objective_scores,
        batch.metadata,
        batch.inputs,
    )
    return EvaluationBatch(
        outputs=[batch.outputs[i] for i in indices],
        scores=[batch.scores[i] for i in indices],
        trajectories=(
            None if trajectories is None else [trajectories[i] for i in indices]
        ),
        objective_scores=(
            None if objective_scores is None else [objective_scores[i] for i in indices]
        ),
        metadata=None if metadata is None else [metadata[i] for i in indices],
        inputs=None if inputs is None else [inputs[i] for i in indices],
    )


@dataclass
class _EngineState:
    """Internal mutable state during evolution run.

    This class holds the state that changes during a single evolution
    run. It is not exposed publicly and is converted to a frozen
    EvolutionResult at the end of the run.

    Attributes:
        best_candidate (Candidate): Best candidate found so far.
        best_score (float): Acceptance score of best candidate (sum or mean
            based on acceptance_metric).
        original_score (float): Baseline acceptance score from first evaluation.
        iteration (int): Current iteration number (0-based internally,
            1-indexed in records).
        stagnation_counter (int): Iterations since last improvement.
        iteration_history (list[IterationRecord]): All iteration records.
        last_eval_batch (EvaluationBatch | None): Cached reflection batch from
            most recent best candidate evaluation on the trainset (for
            reflective dataset generation).
        best_reflection_score (float): Mean score from the best candidate's
            latest trainset reflection evaluation.
        best_valset_mean (float | None): Mean valset score of best candidate.
            None if no valset provided or not yet evaluated.
        best_objective_scores (list[dict[str, float]] | None): Objective scores
            from the best candidate's evaluation. None when adapter does not
            provide objective scores.
        baseline_failed_evaluations (int): Rows whose agent run failed during
            the baseline evaluation, from ``EvaluationBatch.failed_indices``.

    Examples:
        Creating initial engine state from a baseline evaluation:

        ```python
        state = _EngineState(
            best_candidate=initial_candidate,
            best_score=baseline_score,
            original_score=baseline_score,
        )
        ```

    Notes:
        Aggregates reflection metadata needed to drive proposal generation.
        Tracks acceptance score (sum/mean) separately from valset mean.
    """

    # Required fields (no defaults) - must come first
    best_candidate: Candidate
    best_score: float
    original_score: float
    # Optional fields (with defaults)
    iteration: int = 0
    stagnation_counter: int = 0
    iteration_history: list[IterationRecord] = field(default_factory=list)
    last_eval_batch: EvaluationBatch | None = None
    best_reflection_score: float = 0.0
    best_valset_mean: float | None = None
    best_objective_scores: list[dict[str, float]] | None = None
    baseline_failed_evaluations: int = 0


class AsyncGEPAEngine(Generic[DataInst, Trajectory, RolloutOutput]):
    """Async evolution engine orchestrating the GEPA loop.

    This engine executes the core evolution algorithm:
    1. Evaluate baseline candidate
    2. For each iteration until max_iterations or convergence:
       a. Generate reflective dataset from traces
       b. Propose new candidate text (an empty reflection after one retry,
          or a reflection that times out, records a skipped iteration and
          moves on)
       c. Evaluate proposal
       d. Accept if improves above threshold
       e. Record iteration
    3. Return frozen EvolutionResult

    Attributes:
        adapter (AsyncGEPAAdapter): Implementation of AsyncGEPAAdapter protocol.
        config (EvolutionConfig): Evolution parameters.

    Examples:
        Basic usage:

        ```python
        from gepa_adk.engine import AsyncGEPAEngine
        from gepa_adk.domain.models import EvolutionConfig, Candidate

        engine = AsyncGEPAEngine(
            adapter=my_adapter,
            config=EvolutionConfig(max_iterations=50),
            initial_candidate=Candidate(components={"instruction": "Be helpful"}),
            batch=training_data,
        )
        result = await engine.run()
        print(f"Final score: {result.final_score}")
        ```

    Notes:
        Avoid reusing engine instances after run() completes.
        When a seeded ``rng`` is provided, it is used for the auto-created
        merge proposer. The API layer passes the same ``rng`` to candidate
        selectors for full determinism across stochastic components.
        Evaluation, acceptance, reuse, Pareto and merge log events carry
        ``candidate_id`` (``Candidate.id``) as the per-candidate correlation
        key. Rows named in ``EvaluationBatch.failed_indices`` are counted per
        iteration and reported on the result, and so is the token usage the
        evaluated rows' trajectories report (``TokenRollup``). A proposal whose
        ``Candidate.id`` was already scored in the run is not evaluated
        again; its iteration is recorded with ``skip_reason="duplicate"``.
        A proposal whose ``output_schema`` text fails validation is not
        evaluated; its iteration is recorded with
        ``skip_reason="schema_validation_failed"`` and counts toward
        stagnation, so ``max_iterations``, ``patience`` and stoppers still
        end the run. A retryable ``ReflectionError`` (the proposer already
        retried once) is recorded the same way with
        ``skip_reason="reflection_error"``; a non-retryable one aborts the
        run with the partial result attached to the error.
        A merge candidate that is already scored or has an invalid schema is
        not evaluated, and the iteration that scheduled it is still recorded.
        An evaluation policy takes effect only through the Pareto state that
        a candidate selector creates. No policy and no selector is full
        evaluation; a selector alone is full evaluation over the Pareto
        state; a selector with a policy uses the policy; a policy without a
        selector raises ``ConfigurationError`` at construction.
        With ``config.reflection_minibatch_size`` smaller than the trainset,
        a proposal runs first on a fresh seeded sample of trainset rows and
        is evaluated in full only when its mean there beats the parent's
        cached scores on the same rows; otherwise its iteration is recorded
        with ``skip_reason="minibatch_rejected"``.
        With ``config.checkpoint_path`` set, state is checkpointed after the
        baseline and after every recorded iteration, and ``config.resume``
        continues a run from that file (see ``_resume_from_checkpoint``).
    """

    def __init__(
        self,
        adapter: AsyncGEPAAdapter[DataInst, Trajectory, RolloutOutput],
        config: EvolutionConfig,
        initial_candidate: Candidate,
        batch: list[DataInst],
        valset: list[DataInst] | None = None,
        candidate_selector: CandidateSelectorProtocol | None = None,
        component_selector: ComponentSelectorProtocol | None = None,
        evaluation_policy: EvaluationPolicyProtocol | None = None,
        merge_proposer: ProposerProtocol | None = None,
        rng: random.Random | None = None,
    ) -> None:
        """Initialize the evolution engine.

        Args:
            adapter: Implementation of AsyncGEPAAdapter protocol for evaluation
                and proposal generation.
            config: Evolution parameters controlling iterations, thresholds,
                and early stopping.
            initial_candidate: Starting candidate with at least one component.
            batch: Trainset data instances for reflection and mutation.
            valset: Optional validation data for scoring candidates. Defaults
                to trainset when omitted. Must be non-empty if provided.
            candidate_selector: Optional selector strategy for Pareto-aware
                candidate sampling. When provided, initializes ParetoState
                for multi-objective tracking.
            component_selector: Optional selector strategy for choosing which
                components to update. Defaults to RoundRobinComponentSelector.
            evaluation_policy: Optional policy for selecting which validation
                examples to evaluate per iteration. Defaults to
                FullEvaluationPolicy. Requires ``candidate_selector``, because
                the policy acts only through the Pareto state the selector
                creates.
            merge_proposer: Optional proposer for merge operations. If provided
                and config.use_merge is True, merge proposals will be attempted
                after successful mutations.
            rng: Optional seeded random.Random instance for deterministic engine
                decisions. When provided, used for the auto-created merge
                proposer and for drawing reflection minibatch rows. None
                preserves current random behavior, and minibatch rows are then
                drawn from a ``random.Random(config.seed)``.

        Raises:
            ValueError: If batch is empty, valset is provided but empty,
                or initial_candidate has no components.
            ConfigurationError: If evaluation_policy is provided without a
                candidate_selector, including an explicit FullEvaluationPolicy,
                or if ``config.checkpoint_path`` is set together with a
                candidate_selector (Pareto state is not checkpointed).

        Examples:
            Creating an engine:

            ```python
            engine = AsyncGEPAEngine(
                adapter=my_adapter,
                config=EvolutionConfig(max_iterations=50),
                initial_candidate=Candidate(components={"instruction": "Be helpful"}),
                batch=training_data,
                candidate_selector=selector,
            )
            ```

        Notes:
            Configures trainset and valset routing for reflection and scoring.
            A valset that is the same object as the batch (or omitted) marks
            the engine to reuse reflection batches for scoring.
            Initializes stopper lifecycle tracking for custom stop callbacks.
            Initializes the evaluation and pending failure counters, the
            pending and run token rollups, the map from each scored
            candidate's id to its acceptance score, the random source for
            reflection minibatch rows and the slot holding the last mutation
            parent's trainset batch.
            Valid selector and policy combinations: neither is full
            evaluation; a selector alone is full evaluation over the Pareto
            state; a selector with a policy uses that policy; a policy alone
            is rejected. A checkpoint path with a candidate selector is
            rejected too, and the restored-state flag starts False.
        """
        # Validation
        if len(batch) == 0:
            raise ValueError("batch must contain at least one data instance")
        if valset is not None and len(valset) == 0:
            raise ValueError(
                "valset must contain at least one validation data instance"
            )

        if not initial_candidate.components:
            raise ValueError("initial_candidate must have at least one component")

        if evaluation_policy is not None and candidate_selector is None:
            raise ConfigurationError(
                "evaluation_policy requires a candidate_selector: a policy "
                "takes effect only through the Pareto state a candidate "
                "selector creates",
                field="evaluation_policy",
                value=type(evaluation_policy).__name__,
                constraint="candidate_selector is not None",
            )

        if config.checkpoint_path is not None and candidate_selector is not None:
            raise ConfigurationError(
                "checkpoint_path cannot be combined with a candidate_selector: "
                "Pareto state is not checkpointed yet",
                field="candidate_selector",
                value=type(candidate_selector).__name__,
                constraint="candidate_selector is None when checkpoint_path is set",
            )

        # Store dependencies
        self.adapter = adapter
        self.config = config
        self._initial_candidate = initial_candidate
        self._trainset = batch
        self._valset = valset if valset is not None else batch
        # Identity, not equality: an equal-but-separate valset is scored apart.
        self._valset_is_trainset = self._valset is self._trainset
        self._state: _EngineState | None = None
        self._rng = rng
        # Draws each iteration's reflection minibatch rows
        self._minibatch_rng = rng if rng is not None else random.Random(config.seed)
        # Full trainset batch of the parent the last mutation reflected on
        self._mutation_parent_batch: EvaluationBatch | None = None
        self._candidate_selector = candidate_selector
        self._component_selector = component_selector or RoundRobinComponentSelector()
        self._pareto_state: ParetoState | None = None
        self._candidate_eval_batches: dict[int, EvaluationBatch] = {}
        # Acceptance score of every candidate scored this run, keyed by id
        self._scored: dict[str, float] = {}
        if merge_proposer is not None:
            self._merge_proposer = merge_proposer
        elif config.use_merge:
            from gepa_adk.engine.merge_proposer import MergeProposer

            self._merge_proposer = MergeProposer(rng=rng or random.Random())
        else:
            self._merge_proposer = None
        self._merges_due: int = 0
        self._merge_invocations: int = 0
        # Stopper state tracking (T001, T002)
        self._start_time: float | None = None
        self._total_evaluations: int = 0
        # Failed rows evaluated since the last record (see _count_batch)
        self._pending_failed_evaluations: int = 0
        # Token usage since the last record and over the run (see _count_batch)
        self._pending_token_usage: TokenRollup = _ZERO_TOKENS
        self._run_token_usage: TokenRollup = _ZERO_TOKENS
        self._active_stoppers: list[object] = []
        # True once run() restored state from a checkpoint (skips the baseline)
        self._restored: bool = False
        # Import here to avoid circular dependency
        if evaluation_policy is None:
            from gepa_adk.adapters.selection.evaluation_policy import (
                FullEvaluationPolicy,
            )

            self._evaluation_policy: EvaluationPolicyProtocol = FullEvaluationPolicy()
        else:
            self._evaluation_policy = evaluation_policy

    def _take_pending_failed_evaluations(self) -> int:
        """Return the pending failure count and reset it to zero.

        Returns:
            Failed rows counted by ``_count_batch`` since the last call.
        """
        count = self._pending_failed_evaluations
        self._pending_failed_evaluations = 0
        return count

    def _take_pending_token_usage(self) -> TokenRollup:
        """Return the pending token rollup and reset it to zero.

        Returns:
            Token usage folded in by ``_count_batch`` since the last call.
        """
        usage = self._pending_token_usage
        self._pending_token_usage = _ZERO_TOKENS
        return usage

    def _aggregate_acceptance_score(self, scores: list[float]) -> float:
        """Aggregate scores for acceptance decisions based on acceptance_metric.

        Args:
            scores: List of per-example scores from evaluation batch.

        Returns:
            Aggregated acceptance score (sum or mean based on config).

        Raises:
            InvalidScoreListError: If scores list is empty or contains
                non-finite values.

        Notes:
            Sums or averages acceptance scores after validating they are
            non-empty and finite. Uses sum or mean based on config.acceptance_metric.
        """
        # Validate scores are non-empty
        if not scores:
            raise InvalidScoreListError(
                "Cannot aggregate acceptance score from empty score list",
                scores=scores,
                reason="empty",
            )

        # Validate scores are finite
        if not all(math.isfinite(score) for score in scores):
            raise InvalidScoreListError(
                "Cannot aggregate acceptance score from non-finite values (NaN/inf)",
                scores=scores,
                reason="non-finite",
            )

        # Aggregate based on acceptance_metric
        if self.config.acceptance_metric == "sum":
            return sum(scores)
        else:  # acceptance_metric == "mean"
            return sum(scores) / len(scores)

    def _setup_stoppers(self) -> list[object]:
        """Call setup() on stoppers that have lifecycle methods.

        Returns:
            List of stoppers that had setup() called (for cleanup in reverse order).

        Notes:
            Only invokes setup() on stoppers implementing the lifecycle method.
            Stoppers that fail setup() are excluded from stop_callbacks for the
            remainder of execution to prevent inconsistent state.
        """
        setup_stoppers: list[object] = []
        active_stoppers: list[object] = []
        stop_callbacks = self.config.stop_callbacks
        if stop_callbacks:
            for stopper in stop_callbacks:
                setup_method = getattr(stopper, "setup", None)
                if setup_method is not None and callable(setup_method):
                    try:
                        setup_method()
                        setup_stoppers.append(stopper)
                        active_stoppers.append(stopper)
                    except Exception:
                        logger.exception(
                            "stopper.setup_error",
                            stopper=type(stopper).__name__,
                        )
                        # Stopper excluded from active list due to setup failure
                else:
                    # Stopper has no setup() method, still active
                    active_stoppers.append(stopper)
        # Store active stoppers for _should_stop() to use
        self._active_stoppers = active_stoppers
        return setup_stoppers

    def _cleanup_stoppers(self, setup_stoppers: list[object]) -> None:
        """Call cleanup() on stoppers in reverse order of setup.

        Args:
            setup_stoppers: List of stoppers that had setup() called.

        Notes:
            Follows the reverse-order cleanup contract (T025).
            When cleanup() raises, logs the error and continues (T026).
        """
        for stopper in reversed(setup_stoppers):
            cleanup_method = getattr(stopper, "cleanup", None)
            if cleanup_method is not None and callable(cleanup_method):
                try:
                    cleanup_method()
                except Exception:
                    logger.exception(
                        "stopper.cleanup_error",
                        stopper=type(stopper).__name__,
                    )

    def _build_stopper_state(self) -> StopperState:
        """Build a StopperState snapshot from current engine state.

        Constructs an immutable snapshot of evolution state for stopper
        callbacks to evaluate. Captures all metrics needed by stoppers
        including elapsed time and total evaluations.

        Returns:
            Frozen StopperState containing current iteration, best score,
            stagnation counter, total evaluations, candidates count, and
            elapsed time.

        Notes:
            Obtains elapsed_seconds from monotonic time since run() started.
            Uses zero if _start_time has not yet been set.
        """
        assert self._state is not None, "Engine state not initialized"
        elapsed = (
            time.monotonic() - self._start_time if self._start_time is not None else 0.0
        )
        candidates_count = (
            len(self._pareto_state.candidates) if self._pareto_state is not None else 0
        )
        return StopperState(
            iteration=self._state.iteration,
            best_score=self._state.best_score,
            stagnation_counter=self._state.stagnation_counter,
            total_evaluations=self._total_evaluations,
            candidates_count=candidates_count,
            elapsed_seconds=elapsed,
        )

    @property
    def pareto_state(self) -> ParetoState | None:
        """Return the current Pareto state, if initialized."""
        return self._pareto_state

    def _build_component_list(self, candidate: Candidate) -> list[str]:
        """Build list of available component keys from candidate.

        Excludes generic 'instruction' alias if agent-specific keys exist
        (e.g., 'agent1_instruction').

        Args:
            candidate: Candidate to extract component keys from.

        Returns:
            List of component keys to consider for update.

        Notes:
            Selects component keys, filtering out the default component name when
            more specific per-agent component keys are present.
        """
        keys = list(candidate.components.keys())
        if len(keys) > 1 and DEFAULT_COMPONENT_NAME in keys:
            # If multiple keys exist, assume default component might be an alias/proxy
            # or simply one of many.
            # For now, simplistic rule: if other keys exist, exclude default.
            return [k for k in keys if k != DEFAULT_COMPONENT_NAME]
        return keys

    def _count_batch(
        self, candidate: Candidate, batch: EvaluationBatch, phase: str
    ) -> None:
        """Count one adapter evaluation and log it under the candidate's id.

        Adds the batch's rows to the evaluation counter that stoppers read
        and its ``failed_indices`` to the failures pending for the next
        record (the baseline or the current iteration), folds the batch's
        ``TokenRollup`` into the pending and the run token rollups, then logs
        ``evaluation.completed`` with the candidate's id, the phase, the row
        count and that same failure count.

        Args:
            candidate: Candidate whose components were evaluated.
            batch: Evaluation batch the adapter just returned.
            phase: ``"reflection"`` for a trainset evaluation with traces,
                ``"scoring"`` for a valset evaluation.

        Notes:
            Called once per adapter ``evaluate()`` call, so a reused batch
            is neither counted nor logged, because no row was evaluated
            again. An adapter that leaves ``failed_indices`` as None reports
            zero failures.
        """
        failed = len(batch.failed_indices or [])
        self._total_evaluations += len(batch.scores)
        self._pending_failed_evaluations += failed
        usage = TokenRollup.from_batch(batch)
        self._pending_token_usage = self._pending_token_usage.combine(usage)
        self._run_token_usage = self._run_token_usage.combine(usage)
        logger.debug(
            "evaluation.completed",
            candidate_id=candidate.id,
            phase=phase,
            n=len(batch.scores),
            failed=failed,
            iteration=self._state.iteration if self._state is not None else 0,
        )

    async def _initialize_baseline(self) -> None:
        """Initialize baseline evaluation.

        Evaluates the initial candidate on trainset for reflection and
        on valset for scoring. Caches the reflection batch for use in
        the first mutation proposal. When the valset is the trainset, the
        reflection batch also serves scoring, so the baseline is evaluated
        once.

        Notes:
            Sets up both reflection and scoring baselines up front. The
            baseline evaluation is counted and logged via ``_count_batch``.
            Rows that failed during these evaluations are stored on the state
            as ``baseline_failed_evaluations``. The baseline's token usage
            stays in the run rollup and is cleared from the pending one, so
            the first iteration's record does not include it. Ends by writing
            a checkpoint through ``_write_checkpoint`` when
            ``config.checkpoint_path`` is set.
        """
        # Create pareto_state before evaluation if candidate_selector exists
        # so that _evaluate_scoring can use evaluation_policy
        if self._candidate_selector is not None:
            self._pareto_state = ParetoState(frontier_type=self.config.frontier_type)

        reflection_batch = await self.adapter.evaluate(
            self._trainset,
            self._initial_candidate.components,
            capture_traces=True,
        )
        self._count_batch(self._initial_candidate, reflection_batch, "reflection")
        # Use _evaluate_scoring for baseline to get eval_indices
        (
            baseline_score,
            scoring_batch,
            baseline_eval_indices,
        ) = await self._evaluate_scoring(
            self._initial_candidate, reflection_batch=reflection_batch
        )
        baseline_reflection_score = sum(reflection_batch.scores) / len(
            reflection_batch.scores
        )
        baseline_valset_mean = (
            sum(scoring_batch.scores) / len(scoring_batch.scores)
            if scoring_batch.scores
            else 0.0
        )
        self._state = _EngineState(
            best_candidate=self._initial_candidate,
            best_score=baseline_score,
            original_score=baseline_score,
            iteration=0,
            stagnation_counter=0,
            iteration_history=[],
            last_eval_batch=reflection_batch,
            best_reflection_score=baseline_reflection_score,
            best_valset_mean=baseline_valset_mean,
            best_objective_scores=scoring_batch.objective_scores,
            baseline_failed_evaluations=self._take_pending_failed_evaluations(),
        )
        self._take_pending_token_usage()
        if self._candidate_selector is not None:
            # Prepare objective scores for baseline if needed
            objective_scores: dict[str, float] | None = None
            per_example_objective_scores: dict[int, dict[str, float]] | None = None

            if scoring_batch.objective_scores is not None:
                from statistics import fmean

                if self.config.frontier_type in (
                    FrontierType.OBJECTIVE,
                    FrontierType.HYBRID,
                ):
                    objective_scores_by_name: dict[str, list[float]] = {}
                    for obj_scores in scoring_batch.objective_scores:
                        for obj_name, obj_score in obj_scores.items():
                            objective_scores_by_name.setdefault(obj_name, []).append(
                                obj_score
                            )
                    objective_scores = {
                        obj_name: fmean(scores)
                        for obj_name, scores in objective_scores_by_name.items()
                    }

                if self.config.frontier_type == FrontierType.CARTESIAN:
                    per_example_objective_scores = {
                        baseline_eval_indices[i]: scoring_batch.objective_scores[i]
                        for i in range(len(baseline_eval_indices))
                    }
                    objective_scores_by_name: dict[str, list[float]] = {}
                    for obj_scores in scoring_batch.objective_scores:
                        for obj_name, obj_score in obj_scores.items():
                            objective_scores_by_name.setdefault(obj_name, []).append(
                                obj_score
                            )
                    objective_scores = {
                        obj_name: fmean(scores)
                        for obj_name, scores in objective_scores_by_name.items()
                    }

            assert self._pareto_state is not None, "Pareto state not initialized"
            candidate_idx = self._pareto_state.add_candidate(
                self._initial_candidate,
                scoring_batch.scores,
                score_indices=baseline_eval_indices,
                objective_scores=objective_scores,
                per_example_objective_scores=per_example_objective_scores,
                logger=logger,
            )
            self._candidate_eval_batches[candidate_idx] = reflection_batch
        self._write_checkpoint()

    async def _evaluate_reflection(
        self, candidate: Candidate
    ) -> tuple[float, EvaluationBatch]:
        """Evaluate a candidate on the trainset for reflection.

        Args:
            candidate: Candidate to evaluate.

        Returns:
            Tuple of (mean score across trainset examples, evaluation batch).

        Notes:
            Supplies trajectories for reflective dataset construction.
            The evaluation is counted and logged via ``_count_batch``.
        """
        eval_batch = await self.adapter.evaluate(
            self._trainset,
            candidate.components,
            capture_traces=True,
        )
        self._count_batch(candidate, eval_batch, "reflection")
        score = sum(eval_batch.scores) / len(eval_batch.scores)
        return score, eval_batch

    async def _evaluate_scoring(
        self,
        candidate: Candidate,
        reflection_batch: EvaluationBatch | None = None,
    ) -> tuple[float, EvaluationBatch, list[int]]:
        """Evaluate a candidate on the valset for scoring decisions.

        Args:
            candidate: Candidate to evaluate on the validation set.
            reflection_batch: The candidate's trainset reflection batch. When
                the valset is the trainset, scoring reuses this batch (or its
                entries at the selected indices) instead of calling the
                adapter again.

        Returns:
            Tuple of (aggregated acceptance score, evaluation batch, eval_indices).
            Score is aggregated using acceptance_metric (sum or mean).
            eval_indices are the valset indices that were actually evaluated.

        Notes:
            Supplies scores without traces for acceptance decisions.
            Aggregation method (sum/mean) is determined by config.acceptance_metric.
            Uses evaluation_policy to determine which examples to evaluate.
            Only the canonical ordered index list counts as a full evaluation;
            any other selection, including a permutation, is built row by row
            in the policy's order.
            A reused batch adds nothing to the evaluation or failure
            counters, because no example is evaluated again; its reuse log
            names the ``candidate_id``. The acceptance score is stored under
            the candidate's id so a later duplicate proposal is not
            evaluated again.
        """
        # Get indices to evaluate from evaluation policy
        valset_ids = list(range(len(self._valset)))
        if self._pareto_state is not None:
            eval_indices = self._evaluation_policy.get_eval_batch(
                valset_ids, self._pareto_state
            )
        else:
            # Fallback to all indices if no pareto state yet
            eval_indices = valset_ids

        # Filter valset to only include selected indices
        # Only the canonical ordered list counts as a full evaluation, so a
        # policy that permutes the indices gets a batch built in its order.
        is_full_eval = list(eval_indices) == valset_ids

        if reflection_batch is not None and self._valset_is_trainset:
            logger.debug(
                "evaluation.reuse_trainset_batch",
                candidate_id=candidate.id,
                components=sorted(candidate.components),
                reason="valset_is_trainset",
                full=is_full_eval,
                n=len(eval_indices),
            )
            eval_batch = (
                reflection_batch
                if is_full_eval
                else _select_batch_rows(reflection_batch, eval_indices)
            )
        else:
            eval_valset = (
                self._valset
                if is_full_eval
                else [self._valset[i] for i in eval_indices]
            )
            eval_batch = await self.adapter.evaluate(
                eval_valset,
                candidate.components,
                capture_traces=False,
            )
            self._count_batch(candidate, eval_batch, "scoring")
        score = self._aggregate_acceptance_score(eval_batch.scores)
        self._scored[candidate.id] = score
        return score, eval_batch, eval_indices

    async def _propose_mutation(self) -> tuple[Candidate, list[str]]:
        """Propose a new candidate via reflective mutation.

        Uses the cached evaluation batch from the most recent best candidate
        evaluation to generate the reflective dataset, avoiding redundant
        adapter calls.

        Returns:
            Tuple of (new candidate with proposed component updates,
            list of component names that were updated).

        Notes:
            Spawns a new candidate with updated components based on reflective
            dataset analysis and component selector strategy. The selected
            parent is logged with its ``candidate_id``. A fallback parent
            evaluation is counted and logged through ``_count_batch``. The
            parent's full trainset batch it reflected on is kept on the
            engine for the reflection minibatch gate.
        """
        assert self._state is not None, "Engine state not initialized"
        assert self._state.last_eval_batch is not None, "No eval batch cached"

        selected_candidate = self._state.best_candidate
        selected_idx: int | None = None
        eval_batch = self._state.last_eval_batch

        if self._candidate_selector is not None and self._pareto_state is not None:
            try:
                selected_idx = await self._candidate_selector.select_candidate(
                    self._pareto_state
                )
                selected_candidate = self._pareto_state.candidates[selected_idx]
                eval_batch = self._candidate_eval_batches.get(selected_idx)
                logger.info(
                    "pareto_selection.mutation_parent_selected",
                    candidate_idx=selected_idx,
                    candidate_id=selected_candidate.id,
                    iteration=self._state.iteration,
                    selector_type=type(self._candidate_selector).__name__,
                )
            except NoCandidateAvailableError as exc:
                logger.info(
                    "pareto_selection.empty_frontier_fallback",
                    iteration=self._state.iteration,
                    selector_type=type(self._candidate_selector).__name__,
                    error=str(exc),
                )
                eval_batch = self._state.last_eval_batch

        if eval_batch is None:
            eval_batch = await self.adapter.evaluate(
                self._trainset,
                selected_candidate.components,
                capture_traces=True,
            )
            self._count_batch(selected_candidate, eval_batch, "reflection")
            if selected_idx is not None:
                self._candidate_eval_batches[selected_idx] = eval_batch
        # The minibatch gate compares the proposal with this parent batch
        self._mutation_parent_batch = eval_batch

        # Build component list
        available_components = self._build_component_list(selected_candidate)

        # Select components to update
        components_to_update = await self._component_selector.select_components(
            components=available_components,
            iteration=self._state.iteration,
            candidate_idx=selected_idx if selected_idx is not None else 0,
        )

        logger.info(
            "mutation.components_selected",
            iteration=self._state.iteration,
            components=components_to_update,
            selector=type(self._component_selector).__name__,
        )

        # Build reflective dataset
        reflective_dataset = await self.adapter.make_reflective_dataset(
            selected_candidate.components,
            eval_batch,
            components_to_update,
        )

        # Propose new texts
        proposed_components = await self.adapter.propose_new_texts(
            selected_candidate.components,
            reflective_dataset,
            components_to_update,
        )

        # Create new candidate with proposed components
        new_components = dict(selected_candidate.components)
        new_components.update(proposed_components)
        return (
            Candidate(
                components=new_components,
                generation=selected_candidate.generation,
                parent_id=selected_candidate.parent_id,
            ),
            components_to_update,
        )

    async def _record_iteration(
        self,
        score: float,
        component_text: str,
        evolved_component: str,
        accepted: bool,
        objective_scores: list[dict[str, float]] | None = None,
        reflection_reasoning: str | None = None,
        skip_reason: str | None = None,
        candidate_id: str | None = None,
    ) -> None:
        """Record iteration outcome and notify the ``on_iteration`` callback.

        Args:
            score: Score achieved in this iteration.
            component_text: The text of the component that was evaluated.
            evolved_component: The name of the component that was evolved
                (e.g., "instruction", "output_schema").
            accepted: Whether proposal was accepted.
            objective_scores: Optional objective scores from this iteration's
                evaluation. None when adapter does not provide objective scores.
            reflection_reasoning: Optional natural language reasoning from
                the reflection agent explaining the mutation. None when
                reasoning is not available.
            skip_reason: Why the iteration produced no evaluated proposal
                (e.g., ``"empty_proposal"``). None for ordinary iterations.
            candidate_id: Id of the candidate the record concerns, passed to
                the callback. None when nothing was proposed.

        Notes:
            Appends an IterationRecord to ``state.iteration_history`` so the
            chronological evolution trace is preserved for analysis. The
            record's ``failed_evaluations`` takes the failures counted since
            the iteration began, including any merge evaluation, and its
            ``token_usage`` the token rollup of the same evaluations (zeros
            when the iteration evaluated nothing). Every record
            path goes through here, so ``config.on_iteration``, when set, is
            called with the record and ``candidate_id`` right after the
            append; an awaitable return value is awaited. Exceptions from the
            callback are not caught. Ends by writing a checkpoint through
            ``_write_checkpoint`` when ``config.checkpoint_path`` is set.
        """
        assert self._state is not None, "Engine state not initialized"
        record = IterationRecord(
            iteration_number=self._state.iteration,
            score=score,
            component_text=component_text,
            evolved_component=evolved_component,
            accepted=accepted,
            objective_scores=objective_scores,
            reflection_reasoning=reflection_reasoning,
            skip_reason=skip_reason,
            failed_evaluations=self._take_pending_failed_evaluations(),
            token_usage=self._take_pending_token_usage(),
        )
        self._state.iteration_history.append(record)
        callback = self.config.on_iteration
        if callback is not None:
            outcome = callback(record, candidate_id)
            if inspect.isawaitable(outcome):
                await outcome
        self._write_checkpoint()

    async def _record_empty_proposal(self, error: EmptyProposalError) -> None:
        """Record an iteration whose reflection returned an empty proposal.

        Args:
            error: The error raised while proposing; its ``component`` names
                the component the reflection was working on.

        Notes:
            Logs ``evolution.proposal_skipped`` with
            ``reason="empty_proposal"``, counts the iteration toward
            stagnation and appends a not-accepted IterationRecord with
            ``score=0.0``, empty ``component_text`` and
            ``skip_reason="empty_proposal"``. Nothing is evaluated. The
            ``on_iteration`` callback receives ``None`` as the candidate id.
        """
        assert self._state is not None, "Engine state not initialized"
        logger.debug(
            "evolution.proposal_skipped",
            iteration=self._state.iteration,
            reason="empty_proposal",
            component=error.component,
        )
        self._state.stagnation_counter += 1
        await self._record_iteration(
            score=0.0,
            component_text="",
            evolved_component=error.component,
            accepted=False,
            skip_reason="empty_proposal",
        )

    async def _record_reflection_timeout(self, error: ReflectionTimeoutError) -> None:
        """Record an iteration whose reflection agent timed out.

        Args:
            error: The error raised while proposing; its ``component`` names
                the component the reflection was working on and its
                ``timeout_seconds`` the timeout it ran under.

        Notes:
            Logs ``evolution.proposal_skipped`` with
            ``reason="reflection_timeout"`` and ``timeout_seconds``, counts
            the iteration toward stagnation and appends a not-accepted
            IterationRecord with ``score=0.0``, empty ``component_text`` and
            ``skip_reason="reflection_timeout"``. Nothing is evaluated, and
            accepted candidates and the Pareto state are untouched.
        """
        assert self._state is not None, "Engine state not initialized"
        logger.debug(
            "evolution.proposal_skipped",
            iteration=self._state.iteration,
            reason="reflection_timeout",
            component=error.component,
            timeout_seconds=error.timeout_seconds,
        )
        self._state.stagnation_counter += 1
        await self._record_iteration(
            score=0.0,
            component_text="",
            evolved_component=error.component,
            accepted=False,
            skip_reason="reflection_timeout",
        )

    async def _record_reflection_error(self, error: ReflectionError) -> None:
        """Record an iteration whose reflection function kept raising.

        Args:
            error: The retryable error the proposer raised after its retry;
                its ``component`` names the component the reflection was
                working on, ``cause`` the provider exception and
                ``attempts`` the number of reflection calls made.

        Notes:
            Logs ``evolution.proposal_skipped`` at warning level with
            ``reason="reflection_error"``, the cause's ``error_type`` and
            text and ``attempts``, counts the iteration toward stagnation
            and appends a not-accepted IterationRecord with ``score=0.0``,
            empty ``component_text`` and ``skip_reason="reflection_error"``.
            Nothing is evaluated, and accepted candidates and the Pareto
            state are untouched.
        """
        assert self._state is not None, "Engine state not initialized"
        logger.warning(
            "evolution.proposal_skipped",
            iteration=self._state.iteration,
            reason="reflection_error",
            component=error.component,
            error_type=type(error.cause).__name__,
            error=str(error.cause),
            attempts=error.attempts,
        )
        self._state.stagnation_counter += 1
        await self._record_iteration(
            score=0.0,
            component_text="",
            evolved_component=error.component,
            accepted=False,
            skip_reason="reflection_error",
        )

    async def _record_schema_validation_skip(
        self, proposal: Candidate, evolved_components: list[str]
    ) -> None:
        """Record an iteration whose proposed output schema failed validation.

        Args:
            proposal: The proposal whose ``output_schema`` text is invalid.
            evolved_components: Names of the components the proposal evolved,
                logged with the skip.

        Notes:
            Logs ``evolution.proposal_skipped`` with
            ``reason="schema_validation_failed"``, counts the iteration toward
            stagnation and appends a not-accepted IterationRecord with
            ``score=0.0``, the invalid schema text as ``component_text``,
            ``evolved_component="output_schema"`` and
            ``skip_reason="schema_validation_failed"``. Nothing is evaluated.
            The ``on_iteration`` callback receives the proposal's id.
        """
        assert self._state is not None, "Engine state not initialized"
        logger.debug(
            "evolution.proposal_skipped",
            iteration=self._state.iteration,
            reason="schema_validation_failed",
            candidate_id=proposal.id,
            components=evolved_components,
        )
        self._state.stagnation_counter += 1
        await self._record_iteration(
            score=0.0,
            component_text=proposal.components["output_schema"],
            evolved_component="output_schema",
            accepted=False,
            skip_reason="schema_validation_failed",
            candidate_id=proposal.id,
        )

    async def _record_if_duplicate(
        self, proposal: Candidate, evolved_components: list[str]
    ) -> bool:
        """Record a skipped iteration when the proposal was already scored.

        Args:
            proposal: The candidate proposed this iteration.
            evolved_components: Names of the components evolved this
                iteration; the first one names the record's component.

        Returns:
            True when the proposal's id was already scored and the iteration
            was recorded as a duplicate; False when it must be evaluated.

        Notes:
            A duplicate logs ``proposal.duplicate`` with the stored
            acceptance score, counts toward stagnation and appends a
            not-accepted IterationRecord carrying that score, the proposal's
            text for the evolved component and ``skip_reason="duplicate"``.
            No adapter call is made. The ``on_iteration`` callback receives
            the duplicate proposal's id.
        """
        assert self._state is not None, "Engine state not initialized"
        score = self._scored.get(proposal.id)
        if score is None:
            return False
        component = (
            evolved_components[0]
            if evolved_components
            else next(iter(proposal.components))
        )
        logger.info(
            "proposal.duplicate",
            iteration=self._state.iteration,
            candidate_id=proposal.id,
            score=score,
        )
        self._state.stagnation_counter += 1
        await self._record_iteration(
            score=score,
            component_text=proposal.components.get(component, ""),
            evolved_component=component,
            accepted=False,
            skip_reason="duplicate",
            candidate_id=proposal.id,
        )
        return True

    def _effective_minibatch_size(self) -> int | None:
        """Return the reflection minibatch size in effect for this run.

        Returns:
            ``min(reflection_minibatch_size, len(trainset))`` when that is
            smaller than the trainset, otherwise None, meaning every proposal
            is evaluated on the full trainset.
        """
        size = self.config.reflection_minibatch_size
        if size is None:
            return None
        k = min(size, len(self._trainset))
        return k if k < len(self._trainset) else None

    async def _gate_on_minibatch(
        self, proposal: Candidate, evolved_components: list[str]
    ) -> bool:
        """Decide whether a proposal earns its full evaluation.

        Draws a fresh seeded sample of trainset rows, evaluates the proposal
        on them with traces, and compares the mean of its scores with the
        mean of the mutation parent's cached scores on the same rows.

        Args:
            proposal: The candidate proposed this iteration.
            evolved_components: Names of the components evolved this
                iteration; the first one names the record's component.

        Returns:
            True when the minibatch is disabled or the proposal's mean is
            strictly greater than the parent's; False when the proposal was
            rejected and its iteration recorded.

        Notes:
            The minibatch evaluation is counted through ``_count_batch`` as a
            ``"reflection"`` evaluation. A rejection logs
            ``proposal.minibatch_rejected``, counts toward stagnation and
            appends a not-accepted IterationRecord whose score is the
            acceptance aggregate over the minibatch rows and whose
            ``skip_reason`` is ``"minibatch_rejected"``. A rejected proposal
            is not stored as scored, so an identical later proposal draws a
            fresh sample. A pass logs ``proposal.minibatch_passed``.
        """
        assert self._state is not None, "Engine state not initialized"
        k = self._effective_minibatch_size()
        if k is None:
            return True
        parent_batch = self._mutation_parent_batch
        assert parent_batch is not None, "No parent batch cached"
        indices = sorted(self._minibatch_rng.sample(range(len(self._trainset)), k))
        minibatch = await self.adapter.evaluate(
            [self._trainset[i] for i in indices],
            proposal.components,
            capture_traces=True,
        )
        self._count_batch(proposal, minibatch, "reflection")
        proposal_mean = sum(minibatch.scores) / len(minibatch.scores)
        parent_mean = sum(parent_batch.scores[i] for i in indices) / k
        fields = {
            "iteration": self._state.iteration,
            "candidate_id": proposal.id,
            "indices": indices,
            "proposal_mean": proposal_mean,
            "parent_mean": parent_mean,
        }
        if proposal_mean > parent_mean:
            logger.info("proposal.minibatch_passed", **fields)
            return True
        logger.info("proposal.minibatch_rejected", **fields)
        component = (
            evolved_components[0]
            if evolved_components
            else next(iter(proposal.components))
        )
        self._state.stagnation_counter += 1
        await self._record_iteration(
            score=self._aggregate_acceptance_score(minibatch.scores),
            component_text=proposal.components.get(component, ""),
            evolved_component=component,
            accepted=False,
            skip_reason="minibatch_rejected",
            candidate_id=proposal.id,
        )
        return False

    def _start_merge(self, merge_result: ProposalResult) -> bool:
        """Count a merge attempt and decide whether to evaluate it.

        Args:
            merge_result: The merge proposer's result for this iteration.

        Returns:
            True when the merge candidate should be evaluated; False when it
            is skipped for an invalid schema or an already scored id.

        Notes:
            Decrements ``merges_due``, increments the invocation count and
            logs ``merge_scheduling.merge_attempted`` for every attempt,
            skipped or not.
        """
        assert self._state is not None, "Engine state not initialized"
        self._merges_due -= 1
        self._merge_invocations += 1
        logger.info(
            "merge_scheduling.merge_attempted",
            iteration=self._state.iteration,
            candidate_id=merge_result.candidate.id,
            parent_indices=merge_result.parent_indices,
            ancestor_idx=merge_result.metadata.get("ancestor_idx"),
            merges_due=self._merges_due,
            total_invocations=self._merge_invocations,
        )
        return not self._skip_merge_candidate(merge_result.candidate)

    def _skip_merge_candidate(self, candidate: Candidate) -> bool:
        """Decide whether a merge candidate must not be evaluated.

        Args:
            candidate: The candidate produced by the merge proposer.

        Returns:
            True when the candidate has an invalid output schema or its id
            was already scored; False when it should be evaluated.

        Notes:
            Logs ``merge.proposal_skipped`` with
            ``reason="schema_validation_failed"`` or ``reason="duplicate"``.
            No iteration record is written for a skipped merge; the
            iteration's own proposal record is unaffected.
        """
        assert self._state is not None, "Engine state not initialized"
        if not self._validate_schema_component(candidate):
            reason = "schema_validation_failed"
        elif candidate.id in self._scored:
            reason = "duplicate"
        else:
            return False
        logger.debug(
            "merge.proposal_skipped",
            iteration=self._state.iteration,
            candidate_id=candidate.id,
            reason=reason,
        )
        return True

    def _should_stop(self) -> StopReason | None:
        """Check if evolution should terminate.

        Returns:
            The ``StopReason`` that triggered termination, or ``None`` if
            evolution should continue. Conditions are checked in priority
            order: max iterations, early stopping patience, custom stoppers.

        Notes:
            Only active stoppers (those that passed setup or have no setup
            method) are invoked. Patience-based early stopping maps to
            ``MAX_ITERATIONS`` because it is a built-in convergence
            criterion, not a user-provided custom stopper.
        """
        assert self._state is not None, "Engine state not initialized"
        # Condition 1: Max iterations reached (built-in, fast path)
        if self._state.iteration >= self.config.max_iterations:
            return StopReason.MAX_ITERATIONS

        # Condition 2: Early stopping (patience exhausted, built-in)
        if self.config.patience > 0:
            if self._state.stagnation_counter >= self.config.patience:
                return StopReason.MAX_ITERATIONS

        # Condition 3: Custom stoppers (T010-T013)
        # Use _active_stoppers which excludes stoppers that failed setup
        active_stoppers = getattr(self, "_active_stoppers", None)
        if active_stoppers:
            stopper_state = self._build_stopper_state()
            for stopper in active_stoppers:
                try:
                    if stopper(stopper_state):
                        # Log stopper trigger (T013)
                        logger.info(
                            "stopper.triggered",
                            stopper=type(stopper).__name__,
                            iteration=self._state.iteration,
                        )
                        return StopReason.STOPPER_TRIGGERED
                except Exception:
                    # T032: Handle stopper exception gracefully
                    logger.exception(
                        "stopper.error",
                        stopper=type(stopper).__name__,
                        iteration=self._state.iteration,
                    )
                    # Continue checking other stoppers

        return None

    def _should_accept(self, proposal_score: float, best_score: float) -> bool:
        """Check if proposal should be accepted.

        Args:
            proposal_score: Score of the proposed candidate.
            best_score: Current best score.

        Returns:
            True if proposal_score > best_score + min_improvement_threshold.

        Notes:
            Signals True when proposal exceeds best score by the configured
            improvement threshold, enabling configurable acceptance sensitivity.
        """
        threshold = self.config.min_improvement_threshold
        return proposal_score > best_score + threshold

    def _validate_schema_component(self, proposal: Candidate) -> bool:
        """Validate output_schema component if present.

        Validates that proposed schema text is syntactically correct and
        structurally valid (inherits from BaseModel, no imports/functions).
        Invalid schemas are rejected to prevent evolution from accepting
        non-functional schema proposals.

        Args:
            proposal: Candidate containing components to validate.

        Returns:
            True if valid or no output_schema component present.
            False if output_schema validation fails.

        Notes:
            This validation runs before expensive evaluation to reject
            invalid schemas early. Security checks (no imports, no functions)
            are enforced to prevent code injection.
        """
        if "output_schema" not in proposal.components:
            return True

        schema_text = proposal.components["output_schema"]

        try:
            # Import here to avoid circular dependency at module load
            from gepa_adk.utils.schema_utils import validate_schema_text

            validate_schema_text(schema_text)
            logger.debug(
                "schema_validation.passed",
                iteration=self._state.iteration if self._state else None,
            )
            return True
        except SchemaValidationError as e:
            logger.warning(
                "schema_validation.rejected",
                iteration=self._state.iteration if self._state else None,
                validation_stage=e.validation_stage,
                line_number=e.line_number,
                error=e.validation_error,
            )
            return False

    def _accept_proposal(
        self,
        proposal: Candidate,
        score: float,
        eval_batch: EvaluationBatch,
        *,
        candidate_idx: int | None = None,
        reflection_score: float | None = None,
        valset_mean: float | None = None,
        objective_scores: list[dict[str, float]] | None = None,
    ) -> None:
        """Accept a proposal and update state.

        Args:
            proposal: Proposed candidate to accept.
            score: Acceptance score of the proposed candidate (sum or mean).
            eval_batch: Reflection batch from proposal evaluation (cached for
                next iteration's reflective dataset generation).
            candidate_idx: Optional ParetoState candidate index to update with
                lineage metadata.
            reflection_score: Optional trainset score to store with best
                candidate metadata.
            valset_mean: Optional valset mean score to track separately from
                acceptance score.
            objective_scores: Optional objective scores from scoring batch.
                None when adapter does not provide objective scores.

        Notes:
            Replaces the cached reflection batch for the next proposal
            iteration and tracks acceptance score and valset mean separately.
        """
        assert self._state is not None, "Engine state not initialized"
        # Create new candidate with lineage
        new_candidate = Candidate(
            components=dict(proposal.components),
            generation=self._state.best_candidate.generation + 1,
            parent_id=f"gen-{self._state.best_candidate.generation}",
        )
        if candidate_idx is not None and self._pareto_state is not None:
            self._pareto_state.candidates[candidate_idx] = new_candidate
        self._state.best_candidate = new_candidate
        self._state.best_score = score
        self._state.stagnation_counter = 0
        self._state.last_eval_batch = eval_batch
        if reflection_score is not None:
            self._state.best_reflection_score = reflection_score
        if valset_mean is not None:
            self._state.best_valset_mean = valset_mean
        self._state.best_objective_scores = objective_scores

    def _build_result(
        self, stop_reason: StopReason = StopReason.COMPLETED
    ) -> EvolutionResult:
        """Build final result from current state.

        Args:
            stop_reason: Why the evolution run terminated.

        Returns:
            Frozen EvolutionResult with all metrics and original_components.

        Notes:
            Synthesizes a frozen EvolutionResult containing all evolution metrics,
            history, and original_components snapshot, suitable for immutable
            result reporting. The evolved_components dict contains all component
            values from the best candidate. ``total_failed_evaluations`` is
            the baseline count plus the sum over ``iteration_history``, and
            ``token_usage`` is the run token rollup, baseline included.
        """
        assert self._state is not None, "Engine state not initialized"
        baseline_failed = self._state.baseline_failed_evaluations
        return EvolutionResult(
            stop_reason=stop_reason,
            original_score=self._state.original_score,
            final_score=self._state.best_score,
            evolved_components=dict(self._state.best_candidate.components),
            iteration_history=self._state.iteration_history,
            total_iterations=self._state.iteration,
            valset_score=self._state.best_valset_mean,
            trainset_score=self._state.best_reflection_score,
            objective_scores=self._state.best_objective_scores,
            original_components=dict(self._initial_candidate.components),
            baseline_failed_evaluations=baseline_failed,
            total_failed_evaluations=baseline_failed
            + sum(r.failed_evaluations for r in self._state.iteration_history),
            token_usage=self._run_token_usage,
        )

    def _write_checkpoint(self) -> None:
        """Write the engine's state to ``config.checkpoint_path``.

        Does nothing when no checkpoint path is configured. Otherwise
        builds the checkpoint dict (version, iteration, stagnation counter,
        best candidate and scores, history, scored map, evaluation counter,
        best reflection batch, random states and run identity) and writes it
        atomically through ``write_checkpoint``.

        Raises:
            TypeError: If a batch field holds a value JSON cannot encode.
            OSError: If the file cannot be written. Nothing is swallowed.

        Notes:
            ``rng_state`` is the engine ``rng``'s state when one was given,
            else null; ``minibatch_rng_state`` is always written.
            ``valset_size`` is null when the valset is the trainset.
            ``run_token_usage`` is the run's token rollup so far, so a
            resumed run reports the whole run's usage.
        """
        if self.config.checkpoint_path is None or self._state is None:
            return
        path = Path(self.config.checkpoint_path)
        state = self._state
        data = {
            "checkpoint_version": CHECKPOINT_VERSION,
            "iteration": state.iteration,
            "stagnation_counter": state.stagnation_counter,
            "best_candidate": state.best_candidate.to_dict(),
            "best_score": state.best_score,
            "original_score": state.original_score,
            "best_reflection_score": state.best_reflection_score,
            "best_valset_mean": state.best_valset_mean,
            "best_objective_scores": state.best_objective_scores,
            "baseline_failed_evaluations": state.baseline_failed_evaluations,
            "iteration_history": [r.to_dict() for r in state.iteration_history],
            "scored": dict(self._scored),
            "total_evaluations": self._total_evaluations,
            "last_eval_batch": batch_to_dict(state.last_eval_batch),
            "rng_state": (
                None if self._rng is None else rng_state_to_json(self._rng.getstate())
            ),
            "minibatch_rng_state": rng_state_to_json(self._minibatch_rng.getstate()),
            "initial_candidate_id": self._initial_candidate.id,
            "trainset_size": len(self._trainset),
            "valset_size": None if self._valset_is_trainset else len(self._valset),
            "seed": self.config.seed,
            "run_token_usage": self._run_token_usage.to_dict(),
            "written_at": datetime.now(UTC).isoformat(),
        }
        write_checkpoint(path, data)
        logger.debug("checkpoint.written", iteration=state.iteration, path=str(path))

    def _load_checkpoint(self) -> dict[str, Any]:
        """Read the checkpoint and refuse one from a different run.

        Returns:
            The checkpoint dict.

        Raises:
            ConfigurationError: If ``config.checkpoint_path`` is unset, the
                file is missing, its version is not ``CHECKPOINT_VERSION``,
                or its initial candidate, trainset size or valset size
                differs from this engine's.
        """
        path = self.config.checkpoint_path
        if path is None:
            raise ConfigurationError(
                "resume=True requires checkpoint_path",
                field="checkpoint_path",
                value=None,
                constraint="not None when resume=True",
            )
        data = read_checkpoint(Path(path))
        check_run_matches(
            data,
            initial_candidate_id=self._initial_candidate.id,
            trainset_size=len(self._trainset),
            valset_size=None if self._valset_is_trainset else len(self._valset),
        )
        return data

    def _resume_from_checkpoint(self) -> None:
        """Restore engine state from ``config.checkpoint_path``.

        Rebuilds ``_EngineState``, the scored map, the evaluation counter,
        the run token rollup, the mutation parent batch and the random
        states from the file, and marks the engine restored so the loop
        skips the baseline.

        Raises:
            ConfigurationError: If ``_load_checkpoint`` refuses the file.

        Notes:
            The engine ``rng`` is restored only when one was given and a
            state was stored; the minibatch random source always is. A
            checkpoint without ``run_token_usage`` restores an unknown
            rollup whose ``rows_unknown`` is the checkpointed evaluation
            count, so the pre-resume rows read as unknown, not free. The
            ``on_iteration`` callback is not called for restored history.
            Logs ``checkpoint.resumed`` with the iteration, the stagnation
            counter, the evaluation counter and the path.
        """
        data = self._load_checkpoint()
        last_eval_batch = batch_from_dict(data["last_eval_batch"])
        self._state = _EngineState(
            best_candidate=Candidate.from_dict(data["best_candidate"]),
            best_score=data["best_score"],
            original_score=data["original_score"],
            iteration=data["iteration"],
            stagnation_counter=data["stagnation_counter"],
            iteration_history=[
                IterationRecord.from_dict(r) for r in data["iteration_history"]
            ],
            last_eval_batch=last_eval_batch,
            best_reflection_score=data["best_reflection_score"],
            best_valset_mean=data["best_valset_mean"],
            best_objective_scores=data["best_objective_scores"],
            baseline_failed_evaluations=data["baseline_failed_evaluations"],
        )
        self._scored = dict(data["scored"])
        self._total_evaluations = data["total_evaluations"]
        stored_usage = data.get("run_token_usage")
        self._run_token_usage = (
            TokenRollup.from_dict(stored_usage)
            if stored_usage is not None
            else _unknown_tokens(data["total_evaluations"])
        )
        self._mutation_parent_batch = last_eval_batch
        if self._rng is not None and data["rng_state"] is not None:
            self._rng.setstate(rng_state_from_json(data["rng_state"]))
        self._minibatch_rng.setstate(rng_state_from_json(data["minibatch_rng_state"]))
        self._restored = True
        logger.info(
            "checkpoint.resumed",
            iteration=self._state.iteration,
            stagnation_counter=self._state.stagnation_counter,
            total_evaluations=self._total_evaluations,
            path=str(self.config.checkpoint_path),
        )

    async def run(self) -> EvolutionResult:
        """Execute the evolution loop.

        Runs the core evolution loop:
        1. Evaluate baseline candidate
        2. For each iteration until max_iterations or convergence:
           a. Generate reflective dataset from traces
           b. Propose new candidate text
           c. Evaluate proposal
           d. Accept if improves above threshold
           e. Record iteration
        3. Return frozen EvolutionResult
        4. On ``KeyboardInterrupt`` or ``asyncio.CancelledError``, return
           partial result with best-so-far components
        5. On an ``EvolutionError`` after the baseline, attach a partial
           result to the error and re-raise it

        Returns:
            EvolutionResult containing evolution metrics and components.
            On normal completion, ``stop_reason`` reflects the termination
            condition. On interrupt, a partial result is returned with
            ``StopReason.KEYBOARD_INTERRUPT`` or ``StopReason.CANCELLED``.

        Raises:
            KeyboardInterrupt: Re-raised if interrupt occurs before baseline
                evaluation completes (no meaningful partial result possible).
            asyncio.CancelledError: Re-raised if cancellation occurs before
                baseline evaluation completes.
            EvolutionError: Re-raised when it aborts the run, for example a
                non-retryable ``ReflectionError``. When the baseline was
                scored, its ``partial_result`` holds an ``EvolutionResult``
                with ``StopReason.ERROR``, the recorded iterations and the
                best candidate so far; otherwise it stays ``None``.
            Exception: Adapter ``Exception`` subclasses propagate unchanged.

        Examples:
            Running evolution:

            ```python
            result = await engine.run()
            print(f"Improved: {result.improved}")
            print(f"Best score: {result.final_score}")
            ```

        Notes:
            Outputs a frozen EvolutionResult after completing the evolution
            loop. Engine instance should not be reused after run() completes.
            Method is idempotent if called multiple times (restarts fresh):
            the evaluation counters and the scored-candidate map used for
            duplicate detection are cleared before the baseline runs.
            Fail-fast behavior: adapter ``Exception`` subclasses propagate
            unchanged. ``KeyboardInterrupt`` and ``asyncio.CancelledError``
            (``BaseException`` subclasses) are caught and converted to partial
            results with appropriate ``StopReason``. An ``EvolutionError`` is
            logged as ``evolution.aborted`` and re-raised; after the
            baseline it carries ``partial_result`` whose
            ``total_iterations`` counts recorded iterations only, since the
            aborted iteration was never recorded. Logs seed value at start
            for reproducibility tracking, and logs
            ``reflection.minibatch.enabled`` when a reflection minibatch
            smaller than the trainset is in effect. Resets the evaluation
            counter, the pending failure counter, the engine state and the
            pending and run token rollups at start, so a reused engine
            never attaches an earlier run's state to ``partial_result``.
            With ``config.resume`` it then restores
            the checkpoint through ``_resume_from_checkpoint``, which sets
            the counters and scored map from the file, and the loop skips
            the baseline.
        """
        logger.info("engine.start", seed=self.config.seed)
        if self._effective_minibatch_size() is not None:
            logger.info(
                "reflection.minibatch.enabled",
                size=self.config.reflection_minibatch_size,
                trainset_size=len(self._trainset),
            )

        # Initialize stopper state tracking (T004)
        self._start_time = time.monotonic()
        self._total_evaluations = 0
        self._pending_failed_evaluations = 0
        self._pending_token_usage = _ZERO_TOKENS
        self._run_token_usage = _ZERO_TOKENS
        # A fresh run scores every candidate again; stale ids would read
        # first-iteration proposals as duplicates.
        self._scored.clear()
        # State from an earlier run must not leak into this run's partial
        # result; the baseline or the checkpoint rebuilds it.
        self._state = None
        self._restored = False
        if self.config.resume:
            self._resume_from_checkpoint()

        # Setup stopper lifecycle (T023)
        setup_stoppers = self._setup_stoppers()

        try:
            return await self._run_evolution_loop()
        except EvolutionError as error:
            logger.error(
                "evolution.aborted",
                iteration=self._state.iteration if self._state else 0,
                error_type=type(error).__name__,
                error=str(error),
            )
            if self._state is not None:
                # The aborted iteration was never recorded
                self._state.iteration = len(self._state.iteration_history)
                error.partial_result = self._build_result(stop_reason=StopReason.ERROR)
            raise
        except KeyboardInterrupt:
            logger.info(
                "evolution.interrupted",
                iteration=self._state.iteration if self._state else 0,
            )
            if self._state is None:
                raise
            return self._build_result(stop_reason=StopReason.KEYBOARD_INTERRUPT)
        except asyncio.CancelledError:
            logger.info(
                "evolution.cancelled",
                iteration=self._state.iteration if self._state else 0,
            )
            if self._state is None:
                raise
            return self._build_result(stop_reason=StopReason.CANCELLED)
        finally:
            # Cleanup stopper lifecycle (T024)
            self._cleanup_stoppers(setup_stoppers)

    async def _run_evolution_loop(self) -> EvolutionResult:
        """Execute the core evolution loop.

        This method contains the actual evolution loop logic, separated
        from lifecycle management for clean try/finally handling.

        Returns:
            EvolutionResult with evolution outcomes.

        Raises:
            ReflectionError: If proposing raises a non-retryable
                ``ReflectionError``; ``run()`` attaches the partial result.

        Notes:
            Only called from run(). Handles the evolution loop body
            while run() manages stopper lifecycle. The loop tracks
            ``StopReason`` to report why evolution terminated.
            Each iteration records ``reflection_reasoning`` from the
            adapter's proposer via a ``getattr`` chain when available.
            Each proposal's reflection batch is handed to scoring so a
            valset that is the trainset is not evaluated twice.
            An ``EmptyProposalError`` from proposing is recorded as a
            skipped iteration (``skip_reason="empty_proposal"``) that counts
            toward stagnation; the loop then checks stop conditions and
            continues. A ``ReflectionTimeoutError`` is handled the same way
            with ``skip_reason="reflection_timeout"``, and a retryable
            ``ReflectionError`` with ``skip_reason="reflection_error"``; a
            non-retryable ``ReflectionError`` propagates to ``run()``,
            which attaches the partial result. A proposal whose
            ``output_schema`` text fails validation is recorded the same way
            with ``skip_reason="schema_validation_failed"``, counts toward
            stagnation and is followed by the stop check. A proposal whose
            ``Candidate.id`` was already scored (baseline, proposal or merge)
            is recorded with
            ``skip_reason="duplicate"`` and its stored score instead of being
            evaluated. With a reflection minibatch in effect, a proposal
            that does not beat its parent on the iteration's sampled rows is
            recorded with ``skip_reason="minibatch_rejected"`` and not
            evaluated further. A merge candidate that is a duplicate or has an
            invalid schema is not evaluated, and the iteration's own record
            and stop check still follow. Each iteration starts with no
            pending failures and a zero pending token rollup, so an
            unrecorded iteration's failures and tokens do not carry into the
            next record.
            Each accept decision is logged as ``proposal.accepted`` or
            ``proposal.rejected`` with the proposal's ``candidate_id``.
            Every recorded iteration, skipped or not, reaches
            ``config.on_iteration`` before the stop check.
            State restored from a checkpoint replaces the baseline
            evaluation.
        """
        # A restored checkpoint already holds the baseline
        if not self._restored:
            await self._initialize_baseline()
        assert self._state is not None, "Engine state not initialized"

        # Evolution loop
        stop_reason = self._should_stop()
        while stop_reason is None:
            self._state.iteration += 1
            # Failures from an unrecorded previous iteration do not carry over
            self._pending_failed_evaluations = 0
            self._pending_token_usage = _ZERO_TOKENS

            # Propose mutation (returns candidate and list of components evolved)
            try:
                proposal, evolved_components_list = await self._propose_mutation()
            except EmptyProposalError as error:
                # Empty reflection after retry: failed iteration, not fatal
                await self._record_empty_proposal(error)
                stop_reason = self._should_stop()
                continue
            except ReflectionTimeoutError as error:
                # Reflection timed out: skipped iteration, not fatal
                await self._record_reflection_timeout(error)
                stop_reason = self._should_stop()
                continue
            except ReflectionError as error:
                # A programming or client error will not clear on its own
                if not error.retryable:
                    raise
                # Provider error survived the proposer's retry: skip it
                await self._record_reflection_error(error)
                stop_reason = self._should_stop()
                continue

            # Validate schema component if present (reject invalid early)
            if not self._validate_schema_component(proposal):
                # Invalid schema: record the skip, no evaluation
                await self._record_schema_validation_skip(
                    proposal, evolved_components_list
                )
                stop_reason = self._should_stop()
                continue

            # Already scored this run: reuse its score, no evaluation
            if await self._record_if_duplicate(proposal, evolved_components_list):
                stop_reason = self._should_stop()
                continue

            # Beat the parent on a trainset minibatch before the full pass
            if not await self._gate_on_minibatch(proposal, evolved_components_list):
                stop_reason = self._should_stop()
                continue

            # Evaluate proposal
            reflection_score, reflection_batch = await self._evaluate_reflection(
                proposal
            )
            proposal_score, scoring_batch, eval_indices = await self._evaluate_scoring(
                proposal, reflection_batch=reflection_batch
            )

            candidate_idx = None
            if self._pareto_state is not None:
                # Use eval_indices returned from _evaluate_scoring (T066)
                # Prepare objective scores if available (T068)
                objective_scores: dict[str, float] | None = None
                per_example_objective_scores: dict[int, dict[str, float]] | None = None

                if scoring_batch.objective_scores is not None:
                    from statistics import fmean

                    if self.config.frontier_type in (
                        FrontierType.OBJECTIVE,
                        FrontierType.HYBRID,
                    ):
                        # Aggregate objective scores across evaluated examples
                        objective_scores_accum: dict[str, list[float]] = {}
                        for obj_scores in scoring_batch.objective_scores:
                            for obj_name, obj_score in obj_scores.items():
                                objective_scores_accum.setdefault(obj_name, []).append(
                                    obj_score
                                )
                        # Take mean per objective
                        objective_scores = {
                            obj_name: fmean(scores)
                            for obj_name, scores in objective_scores_accum.items()
                        }

                    if self.config.frontier_type == FrontierType.CARTESIAN:
                        # For CARTESIAN, need per-example objective scores mapped to valset indices
                        per_example_objective_scores = {
                            eval_indices[i]: scoring_batch.objective_scores[i]
                            for i in range(len(eval_indices))
                        }
                        # Also need aggregated for validation
                        objective_scores_by_name: dict[str, list[float]] = {}
                        for obj_scores in scoring_batch.objective_scores:
                            for obj_name, obj_score in obj_scores.items():
                                objective_scores_by_name.setdefault(
                                    obj_name, []
                                ).append(obj_score)
                        objective_scores = {
                            obj_name: fmean(scores)
                            for obj_name, scores in objective_scores_by_name.items()
                        }

                # Determine parent indices for genealogy tracking
                parent_indices: list[int] | None = None
                if self._candidate_selector is not None:
                    try:
                        parent_idx = await self._candidate_selector.select_candidate(
                            self._pareto_state
                        )
                        parent_indices = [parent_idx]
                    except NoCandidateAvailableError:
                        parent_indices = None
                else:
                    # Use best candidate as parent
                    if self._pareto_state.best_average_idx is not None:
                        parent_indices = [self._pareto_state.best_average_idx]

                # Pass scores with correct index mapping (T066)
                candidate_idx = self._pareto_state.add_candidate(
                    proposal,
                    scoring_batch.scores,
                    score_indices=eval_indices,
                    objective_scores=objective_scores,
                    per_example_objective_scores=per_example_objective_scores,
                    parent_indices=parent_indices,
                    logger=logger,
                )
                self._candidate_eval_batches[candidate_idx] = reflection_batch
                logger.info(
                    "pareto_frontier.candidate_added",
                    candidate_idx=candidate_idx,
                    candidate_id=proposal.id,
                    iteration=self._state.iteration,
                )

            # Calculate valset mean using only evaluated scores (T067)
            valset_mean = (
                sum(scoring_batch.scores) / len(scoring_batch.scores)
                if scoring_batch.scores
                else 0.0
            )

            # Accept if improves above threshold
            accepted = self._should_accept(proposal_score, self._state.best_score)
            if accepted:
                logger.info(
                    "proposal.accepted",
                    iteration=self._state.iteration,
                    candidate_id=proposal.id,
                    score=proposal_score,
                    best_score=self._state.best_score,
                )
                self._accept_proposal(
                    proposal,
                    proposal_score,
                    reflection_batch,
                    candidate_idx=candidate_idx,
                    reflection_score=reflection_score,
                    valset_mean=valset_mean,
                    objective_scores=scoring_batch.objective_scores,
                )
                # Schedule merge if enabled
                if (
                    self.config.use_merge
                    and self._merge_proposer is not None
                    and self._merge_invocations < self.config.max_merge_invocations
                ):
                    self._merges_due += 1
                    logger.debug(
                        "merge_scheduling.merge_scheduled",
                        iteration=self._state.iteration,
                        candidate_id=proposal.id,
                        merges_due=self._merges_due,
                    )
            else:
                logger.debug(
                    "proposal.rejected",
                    iteration=self._state.iteration,
                    candidate_id=proposal.id,
                    score=proposal_score,
                    best_score=self._state.best_score,
                )
                # Increment stagnation counter on rejection
                self._state.stagnation_counter += 1

            # Attempt merge if scheduled
            if (
                self._merges_due > 0
                and self._merge_proposer is not None
                and self._pareto_state is not None
                and self._merge_invocations < self.config.max_merge_invocations
            ):
                merge_result = await self._merge_proposer.propose(self._pareto_state)
                # A skipped merge (invalid schema or already scored) is not
                # evaluated; the iteration is still recorded below
                if merge_result is not None and self._start_merge(merge_result):
                    # Evaluate merge proposal
                    (
                        merge_reflection_score,
                        merge_reflection_batch,
                    ) = await self._evaluate_reflection(merge_result.candidate)
                    (
                        merge_proposal_score,
                        merge_scoring_batch,
                        merge_eval_indices,
                    ) = await self._evaluate_scoring(
                        merge_result.candidate,
                        reflection_batch=merge_reflection_batch,
                    )

                    # Add merge candidate to ParetoState
                    merge_candidate_idx = None
                    assert self._pareto_state is not None, (
                        "Pareto state not initialized"
                    )
                    merge_objective_scores: dict[str, float] | None = None
                    merge_per_example_objective_scores: (
                        dict[int, dict[str, float]] | None
                    ) = None

                    if merge_scoring_batch.objective_scores is not None:
                        from statistics import fmean

                        if self.config.frontier_type in (
                            FrontierType.OBJECTIVE,
                            FrontierType.HYBRID,
                        ):
                            merge_objective_scores_accum: dict[str, list[float]] = {}
                            for obj_scores in merge_scoring_batch.objective_scores:
                                for obj_name, obj_score in obj_scores.items():
                                    merge_objective_scores_accum.setdefault(
                                        obj_name, []
                                    ).append(obj_score)
                            merge_objective_scores = {
                                obj_name: fmean(scores)
                                for obj_name, scores in merge_objective_scores_accum.items()
                            }

                        if self.config.frontier_type == FrontierType.CARTESIAN:
                            merge_per_example_objective_scores = {
                                merge_eval_indices[
                                    i
                                ]: merge_scoring_batch.objective_scores[i]
                                for i in range(len(merge_eval_indices))
                            }
                            merge_objective_scores_by_name: dict[str, list[float]] = {}
                            for obj_scores in merge_scoring_batch.objective_scores:
                                for obj_name, obj_score in obj_scores.items():
                                    merge_objective_scores_by_name.setdefault(
                                        obj_name, []
                                    ).append(obj_score)
                            merge_objective_scores = {
                                obj_name: fmean(scores)
                                for obj_name, scores in merge_objective_scores_by_name.items()
                            }

                    merge_candidate_idx = self._pareto_state.add_candidate(
                        merge_result.candidate,
                        merge_scoring_batch.scores,
                        score_indices=merge_eval_indices,
                        objective_scores=merge_objective_scores,
                        per_example_objective_scores=merge_per_example_objective_scores,
                        parent_indices=merge_result.parent_indices,
                        logger=logger,
                    )
                    self._candidate_eval_batches[merge_candidate_idx] = (
                        merge_reflection_batch
                    )

                    merge_valset_mean = (
                        sum(merge_scoring_batch.scores)
                        / len(merge_scoring_batch.scores)
                        if merge_scoring_batch.scores
                        else 0.0
                    )

                    # Accept merge if improves
                    merge_accepted = self._should_accept(
                        merge_proposal_score, self._state.best_score
                    )
                    if merge_accepted:
                        self._accept_proposal(
                            merge_result.candidate,
                            merge_proposal_score,
                            merge_reflection_batch,
                            candidate_idx=merge_candidate_idx,
                            reflection_score=merge_reflection_score,
                            valset_mean=merge_valset_mean,
                            objective_scores=merge_scoring_batch.objective_scores,
                        )
                        logger.info(
                            "merge_scheduling.merge_accepted",
                            iteration=self._state.iteration,
                            candidate_id=merge_result.candidate.id,
                            merge_score=merge_proposal_score,
                        )
                    else:
                        logger.debug(
                            "merge_scheduling.merge_rejected",
                            iteration=self._state.iteration,
                            candidate_id=merge_result.candidate.id,
                            merge_score=merge_proposal_score,
                            best_score=self._state.best_score,
                        )
                elif merge_result is None:
                    # Merge not possible, decrement counter
                    if self._merges_due > 0:
                        self._merges_due -= 1

            # Record iteration with actual evolved component name (T033)
            # For single-component evolution, use the first (and only) component.
            # For multi-component round-robin, this tracks which component was
            # evolved in this iteration.
            if evolved_components_list:
                evolved_component_name = evolved_components_list[0]
            else:
                # Empty list indicates logic error - use first key from proposal
                logger.warning(
                    "engine.empty_evolved_components_list",
                    iteration=self._state.iteration,
                    proposal_keys=list(proposal.components.keys()),
                )
                evolved_component_name = next(iter(proposal.components.keys()))
            await self._record_iteration(
                score=proposal_score,
                component_text=proposal.components.get(evolved_component_name, ""),
                evolved_component=evolved_component_name,
                accepted=accepted,
                objective_scores=scoring_batch.objective_scores,
                # TODO: Surface last_reasoning through adapter protocol instead
                # of reaching into private _proposer attribute. Safe (defaults
                # to None) but couples engine to adapter internals.
                reflection_reasoning=getattr(
                    getattr(self.adapter, "_proposer", None),
                    "last_reasoning",
                    None,
                ),
                candidate_id=proposal.id,
            )

            stop_reason = self._should_stop()

        # Build and return result
        return self._build_result(stop_reason=stop_reason)
