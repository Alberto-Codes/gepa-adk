# Feature Specification: AsyncGEPAAdapter Protocol

**Feature Branch**: `004-async-gepa-adapter`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "Define AsyncGEPAAdapter protocol - async-first protocol for GEPA adapters with evaluate, make_reflective_dataset, and propose_new_texts methods"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Adapter Protocol (Priority: P1)

As a gepa-adk developer, I want a clear async protocol definition for GEPA adapters, so that I can implement ADK-specific adapters that integrate seamlessly with the async evolution engine.

**Why this priority**: This is the foundational contract that all adapter implementations must follow. Without this protocol, no adapters can be built, and the entire GEPA-ADK integration is blocked.

**Independent Test**: Can be fully tested by creating a mock implementation that satisfies the protocol and verifying it passes runtime type checking.

**Acceptance Scenarios**:

1. **Given** the AsyncGEPAAdapter protocol is defined, **When** I check its interface, **Then** it exposes an `evaluate()` method that accepts a batch of data instances and candidate parameters
2. **Given** the AsyncGEPAAdapter protocol is defined, **When** I check its interface, **Then** it exposes a `make_reflective_dataset()` method that creates reflection data from evaluation results
3. **Given** the AsyncGEPAAdapter protocol is defined, **When** I check its interface, **Then** it exposes a `propose_new_texts()` method that generates improved candidate parameters

---

### User Story 2 - Runtime Type Checking (Priority: P1)

As a gepa-adk developer, I want the protocol to be runtime-checkable, so that I can verify at runtime whether an object correctly implements the adapter interface.

**Why this priority**: Runtime checking enables defensive programming and clear error messages when implementations are incomplete, critical for developer experience.

**Independent Test**: Can be fully tested by implementing a class that satisfies the protocol and using `isinstance()` to verify it is recognized as an AsyncGEPAAdapter.

**Acceptance Scenarios**:

1. **Given** a class that implements all required async methods, **When** I check `isinstance(adapter, AsyncGEPAAdapter)`, **Then** it returns True
2. **Given** a class that is missing one or more required methods, **When** I check `isinstance(adapter, AsyncGEPAAdapter)`, **Then** it returns False
3. **Given** a class with methods that have incorrect signatures, **When** I attempt to use it as an AsyncGEPAAdapter, **Then** type checkers flag the incompatibility

---

### User Story 3 - Generic Type Parameters (Priority: P2)

As a gepa-adk developer, I want the protocol to support generic type parameters, so that different adapter implementations can work with their own domain-specific data types.

**Why this priority**: Generic support allows the protocol to be reused across different domains (ADK agents, custom models, etc.) without sacrificing type safety.

**Independent Test**: Can be tested by creating two different adapter implementations with different generic type arguments and verifying both satisfy the protocol.

**Acceptance Scenarios**:

1. **Given** the AsyncGEPAAdapter protocol with generic parameters, **When** I implement an adapter with specific types, **Then** type checkers enforce those types throughout the implementation
2. **Given** different adapter implementations with different generic types, **When** each is used with the evolution engine, **Then** type safety is maintained for their respective data types

---

### Edge Cases

- What happens when an adapter method is implemented synchronously instead of asynchronously?
- How does the system handle an adapter that implements extra methods beyond the protocol?
- What happens when an adapter returns incompatible types from its methods?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Protocol MUST define an `evaluate()` async method that accepts a batch of data instances, candidate parameters, and an optional flag for capturing traces
- **FR-002**: Protocol MUST define a `make_reflective_dataset()` async method that creates reflection data from evaluation results and specifies which components to update
- **FR-003**: Protocol MUST define a `propose_new_texts()` async method that generates new candidate parameters based on reflective dataset and components to update
- **FR-004**: Protocol MUST be decorated as runtime-checkable to support `isinstance()` verification
- **FR-005**: Protocol MUST support generic type parameters for data instances, trajectories, and rollout outputs
- **FR-006**: Protocol MUST use standard typing constructs that work with common type checkers (mypy, pyright)
- **FR-007**: All protocol methods MUST be async (coroutine functions)

### Key Entities

- **AsyncGEPAAdapter**: The protocol interface that defines the contract for all GEPA adapter implementations. Parameterized by DataInst (input data type), Trajectory (execution trace type), and RolloutOutput (evaluation result type).
- **EvaluationBatch**: A container returned by `evaluate()` that holds trajectories, rollout outputs, and scores for a batch of evaluations. Contains the results needed for reflection.
- **Candidate**: The existing domain model from 002-domain-models (dataclass with `components: dict[str, str]`, `generation`, `parent_id`, `metadata`). Adapters work with `candidate.components` for GEPA compatibility.
- **EvolutionConfig**: The existing configuration model from 002-domain-models. Provides configuration parameters that may be consumed by adapters.
- **Reflective Dataset**: A mapping from component names to sequences of reflection examples. Used by the proposer to generate improved candidates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any class implementing all three async methods with correct signatures is recognized as an AsyncGEPAAdapter by `isinstance()` checks
- **SC-002**: Type checkers (mypy, pyright) report zero errors when correctly implementing the protocol
- **SC-003**: Protocol definition is importable and usable from `gepa_adk.ports.adapter`
- **SC-004**: Contract tests verify protocol compliance for at least one reference implementation

## Dependencies

- **Depends on**: `Candidate`, `EvolutionConfig` from 002-domain-models (implemented in PR #22)
- **Blocks**: Issue #6 (AsyncGEPAEngine), Issue #8 (ADKAdapter)

## Assumptions

- The project uses Python 3.10+ which supports full typing features including `ParamSpec`, `TypeVar`, and `Protocol`
- The `EvaluationBatch` type will be defined alongside the protocol (or imported from a shared types module)
- Adapter implementations are expected to handle their own error handling and retry logic internally
- The `capture_traces` flag in `evaluate()` controls whether detailed execution traces are recorded for debugging/analysis
- Design follows async-first approach per ADR-001 and protocol-based design per ADR-002
- The protocol adapts GEPA's `GEPAAdapter` concept to work with Google ADK patterns (streaming, agents)
