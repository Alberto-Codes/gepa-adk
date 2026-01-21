# Feature Specification: Component Handler Migration

**Feature Branch**: `163-component-handler-migration`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "Migrate instruction and output_schema to ComponentHandler pattern (from GH issue #163)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instruction Serialization via Handler (Priority: P1)

As a GEPA maintainer, I want the instruction component to be serialized and applied through a dedicated handler, so that component handling follows a consistent pattern.

**Why this priority**: The instruction component is the simplest to migrate and establishes the pattern for all other components. It serves as the foundation for the handler-based architecture.

**Independent Test**: Can be fully tested by calling the InstructionHandler serialize/apply/restore methods on an agent and verifying the instruction is correctly managed.

**Acceptance Scenarios**:

1. **Given** an agent with instruction "You are helpful", **When** I call the instruction handler's serialize method, **Then** it returns "You are helpful" as a string.
2. **Given** an agent with instruction "Original", **When** I apply a new instruction "Modified" through the handler, **Then** the agent's instruction becomes "Modified" and the original value is returned for later restoration.
3. **Given** a modified agent and its original instruction value, **When** I call the handler's restore method, **Then** the agent's instruction returns to its original state.

---

### User Story 2 - Output Schema Serialization via Handler (Priority: P1)

As a GEPA maintainer, I want the output_schema component to be serialized and applied through a dedicated handler, so that Pydantic schema handling is encapsulated in a consistent interface.

**Why this priority**: The output_schema component is critical for structured agent responses and requires proper serialization/deserialization of Pydantic models.

**Independent Test**: Can be tested by calling the OutputSchemaHandler serialize/apply/restore methods on an agent with a Pydantic schema and verifying the schema is correctly serialized to text and restored from text.

**Acceptance Scenarios**:

1. **Given** an agent with a Pydantic output_schema class, **When** I call the output schema handler's serialize method, **Then** it returns the Pydantic class definition as text.
2. **Given** an agent with an original output_schema, **When** I apply a serialized schema string through the handler, **Then** the agent's output_schema is replaced with the deserialized schema and the original is returned.
3. **Given** a modified agent and its original output_schema, **When** I call the handler's restore method, **Then** the agent's output_schema returns to its original class.

---

### User Story 3 - Registry-Based Dispatch in Apply Candidate (Priority: P2)

As a GEPA maintainer, I want the _apply_candidate method to dispatch component applications through the handler registry, so that adding new component types doesn't require modifying conditional logic.

**Why this priority**: Depends on handlers being implemented first. This delivers the core architectural benefit of extensibility.

**Independent Test**: Can be tested by calling _apply_candidate with a multi-component candidate and verifying all components are applied via their registered handlers.

**Acceptance Scenarios**:

1. **Given** a candidate dictionary with "instruction" and "output_schema" components, **When** _apply_candidate is called, **Then** it dispatches to InstructionHandler.apply() for the instruction component.
2. **Given** a candidate dictionary with "instruction" and "output_schema" components, **When** _apply_candidate is called, **Then** it dispatches to OutputSchemaHandler.apply() for the output_schema component.
3. **Given** the refactored _apply_candidate method, **When** I inspect the code, **Then** no if/elif branches exist for component name checks.

---

### User Story 4 - Registry-Based Dispatch in Restore Agent (Priority: P2)

As a GEPA maintainer, I want the _restore_agent method to dispatch component restorations through the handler registry, so that restoration logic is consistent with application logic.

**Why this priority**: Restoration is the complement to application and must use the same handler pattern for consistency.

**Independent Test**: Can be tested by calling _restore_agent with original values and verifying all components are restored via their registered handlers.

**Acceptance Scenarios**:

1. **Given** original component values captured from _apply_candidate, **When** _restore_agent is called, **Then** it dispatches to each component's handler restore method.
2. **Given** the refactored _restore_agent method, **When** I inspect the code, **Then** no if/elif statements exist for component name dispatch.

---

### User Story 5 - Backward Compatibility (Priority: P1)

As a GEPA user, I want existing evolution workflows to behave identically after the refactor, so that my current usage is not disrupted.

**Why this priority**: Critical to ensure the refactor is a pure internal change with no behavioral differences.

**Independent Test**: Can be tested by running the existing test suite and verifying all tests pass without modification.

**Acceptance Scenarios**:

1. **Given** existing evolution code that evolves instructions, **When** the refactored adapter is used, **Then** behavior is identical to before the refactor.
2. **Given** existing evolution code that evolves output_schema, **When** the refactored adapter is used, **Then** behavior is identical to before the refactor.
3. **Given** the existing ADKAdapter test suite, **When** tests are run after the refactor, **Then** all tests pass without modification.

---

### Edge Cases

- What happens when a handler for an unknown component name is requested from the registry?
- How does the system handle agents that have None as their instruction or output_schema?
- What happens if serialization or deserialization fails for a component?
- How does the system handle partial application (some components succeed, others fail)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an InstructionHandler that serializes agent instructions to string format.
- **FR-002**: System MUST provide an InstructionHandler that applies string instructions to agents and returns the original value.
- **FR-003**: System MUST provide an InstructionHandler that restores agents to their original instruction state.
- **FR-004**: System MUST provide an OutputSchemaHandler that serializes Pydantic output schemas to text format.
- **FR-005**: System MUST provide an OutputSchemaHandler that applies serialized schema text to agents and returns the original schema.
- **FR-006**: System MUST provide an OutputSchemaHandler that restores agents to their original output_schema state.
- **FR-007**: System MUST register InstructionHandler for the "instruction" component name in the default handler registry.
- **FR-008**: System MUST register OutputSchemaHandler for the "output_schema" component name in the default handler registry.
- **FR-009**: ADKAdapter._apply_candidate MUST dispatch to registered handlers instead of using hardcoded if/elif logic.
- **FR-010**: ADKAdapter._restore_agent MUST dispatch to registered handlers instead of using hardcoded if/elif logic.
- **FR-011**: System MUST maintain backward-compatible behavior for all existing evolution workflows.
- **FR-012**: System MUST leverage existing serialize_pydantic_schema and deserialize_schema utilities for output schema handling.

### Key Entities

- **InstructionHandler**: Handles serialization, application, and restoration of agent instruction components. The instruction is a simple string passthrough.
- **OutputSchemaHandler**: Handles serialization, application, and restoration of agent output_schema components. Uses Pydantic schema serialization utilities.
- **Handler Registry**: A mapping of component names to their corresponding handler implementations. Enables dispatch without conditional logic.
- **Candidate**: A dictionary mapping component names to their serialized string values for evolution.
- **Originals**: A dictionary mapping component names to their pre-application values for restoration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All existing ADKAdapter unit tests pass without modification after the refactor.
- **SC-002**: All existing integration tests pass without modification after the refactor.
- **SC-003**: The _apply_candidate method contains zero if/elif statements for component name dispatch.
- **SC-004**: The _restore_agent method contains zero if/elif statements for component name dispatch.
- **SC-005**: InstructionHandler and OutputSchemaHandler are registered in the default handler registry and discoverable by component name.
- **SC-006**: New component types can be added by implementing a handler and registering it, without modifying _apply_candidate or _restore_agent.

## Assumptions

- The ComponentHandler protocol and registry infrastructure from issue #162 is completed and available.
- Existing serialize_pydantic_schema and deserialize_schema utilities are working correctly and can be reused.
- The LlmAgent class from google-adk has mutable instruction and output_schema attributes.
- Handler registration happens at module load time via the default registry.

## Dependencies

- **#162 - ComponentHandler protocol and registry**: Must be completed first as this feature builds on that infrastructure.

## Out of Scope

- Handlers for generate_content_config component (future work).
- Multi-agent component addressing (future work).
- Changes to the ComponentHandler protocol itself.
- New evolution strategies or mutation operators.
