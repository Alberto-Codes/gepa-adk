# Feature Specification: Align Acceptance Scoring with Upstream GEPA

**Feature Branch**: `025-acceptance-scoring`
**Created**: 2026-01-15
**Status**: Draft
**Input**: GitHub Issue #61: "Align acceptance scoring with upstream GEPA"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Acceptance Uses Minibatch Sum (Priority: P1)

As a gepa-adk user, I want acceptance decisions during evolution to use the sum of
per-example scores on the iteration evaluation batch (minibatch), so that
accept/reject behavior matches upstream GEPA and results are comparable.

**Why this priority**: Acceptance semantics define which candidates become the new
best; mismatched scoring changes evolution behavior and makes comparisons against
upstream GEPA unreliable.

**Independent Test**: Can be fully tested by running a unit-level evolution step
with a fixed evaluation batch and deterministic scores and verifying that
acceptance uses sum-based comparison.

**Acceptance Scenarios**:

1. **Given** an iteration evaluation batch of 3 examples with scores 0.3, 0.3,
   0.3, and the current best acceptance score is 0.8, **When** a proposed
   candidate achieves a total (sum) score of 0.9 on that batch, **Then** the
   proposal is accepted even if its mean score is 0.3.

2. **Given** two candidates evaluated on the same iteration evaluation batch,
   **When** candidate A has per-example scores summing to a larger value than
   candidate B, **Then** candidate A is preferred by the acceptance decision.

---

### User Story 2 - Valset Tracking Uses Mean (Priority: P2)

As a researcher or user monitoring progress, I want validation-set performance to
be tracked using mean scoring, so that reported metrics are comparable across
different validation-set sizes and consistent with existing reporting patterns.

**Why this priority**: Mean valset scoring is the most interpretable and stable
metric for progress reporting and for comparing runs across datasets.

**Independent Test**: Can be tested by evaluating a candidate on a known valset
and verifying the tracked valset score equals the arithmetic mean of per-example
scores.

**Acceptance Scenarios**:

1. **Given** a valset of 10 examples with per-example scores, **When** a
   candidate is evaluated on the valset, **Then** the tracked valset score is
   the mean of those per-example scores.

---

### User Story 3 - Backward Compatibility Toggle (Priority: P3)

As a gepa-adk user with existing experiments, I want a configuration option to
use mean-based acceptance, so that I can preserve current behavior and avoid
invalidating historical baselines.

**Why this priority**: A controlled rollout reduces risk and enables A/B
comparison between legacy and upstream-aligned behavior.

**Independent Test**: Can be tested by running the same deterministic evolution
step twice with different acceptance scoring modes and verifying acceptance
decisions change as expected.

**Acceptance Scenarios**:

1. **Given** the acceptance scoring mode is configured as `"mean"`, **When**
   evolution compares a proposal to the current best on the iteration evaluation
   batch, **Then** acceptance uses mean scoring (legacy semantics) instead of
   sum scoring.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases
- What happens when the iteration evaluation batch is empty? System should fail
  fast with a clear configuration or validation error.
- How does the system handle non-finite scores (NaN/inf) returned by evaluation?
  System should treat the evaluation as invalid for acceptance and surface a
  clear error.
- What happens when batch size varies across iterations while using sum-based
  acceptance? System should document the behavior and provide a way to keep the
  batch size consistent for fair comparisons.
- What happens when no valset is provided? System should still perform acceptance
  decisions on the iteration evaluation batch and report valset metrics as
  absent/not computed.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST compute an acceptance score for the iteration
  evaluation batch using a configurable acceptance scoring mode.
- **FR-002**: When the acceptance scoring mode is `"sum"`, the system MUST use
  the sum of per-example scores from the iteration evaluation batch for
  accept/reject decisions.
- **FR-003**: When the acceptance scoring mode is `"mean"`, the system MUST use
  the mean of per-example scores from the iteration evaluation batch for
  accept/reject decisions.
- **FR-004**: System MUST track and report a valset score as the mean of
  per-example scores whenever a valset evaluation is performed.
- **FR-005**: System MUST preserve existing behavior when the acceptance scoring
  mode is explicitly configured as `"mean"`.
- **FR-006**: System MUST apply the same acceptance metric consistently within a
  single evolution run.
- **FR-007**: System MUST fail fast when the iteration evaluation batch is empty
  (no per-example scores available to compute acceptance).
- **FR-008**: System MUST surface a clear error when evaluation returns non-finite
  scores (NaN/inf) that would invalidate acceptance or reporting.
- **FR-009**: System MUST make it possible for users to configure the acceptance
  scoring mode via the public evolution entrypoint(s).

### Key Entities *(include if feature involves data)*

- **Acceptance Scoring Mode**: A configuration value that determines how
  per-example scores from the iteration evaluation batch are aggregated for
  acceptance decisions (sum or mean).
- **Iteration Evaluation Batch**: The set of examples whose per-example scores
  are used to determine whether a proposal is accepted in an iteration.
- **Validation Set (Valset)**: An optional, separate set of examples used for
  tracking generalization performance and reporting a mean score.
- **Candidate Score Summary**: The aggregated acceptance score (sum or mean) for
  an iteration, plus the tracked mean valset score when available.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: In sum acceptance mode, acceptance decisions on a 3-example batch
  use the total score (sum) and accept a proposal with total 0.9 when the
  current best total is 0.8.
- **SC-002**: When evaluating on a 10-example valset, the tracked valset score is
  the arithmetic mean of the 10 per-example scores.
- **SC-003**: In mean acceptance mode, acceptance decisions on an iteration batch
  match the legacy behavior (mean-based comparison) for the same per-example
  scores.
- **SC-004**: When evaluation returns any non-finite score (NaN/inf), the system
  produces a clear, actionable error without recording an invalid acceptance
  outcome.

## Assumptions

- Per-example scores are available from evaluation for both iteration-level
  acceptance decisions and optional valset tracking.
- Upstream GEPA semantics treat iteration-level acceptance as a minibatch
  comparison using sum aggregation, while valset tracking uses mean aggregation.
- Users who want fair sum-based comparisons keep the iteration evaluation batch
  size consistent across iterations.

## Dependencies

- Depends on the ability to configure evolution runs with an acceptance scoring
  mode (sum or mean).
- Depends on existing evaluation mechanisms returning a list of numeric scores
  for the iteration evaluation batch (and valset, when used).

## Out of Scope

- Changing how per-example scores are produced (scorer semantics and score range
  meaning remain unchanged).
- Introducing new sampling strategies for minibatches (handled by separate
  batching/sampler features).
