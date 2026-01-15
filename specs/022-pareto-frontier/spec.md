# Feature Specification: Pareto Frontier Tracking and Candidate Selection

**Feature Branch**: `022-pareto-frontier`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "GitHub Issue #52 - [Feature] Add Pareto frontier tracking and candidate selection strategies"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pareto Frontier Candidate Selection (Priority: P1)

As a gepa-adk user running prompt evolution, I want candidates to be selected from a Pareto frontier instead of always picking the single best candidate, so that evolution explores diverse solutions that excel on different inputs.

**Why this priority**: This is GEPA's core differentiator from simple greedy optimization. Without Pareto-aware selection, the system cannot discover specialized candidates that perform well on different subsets of validation examples.

**Independent Test**: Can be fully tested by running an evolution with multiple validation examples and verifying that candidates with different strengths are selected proportionally, not just the highest-scoring one.

**Acceptance Scenarios**:

1. **Given** multiple candidates tracked in the Pareto frontier, **When** proposing a new mutation, **Then** a candidate is sampled from the Pareto front proportional to leadership frequency (count of examples where the candidate is among the best).
2. **Given** a Pareto frontier with candidates A (high on example 1, low on example 2) and B (low on example 1, high on example 2), **When** requesting the next candidate for mutation, **Then** both A and B have a chance of being selected.
3. **Given** a candidate that dominates all others on all examples, **When** requesting the next candidate, **Then** the dominant candidate is selected as the sole non-dominated option.

---

### User Story 2 - Per-Example Best Score Tracking (Priority: P2)

As a gepa-adk user with diverse validation examples, I want the system to track which candidates perform best on each specific validation example (instance frontier), so that specialized prompts are preserved rather than only generalist prompts.

**Why this priority**: Per-example tracking enables discovery of prompts that excel in specific domains or input types, which is essential for complex tasks where no single prompt works best for all cases.

**Independent Test**: Can be fully tested by configuring `frontier_type="instance"`, running evolution with 3+ diverse validation examples, and verifying that candidates best on any single example remain in the frontier even if their average score is lower.

**Acceptance Scenarios**:

1. **Given** `frontier_type="instance"` is configured, **When** candidates have different strengths on different validation examples, **Then** candidates that dominate on any example are kept in the frontier.
2. **Given** candidate X scores 0.95 on example 1 but 0.50 on examples 2-5, and candidate Y scores 0.70 across all examples, **When** the frontier is updated, **Then** both X and Y are retained (X dominates example 1, Y is competitive overall).

---

### User Story 3 - Multiple Candidate Selection Strategies (Priority: P3)

As a gepa-adk user, I want to choose between different candidate selection strategies (Pareto sampling, greedy best, epsilon-greedy), so that I can tune the exploration-exploitation tradeoff for my specific use case.

**Why this priority**: Different optimization problems benefit from different selection strategies. Providing options allows users to customize behavior for their needs.

**Independent Test**: Can be fully tested by configuring each selector type and verifying that selection behavior matches the expected strategy (e.g., epsilon-greedy selects random candidate ~epsilon fraction of the time).

**Acceptance Scenarios**:

1. **Given** `ParetoCandidateSelector` is configured, **When** selecting a candidate, **Then** candidates are sampled from the Pareto front proportional to their scores.
2. **Given** `CurrentBestCandidateSelector` is configured, **When** selecting a candidate, **Then** the candidate with the highest average score is always selected.
3. **Given** `EpsilonGreedyCandidateSelector` with `epsilon=0.1` is configured, **When** selecting candidates over many iterations, **Then** approximately 10% of selections are random exploration and 90% are the current best.

---

### Edge Cases

- What happens when the Pareto frontier is empty (no candidates yet)?
  - Selector raises NoCandidateAvailableError (EvolutionError subclass); engine handles by initializing baseline or returning no candidate.
- What happens when all candidates have identical scores?
  - All candidates are non-dominated, so any can be selected with equal probability.
- What happens when a new candidate dominates all existing frontier members?
  - The frontier should be updated to contain only the new dominant candidate.
- How does the system handle validation examples being added or removed mid-evolution?
  - Not supported in this iteration; evolution must be restarted to recalculate the frontier.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track which candidates perform best on which validation examples (Pareto frontier tracking).
- **FR-002**: System MUST support selecting candidates from the Pareto frontier with probability proportional to leadership frequency (`ParetoCandidateSelector`).
- **FR-003**: System MUST support selecting the candidate with the highest average score (`CurrentBestCandidateSelector`).
- **FR-004**: System MUST support epsilon-greedy selection that explores random candidates with probability epsilon (`EpsilonGreedyCandidateSelector`).
- **FR-005**: System MUST support the "instance" frontier type that tracks best candidates per validation example.
- **FR-006**: System MUST update the Pareto frontier when new candidates are evaluated, removing dominated candidates.
- **FR-007**: System MUST allow configuring the candidate selection strategy at evolution initialization.
- **FR-008**: System MUST provide the selected candidate to the mutation/proposal component for generating new candidates.
- **FR-009**: System MUST handle empty frontier states gracefully (e.g., at evolution start).
- **FR-010**: System MUST integrate Pareto frontier tracking with the existing evolution engine.

### Key Entities

- **Candidate**: A prompt variant being evolved, with scores on each validation example.
- **ParetoFrontier**: Collection of non-dominated candidates, tracking per-example best scores.
- **CandidateSelector**: Strategy for choosing which candidate to mutate next (Pareto, greedy, epsilon-greedy).
- **ValidationExample**: A single input used to evaluate candidate performance; candidates may specialize on specific examples.
- **FrontierType**: Configuration for what dimensions to track. Initial scope: INSTANCE only. Future: OBJECTIVE, HYBRID, CARTESIAN.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Evolution discovers at least 2 distinct candidate specializations when run with 3+ diverse validation examples (vs. single best with greedy selection).
- **SC-002**: Pareto frontier selection results in at least 30% of mutations originating from non-top-scoring candidates (demonstrating exploration).
- **SC-003**: All three candidate selectors (Pareto, greedy, epsilon-greedy) are available and configurable by users.
- **SC-004**: Epsilon-greedy selector produces exploration selections within 5% of the configured epsilon rate over 100+ selections.
- **SC-005**: Frontier update operations complete in under 10ms for frontiers containing up to 100 candidates and 50 validation examples.

## Assumptions

- The existing evolution engine supports pluggable candidate selection (or will be modified to support it).
- Validation examples and their scores are already available from the evaluation/scoring system.
- Per-example scores are stored and accessible for frontier calculations.
- Initial implementation focuses on "instance" frontier type only. The FrontierType enum will define all four values (INSTANCE, OBJECTIVE, HYBRID, CARTESIAN) for forward compatibility, but only INSTANCE is implemented in this feature. Other types are deferred to future iterations.
