"""Domain models for Pareto frontier tracking.

Examples:
    Basic ParetoState usage:

    ```python
    from gepa_adk.domain.models import Candidate
    from gepa_adk.domain.state import ParetoState

    state = ParetoState()
    idx = state.add_candidate(
        Candidate(components={"instruction": "Be helpful."}),
        [0.8, 0.7, 0.9],
    )
    print(state.get_average_score(idx))  # 0.8
    ```

Note:
    This module captures Pareto frontier leaders and candidate state.

See Also:
    - [`gepa_adk.domain.models.Candidate`][gepa_adk.domain.models.Candidate]:
        Domain model stored by ParetoState during evolution.
    - [`gepa_adk.ports.candidate_selector`][gepa_adk.ports.candidate_selector]:
        Protocol that consumes ParetoState for parent selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import fmean
from typing import Protocol, Sequence

from gepa_adk.domain.exceptions import ConfigurationError, NoCandidateAvailableError
from gepa_adk.domain.models import Candidate
from gepa_adk.domain.types import FrontierKey, FrontierType, Score


class FrontierLogger(Protocol):
    """Protocol for logging frontier update events.

    Note:
        A lightweight logger interface keeps frontier updates consistent.

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
    """Tracks non-dominated candidates across multiple frontier dimensions.

    Attributes:
        example_leaders (dict[int, set[int]]): Instance-level mapping of
            example_idx to leader candidate indices.
        best_scores (dict[int, float]): Instance-level mapping of
            example_idx to best score.
        objective_leaders (dict[str, set[int]]): Objective-level mapping of
            objective_name to leader candidate indices.
        objective_best_scores (dict[str, float]): Objective-level mapping of
            objective_name to best score.
        cartesian_leaders (dict[tuple[int, str], set[int]]): Cartesian mapping of
            (example_idx, objective) to leader candidate indices.
        cartesian_best_scores (dict[tuple[int, str], float]): Cartesian mapping of
            (example_idx, objective) to best score.

    Examples:
        ```python
        frontier = ParetoFrontier()
        frontier.update(0, {0: 0.8, 1: 0.6})
        ```

    Note:
        A frontier stores the best candidate indices per dimension for sampling.
        The active dimension depends on frontier_type.
    """

    example_leaders: dict[int, set[int]] = field(default_factory=dict)
    best_scores: dict[int, float] = field(default_factory=dict)
    objective_leaders: dict[str, set[int]] = field(default_factory=dict)
    objective_best_scores: dict[str, float] = field(default_factory=dict)
    cartesian_leaders: dict[tuple[int, str], set[int]] = field(default_factory=dict)
    cartesian_best_scores: dict[tuple[int, str], float] = field(default_factory=dict)

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

        Note:
            Outputs updated leader sets and best scores for instance-level
            frontier tracking.

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
        """Return candidate indices that lead any example.

        Returns:
            Set of candidate indices that are non-dominated (lead at
            least one example).

        Note:
            Outputs the union of all leader sets across example indices.
        """
        candidates: set[int] = set()
        for leaders in self.example_leaders.values():
            candidates.update(leaders)
        return candidates

    def get_selection_weights(self) -> dict[int, int]:
        """Return selection weights based on leadership frequency.

        Returns:
            Mapping of candidate index to leadership count, usable as
            weights for weighted sampling.

        Note:
            Outputs weights proportional to how many examples each candidate
            leads, enabling weighted sampling.
        """
        weights: dict[int, int] = {}
        for leaders in self.example_leaders.values():
            for candidate_idx in leaders:
                weights[candidate_idx] = weights.get(candidate_idx, 0) + 1
        return weights

    def update_objective(
        self,
        candidate_idx: int,
        objective_scores: dict[str, float],
        *,
        logger: FrontierLogger | None = None,
    ) -> None:
        """Update objective-level frontier with a candidate's objective scores.

        Args:
            candidate_idx: Index of the candidate being added.
            objective_scores: Mapping of objective name to score.
            logger: Optional structured logger for leader updates.

        Note:
            Outputs updated objective leader sets and best scores for
            objective-level frontier tracking.

        Examples:
            ```python
            frontier.update_objective(0, {"accuracy": 0.9, "latency": 0.7})
            ```
        """
        for objective_name, score in objective_scores.items():
            best_score = self.objective_best_scores.get(objective_name)
            if best_score is None or score > best_score:
                previous_leaders = self.objective_leaders.get(objective_name, set())
                self.objective_best_scores[objective_name] = score
                self.objective_leaders[objective_name] = {candidate_idx}
                if logger is not None:
                    logger.info(
                        "pareto_frontier.objective_leader_updated",
                        objective_name=objective_name,
                        candidate_idx=candidate_idx,
                        score=score,
                        previous_leaders=sorted(previous_leaders),
                    )
            elif score == best_score:
                leaders = self.objective_leaders.setdefault(objective_name, set())
                if candidate_idx not in leaders:
                    leaders.add(candidate_idx)
                    if logger is not None:
                        logger.info(
                            "pareto_frontier.objective_leader_tied",
                            objective_name=objective_name,
                            candidate_idx=candidate_idx,
                            score=score,
                        )

    def update_cartesian(
        self,
        candidate_idx: int,
        scores: dict[int, float],
        objective_scores: dict[int, dict[str, float]],
        *,
        logger: FrontierLogger | None = None,
    ) -> None:
        """Update cartesian frontier per (example, objective) pair.

        Args:
            candidate_idx: Index of the candidate being added.
            scores: Mapping of example index to score.
            objective_scores: Mapping of example index to objective scores dict.
            logger: Optional structured logger for leader updates.

        Note:
            Outputs updated cartesian leader sets and best scores for
            per (example, objective) pair frontier tracking.

        Examples:
            ```python
            frontier.update_cartesian(
                0, {0: 0.8, 1: 0.6}, {0: {"accuracy": 0.9}, 1: {"accuracy": 0.7}}
            )
            ```
        """
        for example_idx, example_objectives in objective_scores.items():
            for objective_name, score in example_objectives.items():
                key = (example_idx, objective_name)
                best_score = self.cartesian_best_scores.get(key)
                if best_score is None or score > best_score:
                    previous_leaders = self.cartesian_leaders.get(key, set())
                    self.cartesian_best_scores[key] = score
                    self.cartesian_leaders[key] = {candidate_idx}
                    if logger is not None:
                        logger.info(
                            "pareto_frontier.cartesian_leader_updated",
                            example_idx=example_idx,
                            objective_name=objective_name,
                            candidate_idx=candidate_idx,
                            score=score,
                            previous_leaders=sorted(previous_leaders),
                        )
                elif score == best_score:
                    leaders = self.cartesian_leaders.setdefault(key, set())
                    if candidate_idx not in leaders:
                        leaders.add(candidate_idx)
                        if logger is not None:
                            logger.info(
                                "pareto_frontier.cartesian_leader_tied",
                                example_idx=example_idx,
                                objective_name=objective_name,
                                candidate_idx=candidate_idx,
                                score=score,
                            )

    def get_pareto_front_mapping(
        self, frontier_type: FrontierType
    ) -> dict[FrontierKey, set[int]]:
        """Return frontier mapping for specified frontier type.

        Args:
            frontier_type (FrontierType): Type of frontier to return mapping for.

        Returns:
            dict[FrontierKey, set[int]]: Mapping from frontier key to set of
                candidate indices.

        Raises:
            ValueError: If frontier_type is not a supported value.

        Note:
            Outputs a mapping with keys appropriate for the frontier type
            (int for INSTANCE, str for OBJECTIVE, tuples for HYBRID/CARTESIAN).

        Examples:
            ```python
            mapping = frontier.get_pareto_front_mapping(FrontierType.INSTANCE)
            # Returns: {0: {1, 2}, 1: {2, 3}}
            ```
        """
        if frontier_type == FrontierType.INSTANCE:
            return {
                key: leaders.copy() for key, leaders in self.example_leaders.items()
            }
        elif frontier_type == FrontierType.OBJECTIVE:
            return {
                key: leaders.copy() for key, leaders in self.objective_leaders.items()
            }
        elif frontier_type == FrontierType.HYBRID:
            mapping: dict[FrontierKey, set[int]] = {}
            # Add instance-level with type tag
            for example_idx, leaders in self.example_leaders.items():
                mapping[("val_id", example_idx)] = leaders.copy()
            # Add objective-level with type tag
            for objective_name, leaders in self.objective_leaders.items():
                mapping[("objective", objective_name)] = leaders.copy()
            return mapping
        elif frontier_type == FrontierType.CARTESIAN:
            mapping: dict[FrontierKey, set[int]] = {}
            for (
                example_idx,
                objective_name,
            ), leaders in self.cartesian_leaders.items():
                mapping[("cartesian", example_idx, objective_name)] = leaders.copy()
            return mapping
        else:
            raise ValueError(f"Unknown frontier type: {frontier_type}")


@dataclass(slots=True)
class ParetoState:
    """Tracks evolution state for Pareto-aware selection.

    Attributes:
        candidates (list[Candidate]): Candidates discovered during evolution.
        candidate_scores (dict[int, dict[int, float]]): Per-example scores
            mapping candidate index to example-score mappings.
        frontier (ParetoFrontier): Current frontier leader sets.
        frontier_type (FrontierType): Frontier tracking strategy.
        iteration (int): Current iteration number.
        best_average_idx (int | None): Index of best-average candidate.
        parent_indices (dict[int, list[int | None]]): Genealogy map tracking
            parent relationships, mapping candidate_idx to parent index list
            or ``[None]`` for seeds.

    Examples:
        ```python
        state = ParetoState()
        state.add_candidate(Candidate(components={"instruction": "seed"}), [0.5])
        ```

    Note:
        A single state object keeps frontier and candidate metrics aligned.
    """

    candidates: list[Candidate] = field(default_factory=list)
    candidate_scores: dict[int, dict[int, float]] = field(default_factory=dict)
    candidate_objective_scores: dict[int, dict[str, float]] = field(
        default_factory=dict
    )
    frontier: ParetoFrontier = field(default_factory=ParetoFrontier)
    frontier_type: FrontierType = FrontierType.INSTANCE
    iteration: int = 0
    best_average_idx: int | None = None
    parent_indices: dict[int, list[int | None]] = field(default_factory=dict)
    _frontier_type_initialized: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Validate state configuration and initialize averages.

        Raises:
            ConfigurationError: If any candidate_scores index exceeds the
                candidates list length.

        Note:
            Checks candidate_scores indices are valid and marks frontier_type
            as initialized for immutability enforcement.
        """
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
        self._frontier_type_initialized = True
        self.update_best_average()

    def __setattr__(self, name: str, value: object) -> None:
        """Enforce frontier_type immutability after initialization (T069).

        Raises:
            ConfigurationError: If frontier_type is changed after
                ParetoState initialization.

        Note:
            Only frontier_type is protected because it determines the frontier
            update routing logic in add_candidate(). Other fields (candidates,
            frontier, candidate_scores) are intentionally mutable to support
            evolution state updates. Using frozen=True would prevent all
            mutations, which is too restrictive for evolution state management.
        """
        # Allow setting during __init__ and __post_init__
        if name == "frontier_type":
            # Check if we're in initialization phase
            if hasattr(self, "_frontier_type_initialized"):
                # Already initialized, check if we're trying to change it
                if (
                    self._frontier_type_initialized
                    and getattr(self, "frontier_type", None) != value
                ):
                    raise ConfigurationError(
                        "frontier_type cannot be changed after ParetoState initialization",
                        field="frontier_type",
                        value=value,
                        constraint="immutable after initialization",
                    )
        # Use object.__setattr__ to avoid recursion during initialization
        object.__setattr__(self, name, value)

    @staticmethod
    def _validate_parent_indices(
        indices: Sequence[int | None], label: str
    ) -> list[int | None]:
        """Validate parent indices for genealogy tracking.

        Returns:
            Validated list of parent indices (int or None).

        Raises:
            TypeError: If any element in indices is not int or None.
        """
        validated: list[int | None] = []
        for idx, parent_idx in enumerate(indices):
            if not (isinstance(parent_idx, int) or parent_idx is None):
                raise TypeError(
                    f"{label} elements must be int or None; "
                    f"got {type(parent_idx).__name__} at position {idx}"
                )
            validated.append(parent_idx)
        return validated

    def add_candidate(
        self,
        candidate: Candidate,
        scores: Sequence[Score],
        *,
        score_indices: Sequence[int] | None = None,
        objective_scores: dict[str, float] | None = None,
        per_example_objective_scores: dict[int, dict[str, float]] | None = None,
        parent_indices: list[int] | None = None,
        logger: FrontierLogger | None = None,
    ) -> int:
        """Add a candidate and update frontier tracking.

        Args:
            candidate: Candidate to add.
            scores: Per-example scores for the candidate.
            score_indices: Optional sequence mapping scores to example indices.
                If None, scores are assumed to be indexed 0, 1, 2, ... (full valset).
                If provided, scores[i] corresponds to example index score_indices[i].
            objective_scores: Optional aggregated objective scores
                (required for OBJECTIVE, HYBRID, CARTESIAN).
            per_example_objective_scores: Optional per-example objective scores
                (required for CARTESIAN).
            parent_indices: Optional parent candidate indices for genealogy tracking.
                If None, uses candidate.parent_ids if available, otherwise [None] for seed.
            logger: Optional structured logger for frontier updates.

        Returns:
            Index of the newly added candidate.

        Raises:
            ConfigurationError: If objective_scores are required but not provided.

        Note:
            Outputs the new candidate index after routing to the appropriate
            frontier update method based on frontier_type.

        Examples:
            ```python
            candidate_idx = state.add_candidate(candidate, [0.7, 0.8])
            candidate_idx = state.add_candidate(
                candidate, [0.7, 0.8], objective_scores={"accuracy": 0.9}
            )
            ```
        """
        # Validate objective_scores requirement for objective-based frontier types
        if self.frontier_type in (
            FrontierType.OBJECTIVE,
            FrontierType.HYBRID,
            FrontierType.CARTESIAN,
        ):
            if objective_scores is None:
                raise ConfigurationError(
                    "objective_scores required for frontier_type",
                    field="objective_scores",
                    value=None,
                    constraint=f"required for {self.frontier_type}",
                )
            if (
                self.frontier_type == FrontierType.CARTESIAN
                and per_example_objective_scores is None
            ):
                raise ConfigurationError(
                    "per_example_objective_scores required for CARTESIAN frontier_type",
                    field="per_example_objective_scores",
                    value=None,
                    constraint="required for CARTESIAN",
                )

        candidate_idx = len(self.candidates)
        self.candidates.append(candidate)

        # Track parent indices for genealogy
        if parent_indices is not None:
            self.parent_indices[candidate_idx] = self._validate_parent_indices(
                parent_indices, "parent_indices"
            )
        elif candidate.parent_ids is not None:
            self.parent_indices[candidate_idx] = self._validate_parent_indices(
                candidate.parent_ids, "candidate.parent_ids"
            )
        else:
            # Seed candidate with no parents
            self.parent_indices[candidate_idx] = [None]

        # Map scores to example indices
        if score_indices is not None:
            if len(score_indices) != len(scores):
                raise ValueError(
                    f"score_indices length ({len(score_indices)}) must match "
                    f"scores length ({len(scores)})"
                )
            score_map = dict(zip(score_indices, scores))
        else:
            # Default: scores are indexed 0, 1, 2, ... (full valset)
            score_map = dict(enumerate(scores))
        self.candidate_scores[candidate_idx] = score_map

        # Store objective scores if provided
        if objective_scores is not None:
            self.candidate_objective_scores[candidate_idx] = objective_scores

        # Route to appropriate frontier update based on frontier_type
        if self.frontier_type == FrontierType.INSTANCE:
            self.frontier.update(candidate_idx, score_map, logger=logger)
        elif self.frontier_type == FrontierType.OBJECTIVE:
            assert objective_scores is not None  # Validated above
            self.frontier.update_objective(
                candidate_idx, objective_scores, logger=logger
            )
        elif self.frontier_type == FrontierType.HYBRID:
            assert objective_scores is not None  # Validated above
            self.frontier.update(candidate_idx, score_map, logger=logger)
            self.frontier.update_objective(
                candidate_idx, objective_scores, logger=logger
            )
        elif self.frontier_type == FrontierType.CARTESIAN:
            assert objective_scores is not None  # Validated above
            assert per_example_objective_scores is not None  # Validated above
            self.frontier.update_cartesian(
                candidate_idx, score_map, per_example_objective_scores, logger=logger
            )
        else:
            raise ValueError(f"Unknown frontier type: {self.frontier_type}")

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

        Note:
            Outputs the arithmetic mean of all scores for the candidate
            across evaluated examples.

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
        """Update best_average_idx based on current scores.

        Note:
            Outputs the candidate index with the highest mean score, or None
            if no candidates have scores.
        """
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
