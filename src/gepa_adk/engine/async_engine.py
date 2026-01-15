"""Async evolution engine implementation.

This module contains the AsyncGEPAEngine class that orchestrates the
core evolution loop for optimizing agent instructions using async-first
design principles.

Note:
    Tracks separate trainset and valset evaluation flows for evolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

import structlog

from gepa_adk.domain.exceptions import NoCandidateAvailableError
from gepa_adk.domain.models import (
    Candidate,
    EvolutionConfig,
    EvolutionResult,
    IterationRecord,
)
from gepa_adk.domain.state import ParetoState
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
from gepa_adk.ports.selector import CandidateSelectorProtocol

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
        best_score (float): Score of best candidate.
        original_score (float): Baseline score from first evaluation.
        iteration (int): Current iteration number (0-based internally,
            1-indexed in records).
        stagnation_counter (int): Iterations since last improvement.
        iteration_history (list[IterationRecord]): All iteration records.
        last_eval_batch (EvaluationBatch | None): Cached reflection batch from
            most recent best candidate evaluation on the trainset (for
            reflective dataset generation).
        best_reflection_score (float): Mean score from the best candidate's
            latest trainset reflection evaluation.

    Note:
        Aggregates reflection metadata needed to drive proposal generation.
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
            raise ValueError("valset must contain at least one data instance")

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
        self._pareto_state: ParetoState | None = None
        self._candidate_eval_batches: dict[int, EvaluationBatch] = {}

    async def _initialize_baseline(self) -> None:
        """Initialize baseline evaluation.

        Evaluates the initial candidate on trainset for reflection and
        on valset for scoring. Caches the reflection batch for use in
        the first mutation proposal.

        Note:
            Orchestrates both reflection and scoring baselines up front.
        """
        reflection_batch = await self.adapter.evaluate(
            self._trainset,
            self._initial_candidate.components,
            capture_traces=True,
        )
        scoring_batch = await self.adapter.evaluate(
            self._valset,
            self._initial_candidate.components,
            capture_traces=False,
        )
        baseline_score = sum(scoring_batch.scores) / len(scoring_batch.scores)
        baseline_reflection_score = sum(reflection_batch.scores) / len(
            reflection_batch.scores
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
        )
        if self._candidate_selector is not None:
            self._pareto_state = ParetoState(frontier_type=self.config.frontier_type)
            candidate_idx = self._pareto_state.add_candidate(
                self._initial_candidate,
                scoring_batch.scores,
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
    ) -> tuple[float, EvaluationBatch]:
        """Evaluate a candidate on the valset for scoring decisions.

        Note:
            Outputs scores without traces for acceptance decisions.
        """
        eval_batch = await self.adapter.evaluate(
            self._valset,
            candidate.components,
            capture_traces=False,
        )
        score = sum(eval_batch.scores) / len(eval_batch.scores)
        return score, eval_batch

    async def _propose_mutation(self) -> Candidate:
        """Propose a new candidate via reflective mutation.

        Uses the cached evaluation batch from the most recent best candidate
        evaluation to generate the reflective dataset, avoiding redundant
        adapter calls.

        Returns:
            New candidate with proposed component updates.
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

        # Build reflective dataset
        components_to_update = ["instruction"]  # v1: only instruction
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
    ) -> None:
        """Record iteration outcome.

        Args:
            score: Score achieved in this iteration.
            instruction: Instruction text evaluated.
            accepted: Whether proposal was accepted.
        """
        assert self._state is not None, "Engine state not initialized"
        record = IterationRecord(
            iteration_number=self._state.iteration,
            score=score,
            instruction=instruction,
            accepted=accepted,
        )
        self._state.iteration_history.append(record)

    def _should_stop(self) -> bool:
        """Check if evolution should terminate.

        Returns:
            True if any stopping condition met:
            - iteration >= max_iterations
            - patience > 0 AND stagnation_counter >= patience
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
    ) -> None:
        """Accept a proposal and update state.

        Args:
            proposal: Proposed candidate to accept.
            score: Score of the proposed candidate.
            eval_batch: Reflection batch from proposal evaluation (cached for
                next iteration's reflective dataset generation).
            candidate_idx: Optional ParetoState candidate index to update with
                lineage metadata.
            reflection_score: Optional trainset score to store with best
                candidate metadata.

        Note:
            Overwrites cached reflection batch for next proposal iteration.
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

    def _build_result(self) -> EvolutionResult:
        """Build final result from current state.

        Returns:
            Frozen EvolutionResult with all metrics.
        """
        assert self._state is not None, "Engine state not initialized"
        return EvolutionResult(
            original_score=self._state.original_score,
            final_score=self._state.best_score,
            evolved_instruction=self._state.best_candidate.components["instruction"],
            iteration_history=self._state.iteration_history,
            total_iterations=self._state.iteration,
            valset_score=self._state.best_score,
            trainset_score=self._state.best_reflection_score,
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
            Engine instance should not be reused after run() completes.
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
            proposal_score, scoring_batch = await self._evaluate_scoring(proposal)

            candidate_idx = None
            if self._pareto_state is not None:
                candidate_idx = self._pareto_state.add_candidate(
                    proposal,
                    scoring_batch.scores,
                    logger=logger,
                )
                self._candidate_eval_batches[candidate_idx] = reflection_batch
                logger.info(
                    "pareto_frontier.candidate_added",
                    candidate_idx=candidate_idx,
                    iteration=self._state.iteration,
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
                )
            else:
                # Increment stagnation counter on rejection
                self._state.stagnation_counter += 1

            # Record iteration
            self._record_iteration(
                score=proposal_score,
                instruction=proposal.components["instruction"],
                accepted=accepted,
            )

        # Build and return result
        return self._build_result()
