# Feature Specification: AsyncGEPAEngine (Core Evolution Loop)

**Feature Branch**: `006-async-gepa-engine`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "Implement AsyncGEPAEngine core evolution loop - async evolution engine that runs evolution iterations until max_iterations or convergence, accepts improved candidates, and stops early on convergence"
**Parent Issue**: #1
**GitHub Issue**: #6

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Evolution Loop (Priority: P1)

As a gepa-adk user, I want to run an async evolution loop that iterates until max_iterations or convergence, so that I can evolve agent instructions efficiently without blocking my application.

**Why this priority**: This is the core value proposition - without a working evolution loop, the engine has no purpose. Everything else depends on this.

**Independent Test**: Can be fully tested by providing a mock adapter, running `await engine.run()`, and verifying the engine executes iterations and returns a result with the best candidate.

**Acceptance Scenarios**:

1. **Given** an AsyncGEPAEngine with a mock adapter and config (max_iterations=10), **When** I call `await engine.run()`, **Then** it completes up to 10 iterations and returns an EvolutionResult with the best candidate found.

2. **Given** an AsyncGEPAEngine with a valid configuration, **When** I call `await engine.run()`, **Then** each iteration evaluates candidates, proposes mutations, and tracks improvement history.

3. **Given** an AsyncGEPAEngine with config (max_iterations=0), **When** I call `await engine.run()`, **Then** it evaluates only the baseline candidate and returns an EvolutionResult with original_score equal to final_score.

---

### User Story 2 - Early Stopping on Convergence (Priority: P2)

As a gepa-adk user, I want the engine to stop early when no improvement is made for a configured number of iterations (patience), so that I don't waste compute resources when the candidate has converged.

**Why this priority**: Early stopping saves significant compute costs and time. Once core loop works, this optimization is the next most valuable capability.

**Independent Test**: Can be fully tested by configuring a mock adapter that returns stagnant scores, setting patience=3, and verifying the engine stops before max_iterations.

**Acceptance Scenarios**:

1. **Given** an AsyncGEPAEngine with config (patience=3, max_iterations=100), **When** 3 consecutive iterations show no improvement above min_improvement_threshold, **Then** the engine stops early and returns the best candidate.

2. **Given** an AsyncGEPAEngine with config (patience=0), **When** no improvement occurs, **Then** the engine runs until max_iterations (early stopping is disabled).

3. **Given** an AsyncGEPAEngine running with patience=3, **When** improvement occurs after 2 stagnant iterations, **Then** the patience counter resets and evolution continues.

---

### User Story 3 - Accept Improved Candidates (Priority: P3)

As a gepa-adk user, I want the engine to accept proposals only when they improve the score above a configurable threshold, so that I maintain quality standards during evolution.

**Why this priority**: Acceptance logic ensures quality control. It builds on the core loop and convergence detection to make meaningful selection decisions.

**Independent Test**: Can be fully tested by providing proposals with varying scores and verifying only those exceeding min_improvement_threshold are accepted as the new best.

**Acceptance Scenarios**:

1. **Given** a current best score of 0.80 and min_improvement_threshold=0.01, **When** a proposal scores 0.82, **Then** it is accepted as the new best candidate.

2. **Given** a current best score of 0.80 and min_improvement_threshold=0.01, **When** a proposal scores 0.805, **Then** it is NOT accepted (improvement 0.005 < threshold 0.01).

3. **Given** a current best score of 0.80 and min_improvement_threshold=0.0, **When** a proposal scores 0.801, **Then** it is accepted (any improvement counts).

---

### Edge Cases

- What happens when the adapter's evaluate method raises an exception mid-iteration?
  - The engine should propagate the exception to the caller (fail-fast behavior).
- What happens when all proposals in an iteration are rejected?
  - The engine continues with the current best candidate and increments the stagnation counter.
- What happens when the initial baseline evaluation returns a score of 0.0?
  - The engine proceeds normally; any positive score improvement is valid.
- What happens when max_iterations=0 and patience=0?
  - Only baseline evaluation runs; no iterations occur, no early stopping logic applies.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Engine MUST accept an adapter (implementing AsyncGEPAAdapter protocol), configuration (EvolutionConfig), and initial candidate components at construction.
- **FR-002**: Engine MUST evaluate the baseline candidate before starting evolution iterations.
- **FR-003**: Engine MUST execute an async evolution loop that runs until max_iterations is reached OR convergence is detected.
- **FR-004**: Engine MUST track the best candidate and its score across all iterations.
- **FR-005**: Engine MUST accept a new candidate as "best" only when its score exceeds (current_best_score + min_improvement_threshold).
- **FR-006**: Engine MUST detect convergence when no improvement occurs for `patience` consecutive iterations.
- **FR-007**: Engine MUST disable early stopping when patience=0.
- **FR-008**: Engine MUST return an EvolutionResult containing original_score, final_score, evolved_instruction, iteration_history, and total_iterations.
- **FR-009**: Engine MUST create an IterationRecord for each iteration capturing iteration_number, score, instruction, and whether it was accepted.
- **FR-010**: Engine MUST use the adapter's evaluate method to score candidates.
- **FR-011**: Engine MUST use the adapter's make_reflective_dataset and propose_new_texts methods to generate mutation proposals.
- **FR-012**: Engine MUST track candidate lineage using generation numbers and parent references.

### Key Entities

- **AsyncGEPAEngine**: The core evolution engine that orchestrates the loop. Holds adapter, config, and manages internal state during evolution.
- **EvolutionConfig**: Configuration parameters controlling iteration limits, concurrency, improvement thresholds, and patience (already exists in domain).
- **EvolutionResult**: Immutable outcome containing scores, evolved instruction, and iteration history (already exists in domain).
- **IterationRecord**: Immutable snapshot of each iteration's metrics (already exists in domain).
- **Candidate**: Mutable instruction candidate with components, generation, and parent tracking (already exists in domain).
- **AsyncGEPAAdapter**: Protocol for async evaluation and proposal generation (already exists in ports).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Engine completes evolution runs with 100% reliability when provided valid inputs (no unexpected crashes or hangs).
- **SC-002**: Engine respects max_iterations limit exactly - never exceeds configured maximum.
- **SC-003**: Engine stops within `patience + 1` iterations after the last improvement when early stopping is enabled.
- **SC-004**: All iteration records in the result match the actual iterations performed (complete history accuracy).
- **SC-005**: Engine correctly identifies improvement - accepts proposals only when score delta exceeds min_improvement_threshold.
- **SC-006**: Baseline-only mode (max_iterations=0) completes and returns valid EvolutionResult with matching original and final scores.

## Assumptions

- The AsyncGEPAAdapter protocol is correctly implemented by the caller; the engine does not validate adapter behavior.
- Score values returned by the adapter are normalized (typically in [0.0, 1.0] range but not enforced).
- The engine operates on a single "instruction" component for v1; multi-component evolution is a future enhancement.
- Error handling follows fail-fast: exceptions from the adapter propagate to the caller without retry logic in v1.
- The engine does not persist state between runs; each `run()` call starts fresh.
