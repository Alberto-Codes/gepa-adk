# Feature Specification: Concurrent Batch Evaluation

**Feature Branch**: `012-concurrent-batch`
**Created**: 2026-01-11
**Status**: Draft
**Input**: User description: "Add semaphore-controlled concurrent batch evaluation for parallel evaluation runs"
**Related Issue**: [GitHub Issue #12](https://github.com/Alberto-Codes/gepa-adk/issues/12)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parallel Batch Evaluation (Priority: P1)

As a gepa-adk user running evolution experiments, I want my batch evaluations to execute in parallel so that my evolution runs complete 3-5x faster than sequential execution.

**Why this priority**: This is the core value proposition of the feature. Without parallel execution, users experience significant wait times during evolution runs, limiting experimentation velocity and productivity.

**Independent Test**: Can be fully tested by running a batch of evaluations with concurrency enabled and measuring total execution time versus sequential baseline. Delivers immediate performance improvement.

**Acceptance Scenarios**:

1. **Given** a batch of 10 examples each taking 30 seconds to evaluate, **When** I run evaluation with concurrency limit of 5, **Then** total evaluation time is approximately 60 seconds (not 300 seconds).

2. **Given** a batch of 20 examples, **When** I run evaluation with concurrency limit of 10, **Then** all examples complete and I receive results for all 20 evaluations.

3. **Given** a batch of examples, **When** I run evaluation with default settings, **Then** the system uses parallel execution transparently without requiring manual configuration.

---

### User Story 2 - Concurrency Limit Control (Priority: P2)

As a gepa-adk user with resource constraints, I want to configure the maximum number of concurrent evaluations so that I can balance performance with system resource utilization and API rate limits.

**Why this priority**: Enables users to adapt the feature to their specific environment and constraints. Essential for production use but not required for basic functionality.

**Independent Test**: Can be tested by setting different concurrency limits and observing that at most N evaluations run simultaneously. Delivers control over resource consumption.

**Acceptance Scenarios**:

1. **Given** max_concurrent_evals is set to 5 and batch_size is 10, **When** I call evaluate, **Then** at most 5 evaluations run simultaneously at any point in time.

2. **Given** max_concurrent_evals is set to 1, **When** I call evaluate with a batch, **Then** evaluations run sequentially one at a time.

3. **Given** max_concurrent_evals is set to a value larger than batch size, **When** I call evaluate, **Then** all batch items run concurrently without error.

---

### User Story 3 - Graceful Error Handling (Priority: P3)

As a gepa-adk user, I want individual evaluation failures to not block or affect other evaluations in the batch so that I get results for all successful evaluations even when some fail.

**Why this priority**: Resilience is important for production use but basic functionality works without it. Users can work around failures by re-running failed items.

**Independent Test**: Can be tested by intentionally causing one evaluation to fail and verifying others complete successfully. Delivers robustness for real-world usage.

**Acceptance Scenarios**:

1. **Given** one example in a batch fails during evaluation, **When** other examples are running, **Then** they complete independently and return their results.

2. **Given** an evaluation fails with an error, **When** the batch completes, **Then** the failed evaluation result includes the error information and a score of 0.0.

3. **Given** multiple evaluations fail in a batch, **When** the batch completes, **Then** I receive a complete result set with successful results and error information for failed items.

---

### Edge Cases

- What happens when all evaluations in a batch fail? System returns a complete result set with all items marked as failed with error details.
- What happens when concurrency limit is set to 0 or negative? System treats this as invalid configuration and uses a sensible default (e.g., 1).
- What happens when the batch is empty? System returns an empty result set without error.
- What happens when an evaluation times out? System treats timeout as a failure and records it appropriately.
- What happens if the system runs out of memory during parallel execution? Individual evaluations fail gracefully and are recorded as errors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST execute batch evaluations in parallel up to the configured concurrency limit.
- **FR-002**: System MUST respect the maximum concurrent evaluations setting at all times during batch processing.
- **FR-003**: System MUST allow users to configure the maximum number of concurrent evaluations.
- **FR-004**: System MUST provide a sensible default concurrency limit when not explicitly configured.
- **FR-005**: System MUST continue processing remaining evaluations when one evaluation fails.
- **FR-006**: System MUST capture and report error information for failed evaluations.
- **FR-007**: System MUST assign a score of 0.0 to failed evaluations.
- **FR-008**: System MUST return complete result sets containing all evaluation outcomes (success and failure).
- **FR-009**: System MUST preserve the order of results to match the order of input examples.
- **FR-010**: System MUST support optional trajectory capture during parallel evaluation.

### Key Entities

- **EvaluationBatch**: The result of evaluating a batch of examples, containing outputs, scores, and trajectories for each example.
- **DataInst**: An individual example to be evaluated, containing input data and optionally expected output.
- **Candidate**: The configuration/prompt template being evaluated against the batch.
- **ConcurrencyConfig**: Configuration controlling maximum parallel evaluations, part of the adapter configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Batch evaluation of N examples with concurrency C completes in approximately (N/C) * single_evaluation_time, demonstrating linear speedup.
- **SC-002**: Evolution runs complete 3-5x faster compared to sequential evaluation baseline.
- **SC-003**: System processes batches of 100+ examples without memory exhaustion or resource starvation.
- **SC-004**: 100% of successful evaluations return correct results regardless of concurrent failures.
- **SC-005**: Users can configure concurrency from 1 to at least 20 concurrent evaluations.
- **SC-006**: Failed evaluations are clearly identifiable in the result set with actionable error information.

## Assumptions

- The underlying evaluation mechanism (agent execution, scoring) is thread-safe and can be called concurrently.
- External API rate limits are managed separately or are factored into the concurrency limit configuration.
- Memory consumption per evaluation is bounded and predictable, allowing safe concurrent execution.
- Default concurrency limit of 5 is appropriate for most use cases (balances performance with resource consumption).
- Trajectory capture works correctly in concurrent execution contexts.

## Dependencies

- Depends on Issue #8 (async evaluation infrastructure) being completed first.
- Requires the ADK adapter to support async evaluation methods.
