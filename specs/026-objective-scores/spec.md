# Feature Specification: Objective Scores Passthrough

**Feature Branch**: `026-objective-scores`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "Pass through objective_scores for multi-objective tracking"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Access Objective Scores in Results (Priority: P1)

As a gepa-adk user, I want objective scores from evaluations to be passed through and stored, so that multi-objective metrics can be tracked and analyzed after evolution completes.

**Why this priority**: This is the core value proposition - without storing objective scores, users cannot perform multi-objective analysis, which is the primary purpose of this feature.

**Independent Test**: Can be fully tested by running an evolution with an adapter that returns objective_scores and verifying they appear in the iteration history or result metadata. Delivers the ability to access per-candidate objective breakdown.

**Acceptance Scenarios**:

1. **Given** an adapter evaluation that returns objective_scores, **When** evolution runs, **Then** objective_scores are stored in engine state and are available in iteration history or result metadata
2. **Given** evolution has completed with objective scores collected, **When** user accesses results, **Then** objective scores are accessible per candidate for plotting or analysis

---

### User Story 2 - Backward Compatibility (Priority: P1)

As a gepa-adk user with existing adapters, I want evolution to continue working seamlessly even if my adapter does not return objective_scores, so that I don't need to modify existing integrations.

**Why this priority**: Equal priority with User Story 1 because breaking existing adapters would be unacceptable. Both core functionality and backward compatibility must be delivered together.

**Independent Test**: Can be fully tested by running an evolution with an adapter that returns evaluations without objective_scores and verifying evolution completes successfully without errors.

**Acceptance Scenarios**:

1. **Given** an adapter that does not return objective_scores, **When** evolution runs, **Then** evolution proceeds without error
2. **Given** an adapter that returns None or missing objective_scores field, **When** results are accessed, **Then** objective_scores fields are None or empty (not causing exceptions)

---

### Edge Cases

- What happens when objective_scores is partially populated (some candidates have scores, others don't)? System should handle gracefully, storing available scores and treating missing ones as None.
- What happens when objective_scores contains unexpected keys or empty dictionaries? System should pass through whatever structure the adapter provides without validation.
- How does system handle objective_scores when adapter returns them but downstream code doesn't request them? Scores should be stored regardless of whether they're accessed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept optional objective_scores from adapter evaluation results
- **FR-002**: System MUST store objective_scores in engine state when provided by adapter
- **FR-003**: System MUST include objective_scores in iteration history records
- **FR-004**: System MUST make objective_scores available in evolution result metadata
- **FR-005**: System MUST default objective_scores to None when adapter does not provide them
- **FR-006**: System MUST NOT fail or raise errors when objective_scores is absent, None, or empty
- **FR-007**: System MUST preserve the structure of objective_scores as provided by the adapter (passthrough without transformation)

### Key Entities

- **ObjectiveScores**: A mapping of metric names to numeric values representing individual objective measurements for a candidate (e.g., {"accuracy": 0.95, "latency": 0.8, "cost": 0.7})
- **EvaluationBatch**: Extended to include optional objective_scores field for each candidate evaluation
- **IterationRecord**: Extended to include optional objective_scores for historical tracking per iteration
- **EvolutionResult**: Extended to include optional objective_scores for final result access

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can retrieve objective scores for any candidate from completed evolution results
- **SC-002**: Existing adapters without objective_scores continue to work without code changes
- **SC-003**: All objective score data from adapters is preserved without loss through the entire evolution pipeline
- **SC-004**: Users can access objective scores for any historical iteration in the evolution run

## Assumptions

- Objective scores follow a dictionary/mapping structure with string keys and numeric values
- The system acts as a passthrough and does not validate or transform objective score values
- Upstream GEPA adapter protocol defines the objective_scores field structure
- Optional fields default to None rather than empty collections for consistency with existing patterns

## Dependencies

- Upstream GEPA adapter protocol (gepa/core/adapter.py) - defines objective_scores structure
- Existing EvaluationBatch, IterationRecord, and EvolutionResult data models
