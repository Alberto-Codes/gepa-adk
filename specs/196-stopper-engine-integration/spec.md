# Feature Specification: Wire stop_callbacks into AsyncGEPAEngine

**Feature Branch**: `196-stopper-engine-integration`
**Created**: 2026-01-22
**Status**: Draft
**Input**: User description: "GitHub Issue #196 - Wire stop_callbacks into AsyncGEPAEngine"
**Parent Issue**: #51 - Pluggable stop conditions

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Custom Stopper Invocation (Priority: P1)

As a gepa-adk user, I want my custom stoppers configured in `stop_callbacks` to be checked during evolution, so that I can control when evolution terminates based on my own criteria.

**Why this priority**: This is the core value proposition - without stopper invocation, the entire stop_callbacks system is non-functional. Users cannot use any custom or built-in stoppers.

**Independent Test**: Can be tested by providing a mock stopper that tracks invocation count and verifying it receives valid state each iteration.

**Acceptance Scenarios**:

1. **Given** an EvolutionConfig with stop_callbacks containing a mock stopper, **When** evolution runs for N iterations, **Then** the mock stopper's __call__ method is invoked at least N times with valid StopperState objects.
2. **Given** an EvolutionConfig with stop_callbacks containing a stopper that always returns True, **When** evolution starts, **Then** evolution terminates after the first iteration.
3. **Given** an EvolutionConfig with an empty stop_callbacks list, **When** evolution runs, **Then** evolution proceeds normally using only built-in termination checks (max_iterations, patience).

---

### User Story 2 - Accurate State Tracking (Priority: P1)

As a gepa-adk user, I want stoppers to receive accurate elapsed time and evaluation counts, so that time-based and evaluation-based stoppers function correctly.

**Why this priority**: Time-based stoppers (TimeoutStopper) and evaluation-count-based stoppers depend on accurate state tracking. Without this, critical stoppers will malfunction.

**Independent Test**: Can be tested by verifying elapsed_seconds increases monotonically and total_evaluations accumulates correctly across iterations.

**Acceptance Scenarios**:

1. **Given** a TimeoutStopper configured with 0.5 seconds, **When** evolution runs for at least 0.6 seconds, **Then** the stopper triggers and elapsed_seconds in StopperState is >= 0.5.
2. **Given** evolution runs for 3 iterations with 5 evaluations each, **When** StopperState is built, **Then** total_evaluations is >= 15.
3. **Given** evolution just started, **When** StopperState is built, **Then** elapsed_seconds is a small positive number (> 0) and total_evaluations reflects actual evaluations performed.

---

### User Story 3 - SignalStopper Lifecycle Management (Priority: P2)

As a gepa-adk user, I want SignalStopper to be properly set up and cleaned up by the engine, so that Ctrl+C handling works correctly during evolution and is restored after evolution completes.

**Why this priority**: Signal handling is important for user experience but not critical to core functionality. Users can still terminate via other means if signal handling fails.

**Independent Test**: Can be tested by verifying setup() is called before the evolution loop and cleanup() is called after (even on exceptions).

**Acceptance Scenarios**:

1. **Given** a SignalStopper in stop_callbacks, **When** evolution runs and completes normally, **Then** setup() is called before the evolution loop begins and cleanup() is called after the loop completes.
2. **Given** a SignalStopper in stop_callbacks, **When** evolution encounters an exception, **Then** cleanup() is still called to restore original signal handlers.
3. **Given** multiple stoppers including SignalStopper, **When** evolution runs, **Then** only stoppers with setup/cleanup methods have those methods called.

---

### User Story 4 - Multiple Stopper Coordination (Priority: P2)

As a gepa-adk user, I want multiple stoppers to work together, with the first stopper to fire winning, so that I can combine conditions like "stop after 5 minutes OR when score reaches 0.99".

**Why this priority**: CompositeStopper and multi-stopper use cases are common patterns but represent advanced usage beyond single-stopper scenarios.

**Independent Test**: Can be tested by configuring multiple stoppers with different trigger conditions and verifying the first to match causes termination.

**Acceptance Scenarios**:

1. **Given** stop_callbacks contains [TimeoutStopper(1 second), ScoreThresholdStopper(0.99)], **When** timeout fires before score threshold is reached, **Then** evolution stops and logs indicate TimeoutStopper triggered.
2. **Given** stop_callbacks contains multiple stoppers, **When** one stopper returns True, **Then** remaining stoppers are not checked for that iteration.
3. **Given** stop_callbacks contains multiple stoppers that all return False, **When** iteration completes, **Then** all stoppers were checked and evolution continues.

---

### Edge Cases

- What happens when a stopper raises an exception? The evolution should handle it gracefully (log the error and continue or terminate safely).
- What happens when stop_callbacks is None vs empty list? Both should result in no custom stopper checks.
- What happens if setup() is called on a stopper that doesn't have setup()? Only call setup() on stoppers that have the method.
- What happens if elapsed time tracking starts before the first iteration? Elapsed time should be tracked from the start of the run() method.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST invoke each stopper in stop_callbacks once per iteration, passing a valid StopperState snapshot.
- **FR-002**: System MUST terminate evolution when any stopper returns True.
- **FR-003**: System MUST track elapsed time from the start of run() using monotonic time.
- **FR-004**: System MUST track total evaluations as a cumulative count across all iterations.
- **FR-005**: System MUST build StopperState with accurate iteration, best_score, stagnation_counter, total_evaluations, candidates_count, and elapsed_seconds.
- **FR-006**: System MUST call setup() on stoppers that have this method before the evolution loop begins.
- **FR-007**: System MUST call cleanup() on stoppers that have this method after the evolution loop, including when exceptions occur.
- **FR-008**: System MUST log which stopper triggered termination, including the stopper class name and current iteration.
- **FR-009**: System MUST check built-in termination conditions (max_iterations, patience) before checking custom stoppers.
- **FR-010**: System MUST handle stop_callbacks being None or empty without error.

### Key Entities

- **StopperState**: Immutable snapshot of evolution state passed to stoppers. Contains iteration, best_score, stagnation_counter, total_evaluations, candidates_count, and elapsed_seconds.
- **Stopper Protocol**: Callable objects that receive StopperState and return bool. May optionally have setup() and cleanup() methods for lifecycle management.
- **AsyncGEPAEngine**: The evolution engine that orchestrates the evolution loop and must integrate stopper checking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All configured stoppers are invoked every iteration, verified by mock stopper invocation counts matching iteration counts.
- **SC-002**: Evolution terminates immediately when any stopper returns True, verified by iteration count stopping at the expected point.
- **SC-003**: elapsed_seconds accuracy is within 50ms of actual elapsed time.
- **SC-004**: total_evaluations matches the sum of all evaluation batch sizes across all iterations.
- **SC-005**: SignalStopper cleanup is always called, even when exceptions occur during evolution, verified by cleanup call count matching setup call count.
- **SC-006**: Stopper triggering is logged with stopper class name and iteration number.

## Assumptions

- StopperState and the Stopper protocol are already defined in the codebase (from previous stopper implementation issues).
- Individual stopper implementations (TimeoutStopper, ScoreThresholdStopper, SignalStopper, CompositeStopper) are already complete.
- The existing _should_stop() method can be extended without breaking current behavior.
- Stoppers are expected to be fast (sub-millisecond) and non-blocking.
