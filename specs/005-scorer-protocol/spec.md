# Feature Specification: Scorer Protocol

**Feature Branch**: `005-scorer-protocol`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "Define Scorer protocol for scoring agent outputs with sync and async methods"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Score Agent Output with Custom Logic (Priority: P1)

A developer wants to evaluate how well an agent's output matches expected results using their own scoring logic. They implement the Scorer protocol with a custom algorithm (e.g., semantic similarity, keyword matching, or LLM-based grading) and integrate it into the evolution engine.

**Why this priority**: This is the core use case for the Scorer protocol. Without the ability to implement custom scoring logic, the evolution engine cannot evaluate agent outputs, which blocks all evolution functionality.

**Independent Test**: Can be fully tested by implementing a simple scorer that returns a fixed score and verifying the evolution engine accepts and uses it correctly.

**Acceptance Scenarios**:

1. **Given** a developer implements the Scorer protocol with a `score()` method, **When** the evolution engine calls `score(input_text, output, expected)`, **Then** the scorer returns a tuple of (float, dict) where the float is between 0.0 and 1.0.

2. **Given** a scorer implementation returns a score outside the conventional 0.0-1.0 range, **When** the evolution engine receives this score, **Then** the engine may log a warning but continues processing (validation is caller responsibility per FR-008).

3. **Given** a developer wants to include diagnostic information with a score, **When** they return metadata in the dict, **Then** this metadata is preserved and accessible for debugging or analysis.

---

### User Story 2 - Async Scoring for I/O-Bound Operations (Priority: P2)

A developer needs to score outputs using an external LLM or API call that is inherently asynchronous. They use the `async_score()` method to perform scoring without blocking the event loop, enabling concurrent evaluation of multiple outputs.

**Why this priority**: Many real-world scoring scenarios involve LLM calls or external APIs. Async support enables efficient concurrent evaluation, which is critical for performance but not required for basic functionality.

**Independent Test**: Can be fully tested by implementing an async scorer that simulates an API call with a small delay and verifying it executes concurrently with other tasks.

**Acceptance Scenarios**:

1. **Given** a developer implements `async_score()`, **When** the evolution engine needs to score an output asynchronously, **Then** the method is awaited and returns the same tuple format as `score()`.

2. **Given** multiple outputs need scoring, **When** the evolution engine calls `async_score()` for each, **Then** scoring operations can execute concurrently using standard async patterns.

---

### User Story 3 - Scoring Without Expected Output (Priority: P3)

A developer wants to score agent outputs in scenarios where there is no predefined "expected" answer (e.g., open-ended generation, creativity tasks). They pass `None` for the expected parameter and their scorer evaluates based on other criteria.

**Why this priority**: Not all tasks have expected outputs. Supporting optional expected values enables the Scorer protocol to handle open-ended evaluation scenarios.

**Independent Test**: Can be fully tested by calling `score()` with `expected=None` and verifying the scorer handles this gracefully.

**Acceptance Scenarios**:

1. **Given** a scorer implementation handles optional expected values, **When** `score()` is called with `expected=None`, **Then** the scorer returns a valid score based on its internal criteria.

---

### Edge Cases

- What happens when the scorer returns a score exactly at the boundary (0.0 or 1.0)?
- How does the system handle a scorer that raises an exception during evaluation?
- What happens when the metadata dict contains non-serializable objects?
- How does the system behave when `async_score()` is not implemented but is called?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define a `Scorer` protocol with a `score()` method that accepts input text, output text, and optional expected text.
- **FR-002**: System MUST define a `Scorer` protocol with an `async_score()` method with the same signature as `score()` but returning an awaitable.
- **FR-003**: The `score()` method MUST return a tuple of (float, dict) where the float represents the score.
- **FR-004**: The `async_score()` method MUST return the same tuple type as `score()`.
- **FR-005**: The expected parameter MUST be optional (defaulting to None) to support open-ended scoring scenarios.
- **FR-006**: The protocol MUST be runtime-checkable to support isinstance() verification.
- **FR-007**: The metadata dict MUST allow arbitrary key-value pairs for extensibility.
- **FR-008**: Score values SHOULD be normalized between 0.0 and 1.0 (convention, not enforced by protocol).

### Key Entities

- **Scorer**: Protocol defining the contract for scoring implementations. Provides both synchronous and asynchronous methods for evaluating agent outputs.
- **Score Result**: A tuple containing a normalized score (float) and metadata (dict) with optional diagnostic or analytical information.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can implement custom scorers by following the protocol, verified by creating at least one working implementation in tests.
- **SC-002**: The evolution engine can use any Scorer implementation interchangeably, verified by swapping scorers without code changes.
- **SC-003**: Async scoring enables concurrent evaluation without blocking, verified by running multiple async_score calls in parallel.
- **SC-004**: Protocol implementations are verifiable at runtime using isinstance() checks.

## Assumptions

- Scorers are stateless or manage their own state; the protocol does not prescribe state management.
- The 0.0-1.0 score range is a convention; implementations may use different ranges if documented.
- Both sync and async methods should be implemented for full protocol compliance, though practical usage may only require one.
- The evolution engine will handle any exceptions raised by scorer implementations appropriately.
- The metadata dict accepts arbitrary Python objects; JSON serializability is recommended but not enforced by the protocol.
