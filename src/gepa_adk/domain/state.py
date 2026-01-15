"""Domain models for Pareto frontier tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import Protocol, Sequence

from gepa_adk.domain.exceptions import ConfigurationError, NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.types import FrontierType, Score


class FrontierLogger(Protocol):
    """Protocol for logging frontier update events.

    Examples:
        ```python
        class Logger:
            def info(self, event: str, **kwargs: object) -> None:
                print(event, kwargs)


        logger: FrontierLogger = Logger()
        logger.info("pareto_frontier.updated", example_idx=0, candidate_idx=1)
        ```
    """

    def info(self, event: str, **kwargs: object) -> None:
        """Emit a structured info log event.

        Args:
            event: Event name identifier.

        Other Parameters:
            **kwargs: Structured metadata for the event.

        Examples:
            ```python
            logger.info("pareto_frontier.leader_updated", example_idx=0, score=0.9)
            ```
        """


@dataclass(slots=True)
class ParetoFrontier:
    """Tracks example-level leaders for Pareto selection.

    Attributes:
        example_leaders (dict[int, set[int]]): Example index to leader indices.
        best_scores (dict[int, float]): Example index to best score seen.

    Examples:
        ```python
        frontier = ParetoFrontier()
        frontier.update(0, {0: 0.8, 1: 0.6})
        ```
    """

    example_leaders: dict[int, set[int]] = field(default_factory=dict)
    best_scores: dict[int, float] = field(default_factory=dict)

    def update(
        self,
        candidate_idx: int,
        scores: dict[int, float],
        *,
        logger: FrontierLogger | None = None,
    ) -> None:
        """Update frontier leadership with a candidate's scores.

        Args:
            candidate_idx: Index of the candidate being added.
            scores: Mapping of example index to score.
            logger: Optional structured logger for leader updates.

        Examples:
            ```python
            frontier.update(2, {0: 0.7, 1: 0.9})
            ```
        """
        for example_idx, score in scores.items():
            best_score = self.best_scores.get(example_idx)
            if best_score is None or score > best_score:
                previous_leaders = self.example_leaders.get(example_idx, set())
                self.best_scores[example_idx] = score
                self.example_leaders[example_idx] = {candidate_idx}
                if logger is not None:
                    logger.info(
                        "pareto_frontier.leader_updated",
                        example_idx=example_idx,
                        candidate_idx=candidate_idx,
                        score=score,
                        previous_leaders=sorted(previous_leaders),
                    )
            elif score == best_score:
                leaders = self.example_leaders.setdefault(example_idx, set())
                if candidate_idx not in leaders:
                    leaders.add(candidate_idx)
                    if logger is not None:
                        logger.info(
                            "pareto_frontier.leader_tied",
                            example_idx=example_idx,
                            candidate_idx=candidate_idx,
                            score=score,
                        )

    def get_non_dominated(self) -> set[int]:
        """Return candidate indices that lead any example."""
        candidates: set[int] = set()
        for leaders in self.example_leaders.values():
            candidates.update(leaders)
        return candidates

    def get_selection_weights(self) -> dict[int, int]:
        """Return selection weights based on leadership frequency."""
        weights: dict[int, int] = {}
        for leaders in self.example_leaders.values():
            for candidate_idx in leaders:
                weights[candidate_idx] = weights.get(candidate_idx, 0) + 1
        return weights


@dataclass(slots=True)
class ParetoState:
    """Tracks evolution state for Pareto-aware selection.

    Attributes:
        candidates (list[Candidate]): Candidates discovered during evolution.
        candidate_scores (dict[int, dict[int, float]]): Per-example scores.
        frontier (ParetoFrontier): Current frontier leader sets.
        frontier_type (FrontierType): Frontier tracking strategy.
        iteration (int): Current iteration number.
        best_average_idx (int | None): Index of best-average candidate.

    Examples:
        ```python
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])
        ```
    """

    candidates: list[Candidate] = field(default_factory=list)
    candidate_scores: dict[int, dict[int, float]] = field(default_factory=dict)
    frontier: ParetoFrontier = field(default_factory=ParetoFrontier)
    frontier_type: FrontierType = FrontierType.INSTANCE
    iteration: int = 0
    best_average_idx: int | None = None

    def __post_init__(self) -> None:
        """Validate state configuration and initialize averages."""
        if self.frontier_type is not FrontierType.INSTANCE:
            raise ConfigurationError(
                "frontier_type is not supported in this feature",
                field="frontier_type",
                value=self.frontier_type,
                constraint="FrontierType.INSTANCE",
            )

        if self.candidate_scores:
            max_index = len(self.candidates) - 1
            for candidate_idx in self.candidate_scores:
                if candidate_idx > max_index:
                    raise ConfigurationError(
                        "candidate_scores index out of range",
                        field="candidate_scores",
                        value=candidate_idx,
                        constraint="<= len(candidates) - 1",
                    )
        self.update_best_average()

    def add_candidate(
        self,
        candidate: Candidate,
        scores: Sequence[Score],
        *,
        logger: FrontierLogger | None = None,
    ) -> int:
        """Add a candidate and update frontier tracking.

        Args:
            candidate: Candidate to add.
            scores: Per-example scores for the candidate.
            logger: Optional structured logger for frontier updates.

        Returns:
            Index of the newly added candidate.

        Raises:
            ConfigurationError: If frontier_type is unsupported.

        Examples:
            ```python
            candidate_idx = state.add_candidate(candidate, [0.7, 0.8])
            ```
        """
        if self.frontier_type is not FrontierType.INSTANCE:
            raise ConfigurationError(
                "frontier_type is not supported in this feature",
                field="frontier_type",
                value=self.frontier_type,
                constraint="FrontierType.INSTANCE",
            )

        candidate_idx = len(self.candidates)
        self.candidates.append(candidate)
        score_map = {idx: score for idx, score in enumerate(scores)}
        self.candidate_scores[candidate_idx] = score_map
        self.frontier.update(candidate_idx, score_map, logger=logger)
        self.update_best_average()
        return candidate_idx

    def get_average_score(self, candidate_idx: int) -> float:
        """Return average score for a candidate.

        Args:
            candidate_idx: Index of the candidate.

        Returns:
            Mean score across examples.

        Raises:
            NoCandidateAvailableError: If candidate scores are missing.

        Examples:
            ```python
            average = state.get_average_score(candidate_idx)
            ```
        """
        scores = self.candidate_scores.get(candidate_idx)
        if not scores:
            raise NoCandidateAvailableError(
                "No scores available for candidate",
                candidate_idx=candidate_idx,
            )
        return fmean(scores.values())

    def update_best_average(self) -> None:
        """Update best_average_idx based on current scores."""
        if not self.candidate_scores:
            self.best_average_idx = None
            return
        best_idx = None
        best_score = float("-inf")
        for candidate_idx, scores in self.candidate_scores.items():
            average = fmean(scores.values())
            if average > best_score:
                best_score = average
                best_idx = candidate_idx
        self.best_average_idx = best_idx
