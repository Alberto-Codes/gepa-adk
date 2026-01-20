# Feature Specification: Component-Aware Reflection Agents

**Feature Branch**: `142-component-aware-reflection`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "Add component-aware reflection agents with validation tools. Provide pre-built reflection agent factories for different component types (text, output_schema, agent definition). Each factory creates an ADK agent with appropriate instruction and validation tools. Selection logic picks the right reflection agent based on component name being evolved."
**Related Issue**: #133

## Problem Statement

When evolving components like `output_schema` (Python/Pydantic code), the reflection agent proposes mutations without knowing if the proposed schema is syntactically valid. Invalid schemas waste evolution iterations since they fail at validation time. The reflection agent cannot self-correct because it lacks access to validation tools.

The system should automatically provide the right reflection agent with appropriate tools based on what component is being evolved.

## Scope

### In Scope (MVP)

- **`output_schema`** component validation via Pydantic schema validator tool
- Text components (instructions, description) - default reflection, no validation tools
- Extensible registry architecture for adding future validators
- Auto-selection of reflection agent based on component name

### Out of Scope (Deferred)

The following are deferred but the architecture must support them:

- `generate_content_config` validation
- `tools` definition validation
- `input_schema` validation
- Full ADK agent definition validation
- Any other structured ADK agent attributes

### Long-Term Vision

Any attribute in the ADK agent definition that has a structured format (not free-form text) should eventually have a corresponding validator. The registry pattern enables this without changing the core reflection flow.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Output Schema Evolution with Validation (Priority: P1)

A developer evolves an agent's `output_schema` component. The reflection agent has access to a schema validation tool. When the agent proposes a new schema, it can validate the schema before returning it, fixing any syntax errors internally. Only valid schemas are returned from reflection.

**Why this priority**: This is the core use case that motivated the feature. Invalid schema proposals waste iteration budget and slow evolution.

**Independent Test**: Can be tested by running output_schema evolution and verifying that all proposals from reflection are syntactically valid Pydantic models.

**Acceptance Scenarios**:

1. **Given** a reflection agent for output_schema with validation tool, **When** the agent proposes a schema with a syntax error, **Then** it uses the validation tool to detect the error and fixes it before returning
2. **Given** a reflection agent for output_schema with validation tool, **When** the agent proposes a valid schema, **Then** the schema is returned without needing tool use
3. **Given** a reflection agent for output_schema, **When** reflection completes, **Then** the returned schema text passes `validate_schema_text()` validation

---

### User Story 2 - Automatic Reflection Agent Selection (Priority: P1)

A developer runs evolution without manually configuring reflection agents. The system detects which component is being evolved and automatically selects the appropriate reflection agent with relevant tools.

**Why this priority**: Zero-configuration experience is critical for adoption. Users shouldn't need to manually wire up validators.

**Independent Test**: Can be tested by evolving different component types and verifying the correct reflection agent is used for each.

**Acceptance Scenarios**:

1. **Given** evolution of an "output_schema" component, **When** reflection is invoked, **Then** a schema-aware reflection agent with validation tool is used
2. **Given** evolution of an "instructions" component, **When** reflection is invoked, **Then** a text reflection agent without validation tools is used
3. **Given** evolution of a component with no registered validator, **When** reflection is invoked, **Then** the default text reflection agent is used

---

### User Story 3 - Custom Reflection Agent Override (Priority: P2)

A developer wants to use their own custom reflection agent with specific tools or instructions. They can provide their own agent and it will be used instead of the auto-selected default.

**Why this priority**: Power users need escape hatches for custom behavior.

**Independent Test**: Can be tested by providing a custom reflection agent and verifying it is used during evolution.

**Acceptance Scenarios**:

1. **Given** a user-provided custom reflection agent, **When** evolution runs, **Then** the custom agent is used instead of auto-selected defaults
2. **Given** a user-provided reflection agent with custom tools, **When** reflection runs, **Then** the custom tools are available during reflection

---

### User Story 4 - Extensible Validator Registry (Priority: P2)

A developer can register custom validators for new component types. The registry accepts new component name to validator mappings, enabling future expansion without modifying core reflection logic.

**Why this priority**: Enables future validators (tools, input_schema, etc.) without core changes.

**Independent Test**: Can be tested by registering a mock validator for a custom component name and verifying it is invoked.

**Acceptance Scenarios**:

1. **Given** a custom validator registered for component "my_custom_component", **When** evolution runs on that component, **Then** the custom validator's reflection agent is used
2. **Given** the extensible registry, **When** a new validator is added, **Then** no changes to core reflection code are required

---

### Edge Cases

- What happens when validation tool returns errors the LLM cannot fix after multiple attempts? System should return the best attempt and log a warning, allowing evolution to proceed with downstream validation as fallback.
- How does system handle component names that partially match validators (e.g., "my_output_schema")? Use exact match only for MVP; partial/pattern matching is out of scope.
- What happens when a user provides a reflection agent but the component needs validation tools the agent doesn't have? User-provided agent is used as-is; user is responsible for including needed tools.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a reflection agent factory for text components that creates an agent with text-focused reflection instruction and no validation tools
- **FR-002**: System MUST provide a reflection agent factory for `output_schema` components that creates an agent with schema-focused reflection instruction and a schema validation tool
- **FR-003**: System MUST provide a component-to-reflection-agent registry that maps component names to appropriate reflection agent factories
- **FR-004**: System MUST auto-select the appropriate reflection agent based on component name when no custom agent is provided
- **FR-005**: System MUST allow users to override auto-selection by providing their own reflection agent
- **FR-006**: Validation tools MUST return structured results with validity status and error details
- **FR-007**: Schema validation tool MUST use existing `validate_schema_text()` function from schema_utils
- **FR-008**: Reflection instructions for `output_schema` components MUST guide the agent to use validation tools before returning proposals
- **FR-009**: System MUST fall back to default text reflection when component name has no registered validator
- **FR-010**: System MUST preserve backward compatibility - existing code using default reflection must continue to work
- **FR-011**: Registry MUST support adding new component validators without modifying core reflection code

### Key Entities

- **ReflectionAgentFactory**: A callable that creates an appropriately configured ADK agent for a specific component type
- **ComponentValidatorRegistry**: Maps component names to validation tools and reflection agent factories. Extensible for future validators.
- **ValidationTool**: ADK-compatible function tool that validates component text and returns structured results

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of `output_schema` proposals from reflection pass syntax validation (vs. current state where invalid proposals waste iterations)
- **SC-002**: Zero configuration required for `output_schema` and text components - auto-selection works out of the box
- **SC-003**: Evolution iteration efficiency improves by reducing wasted iterations on invalid schema proposals
- **SC-004**: Existing evolution code continues to work without modification (backward compatibility)
- **SC-005**: Custom reflection agent override works for 100% of component types
- **SC-006**: New validators can be added to registry without modifying core reflection code

## Assumptions

- The reflection agent will be an LlmAgent (required for tool use in ADK)
- Schema validation errors are typically fixable by the LLM with 1-2 tool call iterations
- Component name string matching is sufficient for auto-selection (exact match for MVP)
- Users who need complex validation logic will provide their own reflection agents
- Future validators for other ADK attributes will follow the same registry pattern
