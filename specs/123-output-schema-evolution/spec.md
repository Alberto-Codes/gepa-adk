# Feature Specification: Output Schema Evolution

**Feature Branch**: `123-output-schema-evolution`
**Created**: 2026-01-18
**Status**: Draft
**Input**: GitHub Issue #83 - Enable output_schema evolution as a component

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evolve Output Schema Alongside Instructions (Priority: P1)

As a gepa-adk developer, I want to evolve an agent's output schema as a component so that I can optimize the structured output definition to improve agent performance, just like I can evolve instructions today.

Currently, gepa-adk can evolve the `instruction` component of a generator agent. Generator agents also have `output_schema` (Pydantic models) that define structured outputs. The system should treat output schemas as evolvable components, enabling the evolution engine to propose and test improved schema definitions.

**Why this priority**: This is the core capability. Without the ability to evolve output schemas, the feature has no value. This enables optimization of structured outputs which is critical for agents that must produce specific data formats.

**Independent Test**: Can be fully tested by configuring evolution with `components=["output_schema"]` on an agent with an existing output schema, running evolution, and verifying the schema text is mutated and validated.

**Acceptance Scenarios**:

1. **Given** a generator agent with an output_schema (Pydantic model), **When** I configure evolution with `components=["output_schema"]`, **Then** the schema is converted to text and stored as component_text for evolution.

2. **Given** a component_text containing a serialized output schema, **When** the reflection agent proposes an improved schema, **Then** the proposed text is validated as a syntactically correct schema before acceptance.

3. **Given** an invalid schema proposal (syntax errors, missing required elements), **When** the validator checks the proposed text, **Then** the proposal is rejected and not accepted into the population.

---

### User Story 2 - Validate Schema Mutations (Priority: P2)

As a gepa-adk developer, I want proposed schema mutations to be validated before acceptance so that invalid schemas are rejected and don't break my agent pipeline.

The evolution process generates mutations through LLM reflection. Unlike free-form text instructions, schema definitions have strict syntactic and semantic requirements. Invalid schemas would cause runtime errors when applied to agents.

**Why this priority**: Validation is essential for reliability. Without validation, evolved schemas could break agent execution. However, it depends on the core evolution capability (P1) being in place first.

**Independent Test**: Can be tested by providing various valid and invalid schema texts to the validator and verifying correct accept/reject decisions.

**Acceptance Scenarios**:

1. **Given** a proposed schema text with valid syntax and structure, **When** the validator checks it, **Then** the validation passes and the proposal can be accepted.

2. **Given** a proposed schema text with syntax errors, **When** the validator checks it, **Then** the validation fails with a clear error message indicating the syntax issue.

3. **Given** a proposed schema text that is syntactically valid but missing required fields (e.g., no class definition), **When** the validator checks it, **Then** the validation fails with an error indicating what is missing.

---

### User Story 3 - Use Evolved Schema with Agent (Priority: P3)

As a gepa-adk developer, I want to convert an evolved schema text back into a usable Pydantic model so that I can apply the optimized schema to my agent.

After evolution completes, the result is a text representation of the schema. To actually use the evolved schema with an agent, it must be converted back to a Pydantic model class that can be assigned to `agent.output_schema`.

**Why this priority**: This is the final step that delivers value. Without deserialization, evolved schemas remain as text and cannot be used. Depends on P1 and P2 being complete.

**Independent Test**: Can be tested by deserializing a valid schema text and verifying the resulting class can be used as an output_schema on an agent.

**Acceptance Scenarios**:

1. **Given** a valid evolved schema text, **When** I deserialize it, **Then** I receive a Pydantic model class that can be used as agent.output_schema.

2. **Given** a deserialized schema class, **When** I assign it to an agent's output_schema, **Then** the agent uses the new schema for structured output generation.

---

### Edge Cases

- What happens when the schema text contains imports that aren't available in the runtime environment?
- How does the system handle schema proposals that are syntactically valid but semantically incompatible with the agent's use case (e.g., removes a field the downstream system expects)?
- What happens when deserializing a schema that conflicts with an existing class name in the namespace?
- How does the system handle circular references or complex type annotations in schemas?
- What happens when the LLM proposes a schema in an unexpected format (e.g., JSON Schema instead of Python class)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST convert a Pydantic model class to a text representation suitable for evolution (serialization).
- **FR-002**: System MUST store serialized schema text in `Candidate.components["output_schema"]` using the existing component architecture.
- **FR-003**: System MUST validate proposed schema text before accepting it into the population.
- **FR-004**: System MUST reject schema proposals with syntax errors and provide clear error messages.
- **FR-005**: System MUST reject schema proposals that do not define a valid Pydantic BaseModel class.
- **FR-006**: System MUST convert validated schema text back to a usable Pydantic model class (deserialization).
- **FR-007**: System MUST integrate schema validation into the evolution acceptance flow so invalid schemas are never accepted.
- **FR-008**: System MUST support evolving output_schema independently or alongside other components (e.g., instruction).
- **FR-009**: System MUST preserve existing field definitions and constraints when serializing schemas.
- **FR-010**: System MUST handle schema evolution using the same reflection/mutation process used for instruction evolution.

### Key Entities

- **Schema Text**: The serialized text representation of a Pydantic model class, stored as component_text during evolution. Contains class definition, field definitions, and type annotations.
- **Schema Validator**: A component that checks proposed schema text for syntactic and structural validity before acceptance.
- **Component**: An evolvable unit with a name (e.g., "output_schema") and text content. Schemas are components alongside instructions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can evolve output schemas by specifying `components=["output_schema"]` in evolution configuration.
- **SC-002**: 100% of syntactically invalid schema proposals are rejected by the validator.
- **SC-003**: Valid evolved schemas can be deserialized and used with agents without runtime errors.
- **SC-004**: Schema evolution achieves measurable improvement in agent output quality (same metrics as instruction evolution).
- **SC-005**: The evolution process completes without errors when output_schema is the target component.
- **SC-006**: Developers can evolve both instruction and output_schema components in the same evolution run.

## Assumptions

- **A-001**: Schema serialization will use Python source code format (class definition) rather than JSON Schema, as this aligns with how developers define Pydantic models.
- **A-002**: Deserialization will execute validated Python code in a controlled manner to create the class. Security is addressed by only executing code that passes validation.
- **A-003**: The validator will check for valid Python syntax and presence of a BaseModel subclass, but will not perform deep semantic validation of field types or constraints.
- **A-004**: Evolved schemas must be self-contained (no external imports beyond standard library and Pydantic).
- **A-005**: The existing component selector and evolution engine architecture supports adding new component types without modification.

## Dependencies

- **D-001**: Depends on existing `Candidate.components` architecture (already supports arbitrary component names).
- **D-002**: Depends on existing reflection/mutation proposer (will propose schema mutations like instruction mutations).
- **D-003**: Depends on Pydantic library for model introspection and validation.
