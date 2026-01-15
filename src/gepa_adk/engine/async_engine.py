"""Async evolution engine implementation.

This module contains the AsyncGEPAEngine class that orchestrates the
core evolution loop for optimizing agent instructions using async-first
design principles.

Note:
    Tracks separate trainset and valset evaluation flows for evolution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Generic, TypeVar

import structlog

from gepa_adk.adapters.component_selector import RoundRobinComponentSelector
from gepa_adk.domain.exceptions import InvalidScoreListError, NoCandidateAvailableError
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
)
from gepa_adk.domain.state import ParetoState
from gepa_adk.domain.types import FrontierType
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
from gepa_adk.ports.proposer import ProposerProtocol
from gepa_adk.ports.selector import (
    CandidateSelectorProtocol,
    ComponentSelectorProtocol,
    EvaluationPolicyProtocol,
)

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")

logger = structlog.get_logger(__name__)


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

    Note:
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


class AsyncGEPAEngine(Generic[DataInst, Trajectory, RolloutOutput]):
    """Async evolution engine orchestrating the GEPA loop.

    This engine executes the core evolution algorithm:
    1. Evaluate baseline candidate
    2. For each iteration until max_iterations or convergence:
       a. Generate reflective dataset from traces
       b. Propose new candidate text
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

    Note:
        Avoid reusing engine instances after run() completes.
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
    ) -> None:
        """Initialize the evolution engine.

        Args:
            adapter: Implementation of AsyncGEPAAdapter protocol for evaluation
                and proposal generation.
            config: Evolution parameters controlling iterations, thresholds,
                and early stopping.
            initial_candidate: Starting candidate with 'instruction' component.
            batch: Trainset data instances for reflection and mutation.
            valset: Optional validation data for scoring candidates. Defaults
                to trainset when omitted.
            candidate_selector: Optional selector strategy for Pareto-aware
                candidate sampling.
            component_selector: Optional selector strategy for choosing which
                components to update. Defaults to RoundRobinComponentSelector.
            evaluation_policy: Optional policy for selecting which validation
                examples to evaluate per iteration. Defaults to FullEvaluationPolicy.
            merge_proposer: Optional proposer for merge operations. If provided
                and config.use_merge is True, merge proposals will be attempted
                after successful mutations.

        Raises:
            ValueError: If batch is empty or initial_candidate lacks 'instruction'.
            ConfigurationError: If config validation fails (via EvolutionConfig).

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

        Note:
            Configures trainset and valset routing for reflection and scoring.
        """
        # Validation
        if len(batch) == 0:
            raise ValueError("batch must contain at least one data instance")
        if valset is not None and len(valset) == 0:
            raise ValueError(
                "valset must contain at least one validation data instance"
            )

        if "instruction" not in initial_candidate.components:
            raise ValueError("initial_candidate must have 'instruction' component")

        # Store dependencies
        self.adapter = adapter
        self.config = config
        self._initial_candidate = initial_candidate
        self._trainset = batch
        self._valset = valset if valset is not None else batch
        self._state: _EngineState | None = None
        self._candidate_selector = candidate_selector
        self._component_selector = component_selector or RoundRobinComponentSelector()
        self._pareto_state: ParetoState | None = None
        self._candidate_eval_batches: dict[int, EvaluationBatch] = {}
        self._merge_proposer = merge_proposer
        self._merges_due: int = 0
        self._merge_invocations: int = 0
        # Import here to avoid circular dependency
        if evaluation_policy is None:
            from gepa_adk.adapters.evaluation_policy import FullEvaluationPolicy

            self._evaluation_policy: EvaluationPolicyProtocol = FullEvaluationPolicy()
        else:
            self._evaluation_policy = evaluation_policy

    def _aggregate_acceptance_score(self, scores: list[float]) -> float:
        """Aggregate scores for acceptance decisions based on acceptance_metric.

        Args:
            scores: List of per-example scores from evaluation batch.

        Returns:
            Aggregated acceptance score (sum or mean based on config).

        Raises:
            InvalidScoreListError: If scores list is empty or contains
                non-finite values.

        Note:
            Outputs aggregated acceptance score after validating scores are
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

    def _build_component_list(self, candidate: Candidate) -> list[str]:
        """Build list of available component keys from candidate.

        Excludes generic 'instruction' alias if agent-specific keys exist
        (e.g., 'agent1_instruction').

        Args:
            candidate: Candidate to extract component keys from.

        Returns:
            List of component keys to consider for update.

        Note:
            Outputs component keys, filtering out generic 'instruction' when
            more specific per-agent instruction keys are present.
        """
        keys = list(candidate.components.keys())
        if len(keys) > 1 and "instruction" in keys:
            # If multiple keys exist, assume 'instruction' might be an alias/proxy
            # or simply one of many.
            # For now, simplistic rule: if other keys exist, exclude 'instruction'.
            return [k for k in keys if k != "instruction"]
        return keys

    async def _initialize_baseline(self) -> None:
        """Initialize baseline evaluation.

        Evaluates the initial candidate on trainset for reflection and
        on valset for scoring. Caches the reflection batch for use in
        the first mutation proposal.

        Note:
            Orchestrates both reflection and scoring baselines up front.
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
        # Use _evaluate_scoring for baseline to get eval_indices
        (
            baseline_score,
            scoring_batch,
            baseline_eval_indices,
        ) = await self._evaluate_scoring(self._initial_candidate)
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
        )
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

            if self._pareto_state is not None:
                candidate_idx = self._pareto_state.add_candidate(
                    self._initial_candidate,
                    scoring_batch.scores,
                    score_indices=baseline_eval_indices,
                    objective_scores=objective_scores,
                    per_example_objective_scores=per_example_objective_scores,
                    logger=logger,
                )
                self._candidate_eval_batches[candidate_idx] = reflection_batch

    async def _evaluate_reflection(
        self, candidate: Candidate
    ) -> tuple[float, EvaluationBatch]:
        """Evaluate a candidate on the trainset for reflection.

        Args:
            candidate: Candidate to evaluate.

        Returns:
            Tuple of (mean score across trainset examples, evaluation batch).

        Note:
            Outputs trajectories for reflective dataset construction.
        """
        eval_batch = await self.adapter.evaluate(
            self._trainset,
            candidate.components,
            capture_traces=True,
        )
        score = sum(eval_batch.scores) / len(eval_batch.scores)
        return score, eval_batch

    async def _evaluate_scoring(
        self, candidate: Candidate
    ) -> tuple[float, EvaluationBatch, list[int]]:
        """Evaluate a candidate on the valset for scoring decisions.

        Args:
            candidate: Candidate to evaluate on the validation set.

        Returns:
            Tuple of (aggregated acceptance score, evaluation batch, eval_indices).
            Score is aggregated using acceptance_metric (sum or mean).
            eval_indices are the valset indices that were actually evaluated.

        Note:
            Outputs scores without traces for acceptance decisions.
            Aggregation method (sum/mean) is determined by config.acceptance_metric.
            Uses evaluation_policy to determine which examples to evaluate.
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
        is_full_eval = len(eval_indices) == len(valset_ids) and set(
            eval_indices
        ) == set(valset_ids)
        eval_valset = (
            self._valset if is_full_eval else [self._valset[i] for i in eval_indices]
        )

        eval_batch = await self.adapter.evaluate(
            eval_valset,
            candidate.components,
            capture_traces=False,
        )
        score = self._aggregate_acceptance_score(eval_batch.scores)
        return score, eval_batch, eval_indices

    async def _propose_mutation(self) -> Candidate:
        """Propose a new candidate via reflective mutation.

        Uses the cached evaluation batch from the most recent best candidate
        evaluation to generate the reflective dataset, avoiding redundant
        adapter calls.

        Returns:
            New candidate with proposed component updates.

        Note:
            Outputs a new candidate with updated components based on reflective
            dataset analysis and component selector strategy.
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
            if selected_idx is not None:
                self._candidate_eval_batches[selected_idx] = eval_batch

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
        return Candidate(
            components=new_components,
            generation=selected_candidate.generation,
            parent_id=selected_candidate.parent_id,
        )

    def _record_iteration(
        self,
        score: float,
        instruction: str,
        accepted: bool,
        objective_scores: list[dict[str, float]] | None = None,
    ) -> None:
        """Record iteration outcome.

        Args:
            score: Score achieved in this iteration.
            instruction: Instruction text evaluated.
            accepted: Whether proposal was accepted.
            objective_scores: Optional objective scores from this iteration's
                evaluation. None when adapter does not provide objective scores.

        Note:
            Outputs an IterationRecord to the engine state's iteration_history,
            preserving chronological evolution trace for analysis.
        """
        assert self._state is not None, "Engine state not initialized"
        record = IterationRecord(
            iteration_number=self._state.iteration,
            score=score,
            instruction=instruction,
            accepted=accepted,
            objective_scores=objective_scores,
        )
        self._state.iteration_history.append(record)

    def _should_stop(self) -> bool:
        """Check if evolution should terminate.

        Returns:
            True if any stopping condition met:
            - iteration >= max_iterations
            - patience > 0 AND stagnation_counter >= patience

        Note:
            Outputs True when max iterations reached or early stopping
            patience is exhausted, signaling evolution loop termination.
        """
        assert self._state is not None, "Engine state not initialized"
        # Condition 1: Max iterations reached
        if self._state.iteration >= self.config.max_iterations:
            return True

        # Condition 2: Early stopping (patience exhausted)
        if self.config.patience > 0:
            if self._state.stagnation_counter >= self.config.patience:
                return True

        return False

    def _should_accept(self, proposal_score: float, best_score: float) -> bool:
        """Check if proposal should be accepted.

        Args:
            proposal_score: Score of the proposed candidate.
            best_score: Current best score.

        Returns:
            True if proposal_score > best_score + min_improvement_threshold.

        Note:
            Outputs True when proposal exceeds best score by the configured
            improvement threshold, enabling configurable acceptance sensitivity.
        """
        threshold = self.config.min_improvement_threshold
        return proposal_score > best_score + threshold

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

        Note:
            Overwrites cached reflection batch for next proposal iteration.
            Tracks acceptance score and valset mean separately.
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

    def _build_result(self) -> EvolutionResult:
        """Build final result from current state.

        Returns:
            Frozen EvolutionResult with all metrics.

        Note:
            Outputs a frozen EvolutionResult containing all evolution metrics
            and history, suitable for immutable result reporting.
        """
        assert self._state is not None, "Engine state not initialized"
        return EvolutionResult(
            original_score=self._state.original_score,
            final_score=self._state.best_score,
            evolved_instruction=self._state.best_candidate.components["instruction"],
            iteration_history=self._state.iteration_history,
            total_iterations=self._state.iteration,
            valset_score=self._state.best_valset_mean,
            trainset_score=self._state.best_reflection_score,
            objective_scores=self._state.best_objective_scores,
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

        Returns:
            EvolutionResult containing:
                - original_score: Baseline score before evolution
                - final_score: Best score achieved
                - evolved_instruction: Best instruction text found
                - iteration_history: List of IterationRecord objects
                - total_iterations: Number of iterations performed

        Raises:
            Exception: Any exceptions from adapter methods propagate unchanged.

        Examples:
            Running evolution:

            ```python
            result = await engine.run()
            print(f"Improved: {result.improved}")
            print(f"Best score: {result.final_score}")
            ```

        Note:
            Outputs a frozen EvolutionResult after completing the evolution
            loop. Engine instance should not be reused after run() completes.
            Method is idempotent if called multiple times (restarts fresh).
            Fail-fast behavior: adapter exceptions are not caught.
        """
        # Initialize baseline
        await self._initialize_baseline()
        assert self._state is not None, "Engine state not initialized"

        # Evolution loop
        while not self._should_stop():
            self._state.iteration += 1

            # Propose mutation
            proposal = await self._propose_mutation()

            # Evaluate proposal
            reflection_score, reflection_batch = await self._evaluate_reflection(
                proposal
            )
            proposal_score, scoring_batch, eval_indices = await self._evaluate_scoring(
                proposal
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
                # Determine parent for genealogy tracking
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
                        merges_due=self._merges_due,
                    )
            else:
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
                if merge_result is not None:
                    self._merges_due -= 1
                    self._merge_invocations += 1
                    logger.info(
                        "merge_scheduling.merge_attempted",
                        iteration=self._state.iteration,
                        parent_indices=merge_result.parent_indices,
                        ancestor_idx=merge_result.metadata.get("ancestor_idx"),
                        merges_due=self._merges_due,
                        total_invocations=self._merge_invocations,
                    )
                    # Evaluate merge proposal
                    (
                        merge_reflection_score,
                        merge_reflection_batch,
                    ) = await self._evaluate_reflection(merge_result.candidate)
                    (
                        merge_proposal_score,
                        merge_scoring_batch,
                        merge_eval_indices,
                    ) = await self._evaluate_scoring(merge_result.candidate)

                    # Add merge candidate to ParetoState
                    merge_candidate_idx = None
                    if self._pareto_state is not None:
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
                                merge_objective_scores_accum: dict[
                                    str, list[float]
                                ] = {}
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
                                merge_objective_scores_by_name: dict[
                                    str, list[float]
                                ] = {}
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
                            merge_score=merge_proposal_score,
                        )
                    else:
                        logger.debug(
                            "merge_scheduling.merge_rejected",
                            iteration=self._state.iteration,
                            merge_score=merge_proposal_score,
                            best_score=self._state.best_score,
                        )
                else:
                    # Merge not possible, decrement counter
                    if self._merges_due > 0:
                        self._merges_due -= 1

            # Record iteration
            self._record_iteration(
                score=proposal_score,
                instruction=proposal.components["instruction"],
                accepted=accepted,
                objective_scores=scoring_batch.objective_scores,
            )

        # Build and return result
        return self._build_result()
