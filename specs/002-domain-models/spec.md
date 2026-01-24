# Feature Specification: Domain Models for Evolution Engine

**Feature Branch**: `002-domain-models`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: GitHub Issue #2 - "Implement domain models (EvolutionConfig, EvolutionResult, Candidate)"  
**Related ADRs**: [ADR-000 Hexagonal Architecture](../../docs/adr/ADR-000-hexagonal-architecture.md), [ADR-009 Exception Hierarchy](../../docs/adr/ADR-009-exception-hierarchy.md)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Evolution Parameters (Priority: P1)

As a developer using gepa-adk, I want to configure evolution parameters with sensible defaults so that I can start evolving agents without manually specifying every setting.

**Why this priority**: Configuration is the entry point for all evolution operations. Without configurable parameters with defaults, developers cannot use the evolution engine at all.

**Independent Test**: Can be fully tested by creating an EvolutionConfig instance and verifying default values without any external dependencies.

**Acceptance Scenarios**:

1. **Given** I create an EvolutionConfig with no arguments, **When** I inspect the config, **Then** `max_iterations` defaults to 50
2. **Given** I create an EvolutionConfig with no arguments, **When** I inspect the config, **Then** `max_concurrent_evals` defaults to 5
3. **Given** I create an EvolutionConfig with custom values, **When** I inspect the config, **Then** my custom values are preserved
4. **Given** I create an EvolutionConfig, **When** I access `min_improvement_threshold`, **Then** it defaults to 0.01
5. **Given** I create an EvolutionConfig, **When** I access `patience`, **Then** it defaults to 5
6. **Given** I create an EvolutionConfig, **When** I access `reflection_model`, **Then** it defaults to "gemini-2.5-flash"
7. **Given** I create an EvolutionConfig with `max_iterations=-1`, **When** instantiation occurs, **Then** a `ConfigurationError` is raised with `field="max_iterations"`
8. **Given** I create an EvolutionConfig with `max_concurrent_evals=0`, **When** instantiation occurs, **Then** a `ConfigurationError` is raised with `field="max_concurrent_evals"`

---

### User Story 2 - Track Evolution Results (Priority: P1)

As a developer, I want to receive comprehensive evolution results so that I can understand how much the agent improved and review the evolution history.

**Why this priority**: Results capture the output of the entire evolution process. Without proper result tracking, developers cannot assess whether evolution succeeded or understand improvement trajectory.

**Independent Test**: Can be fully tested by creating an EvolutionResult with sample data and verifying all metrics are accessible.

**Acceptance Scenarios**:

1. **Given** an evolution run completes, **When** I receive the EvolutionResult, **Then** it contains `original_score` (the starting performance)
2. **Given** an evolution run completes, **When** I receive the EvolutionResult, **Then** it contains `final_score` (the ending performance)
3. **Given** an evolution run completes, **When** I receive the EvolutionResult, **Then** it contains `evolved_instruction` (the optimized prompt)
4. **Given** an evolution run completes, **When** I receive the EvolutionResult, **Then** it contains `iteration_history` (list of iteration records)
5. **Given** an evolution run completes, **When** I receive the EvolutionResult, **Then** it contains `total_iterations` (count of iterations performed)
6. **Given** an EvolutionResult, **When** I calculate improvement, **Then** I can compute `final_score - original_score`

---

### User Story 3 - Manage Candidate Instructions (Priority: P1)

As a developer, I want to represent instruction candidates with component-based access so that the evolution engine can manipulate and propose changes to specific parts of an agent's configuration.

**Why this priority**: Candidates are the unit of evolution—they represent what gets mutated and evaluated. The engine cannot function without a way to represent and manipulate instruction state.

**Independent Test**: Can be fully tested by creating a Candidate with instruction text and verifying component get/set operations.

**Acceptance Scenarios**:

1. **Given** I create a Candidate with instruction text, **When** I access `components["instruction"]`, **Then** I get the instruction text
2. **Given** I have a Candidate, **When** I set `components["instruction"]` to a new value, **Then** the instruction is updated
3. **Given** I create a Candidate, **When** I add an "output_schema" component, **Then** I can retrieve it via `components["output_schema"]`
4. **Given** I have a Candidate with multiple components, **When** I list component keys, **Then** all component names are returned
5. **Given** I create a Candidate, **When** I inspect `generation`, **Then** it defaults to 0 (initial generation)
6. **Given** I create a Candidate with a parent reference, **When** I inspect `parent_id`, **Then** it contains the parent's identifier

---

### User Story 4 - Record Iteration History (Priority: P2)

As a developer, I want each evolution iteration to be recorded so that I can analyze the progression of scores and proposals over time.

**Why this priority**: While the engine can function without detailed history, iteration records are essential for debugging, analysis, and understanding why evolution succeeded or failed.

**Independent Test**: Can be fully tested by creating IterationRecord instances and verifying all fields are captured correctly.

**Acceptance Scenarios**:

1. **Given** an iteration completes, **When** I examine the IterationRecord, **Then** it contains the iteration number
2. **Given** an iteration completes, **When** I examine the IterationRecord, **Then** it contains the score achieved
3. **Given** an iteration completes, **When** I examine the IterationRecord, **Then** it contains the candidate instruction used
4. **Given** an iteration completes with a proposal, **When** I examine the IterationRecord, **Then** it indicates whether the proposal was accepted

---

### Edge Cases

- What happens when EvolutionConfig is created with negative `max_iterations`? → Should raise ConfigurationError
- What happens when EvolutionConfig is created with `max_concurrent_evals` of 0? → Should raise ConfigurationError (must be >= 1)
- What happens when EvolutionConfig `reflection_model` is empty string? → Should raise ConfigurationError
- What happens when EvolutionConfig `patience` exceeds `max_iterations`? → Should be allowed (patience may not trigger)
- What happens when Candidate components dict is empty? → Should be allowed (valid initial state)
- What happens when EvolutionResult has `final_score` less than `original_score`? → Should be allowed (evolution may not always improve)
- What happens when iteration_history is empty in EvolutionResult? → Should be allowed (represents early termination)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an `EvolutionConfig` model with configurable evolution parameters
- **FR-002**: System MUST provide sensible defaults for all EvolutionConfig parameters (max_iterations=50, max_concurrent_evals=5, min_improvement_threshold=0.01, patience=5, reflection_model="gemini-2.5-flash")
- **FR-003**: System MUST provide an `EvolutionResult` model capturing evolution metrics (original_score, final_score, evolved_instruction, iteration_history, total_iterations)
- **FR-004**: System MUST provide a `Candidate` model representing instruction state with component-based access
- **FR-005**: System MUST provide an `IterationRecord` model capturing per-iteration metrics
- **FR-006**: All domain models MUST be immutable where appropriate (use frozen dataclasses for result types)
- **FR-007**: All domain models MUST reside in the `domain/` layer with NO external library imports (per ADR-000)
- **FR-008**: System MUST validate config parameters: non-negative for `max_iterations`, `patience`, `min_improvement_threshold`; positive (>= 1) for `max_concurrent_evals`; non-empty for `reflection_model`
- **FR-009**: System MUST provide type aliases and supporting types in a separate `types.py` module

### Key Entities

- **EvolutionConfig**: Represents the configuration for an evolution run. Key attributes: max_iterations, max_concurrent_evals, min_improvement_threshold, patience, reflection_model
- **EvolutionResult**: Represents the outcome of a completed evolution run. Key attributes: original_score, final_score, evolved_instruction, iteration_history, total_iterations
- **Candidate**: Represents an instruction candidate being evolved. Key attributes: components (dict mapping component names to text values), generation (evolution lineage number), parent_id (optional parent reference), metadata (extensible async tracking)
- **IterationRecord**: Represents a single iteration's metrics. Key attributes: iteration_number, score, instruction, accepted

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can create an EvolutionConfig with zero arguments and receive valid defaults within milliseconds
- **SC-002**: All domain models pass type checking with 100% coverage (no `Any` types in public interfaces)
- **SC-003**: Unit tests achieve 100% code coverage for all domain models
- **SC-004**: Domain models have zero external dependencies (only stdlib imports)
- **SC-005**: Developers can access any EvolutionResult metric in a single attribute access
- **SC-006**: All acceptance scenarios from user stories pass as automated tests

## Assumptions

- Scores are represented as floats in the range [0.0, 1.0] (normalized scores)
- Component names in Candidate are strings (e.g., "instruction", "output_schema")
- The reflection_model string follows model naming conventions used by Google ADK/LiteLLM
- EvolutionResult is created by the engine after evolution completes (not by users directly)
- Iteration numbers are 1-indexed for human readability

## Out of Scope

- Persistence/serialization of domain models (future feature)
- Validation of reflection_model against available models (adapter responsibility)
- Multi-objective evolution (single score optimization only in v1)
