# Feature Specification: Evolved Components Dictionary

**Feature Branch**: `126-evolved-components`
**Created**: 2026-01-19
**Status**: Draft
**Input**: User description: "Add evolved_components dict to EvolutionResult for multi-component evolution (GitHub issue #131)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Access Evolved Output Schema (Priority: P1)

As a GEPA user who has evolved an output_schema component, I want to access the evolved schema text from the evolution result, so that I can use the optimized schema in my agent configuration.

**Why this priority**: This is the core functionality that enables multi-component evolution. Without the ability to access any evolved component, users cannot leverage output_schema evolution at all.

**Independent Test**: Can be fully tested by running evolution targeting "output_schema" and verifying the result contains the evolved schema text at the expected key.

**Acceptance Scenarios**:

1. **Given** I run evolution targeting "output_schema" component, **When** evolution completes successfully, **Then** `result.evolved_components["output_schema"]` contains the evolved schema text
2. **Given** I run evolution targeting "output_schema" component, **When** evolution completes successfully, **Then** `result.evolved_components["instruction"]` contains the original instruction (unchanged)

---

### User Story 2 - Default Instruction Evolution (Priority: P1)

As a GEPA user with a simple use case, I want the default evolution behavior to remain unchanged (instruction-only), so that existing code continues to work and I don't need extra configuration for basic usage.

**Why this priority**: Backward compatibility and simplicity are critical. Users with existing code should experience the same behavior with minimal migration effort.

**Independent Test**: Can be fully tested by running evolution with minimal config (just agent + trainset) and verifying instruction evolution works as expected.

**Acceptance Scenarios**:

1. **Given** I run evolution with minimal config (just agent + trainset), **When** evolution completes successfully, **Then** `result.evolved_components["instruction"]` contains the evolved instruction
2. **Given** I have existing code using evolution, **When** I migrate to the new API, **Then** I only need to change the field access pattern (not the configuration)

---

### User Story 3 - Round-Robin Component Evolution (Priority: P2)

As a developer implementing sophisticated evolution strategies, I want to track which components were evolved across iterations, so that I can build round-robin evolution between instruction and output_schema.

**Why this priority**: This enables advanced use cases but requires the P1 stories to be complete first. It extends the basic functionality.

**Independent Test**: Can be fully tested by configuring evolution to alternate between components and verifying each iteration tracks the evolved component.

**Acceptance Scenarios**:

1. **Given** I configure evolution to alternate between "instruction" and "output_schema", **When** evolution runs for multiple iterations, **Then** each iteration's evolved component is tracked in iteration_history
2. **Given** I configure evolution for multiple components, **When** evolution completes, **Then** `result.evolved_components` contains final values for all evolved components

---

### Edge Cases

- What happens when a component key doesn't exist in the result? The dictionary should only contain keys for components that were actually tracked; accessing a missing key raises a standard KeyError.
- How does the system handle evolution with an empty or invalid component name? The system should validate component names and reject invalid configurations before evolution starts.
- What happens if evolution fails mid-way? The result should still contain the best candidate's components up to that point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose all evolved components via an `evolved_components: dict[str, str]` field in `EvolutionResult`
- **FR-002**: System MUST populate `evolved_components` with keys for all tracked components (instruction, output_schema, etc.)
- **FR-003**: System MUST default to instruction-only evolution when no component selector is configured
- **FR-004**: System MUST track which component was evolved in each iteration within the iteration history
- **FR-005**: System MUST populate `evolved_components` from the best candidate's component values upon evolution completion
- **FR-006**: System MUST support accessing individual components via dictionary key access (e.g., `result.evolved_components["instruction"]`)
- **FR-007**: System MUST include all original component values in `evolved_components`, not just the ones that were modified during evolution

### Key Entities

- **EvolutionResult**: The dataclass returned after evolution completes; gains new `evolved_components` field replacing the previous single-value field
- **evolved_components**: Dictionary mapping component names (string keys like "instruction", "output_schema") to their final evolved text values
- **IterationRecord**: Existing entity tracking iteration details; enhanced to record which component was evolved per iteration

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can access any evolved component by name within 1 line of code (e.g., `result.evolved_components["output_schema"]`)
- **SC-002**: Default instruction-only evolution requires zero additional configuration compared to the current behavior
- **SC-003**: All existing evolution examples can be migrated to the new API with a single field access change per usage
- **SC-004**: Multi-component evolution strategies can access final values for all evolved components in a single result object
- **SC-005**: 100% of evolved component values are accessible from the result without additional API calls or lookups

## Assumptions

- The existing `evolved_component_text` field will be replaced entirely (no backward compatibility wrapper)
- Component names are strings that match the keys used in candidate components (e.g., "instruction", "output_schema")
- The dictionary will always contain at least the "instruction" key for default evolution scenarios
- Users are expected to update their field access from `result.evolved_component_text` to `result.evolved_components["instruction"]` during migration
