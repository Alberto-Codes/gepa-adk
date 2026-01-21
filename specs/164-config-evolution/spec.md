# Feature Specification: Generate Content Config Evolution

**Feature Branch**: `164-config-evolution`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "Add generate_content_config as evolvable component"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evolve LLM Generation Config (Priority: P1)

As a GEPA developer, I want to include `generate_content_config` in my evolution configuration, so that the system automatically optimizes LLM generation parameters (temperature, top_p, top_k, max_output_tokens) alongside other agent components.

**Why this priority**: This is the core value proposition - enabling automatic optimization of LLM parameters to improve agent performance for specific tasks without manual tuning.

**Independent Test**: Can be fully tested by configuring evolution with `components=["generate_content_config"]` and verifying that the config parameters change based on reflection agent proposals.

**Acceptance Scenarios**:

1. **Given** an agent with `generate_content_config(temperature=0.7, top_p=0.9)`, **When** I configure evolution with `components=["generate_content_config"]`, **Then** the config is serialized to a text representation for reflection.
2. **Given** the reflection agent proposes an improved config with `temperature=0.5`, **When** the proposal is validated and accepted, **Then** the agent's `generate_content_config` is updated to use the new parameters.
3. **Given** evolution is running with config component, **When** the evolved candidate fails evaluation, **Then** the original config is restored automatically.

---

### User Story 2 - Serialize Config for Reflection (Priority: P2)

As a GEPA developer, I want the `generate_content_config` to be serialized into a human-readable format, so that the reflection agent can understand and propose meaningful improvements.

**Why this priority**: Without proper serialization, the reflection agent cannot reason about the config parameters effectively.

**Independent Test**: Can be tested by calling the serialize method on a handler and verifying the output is a parseable, readable text representation with parameter descriptions.

**Acceptance Scenarios**:

1. **Given** an agent with configured generation parameters, **When** `GenerateContentConfigHandler.serialize(agent)` is called, **Then** it returns a parseable YAML text representation.
2. **Given** the serialized config output, **When** a developer reads it, **Then** they can understand what each parameter controls through included comments or descriptions.

---

### User Story 3 - Apply Proposed Config Changes (Priority: P2)

As a GEPA developer, I want proposed config changes to be applied to my agent safely, so that I can test the evolved parameters while preserving the ability to rollback.

**Why this priority**: Safe application and rollback capability is essential for the evolution loop to function correctly.

**Independent Test**: Can be tested by applying a proposed config, verifying the agent uses new parameters, then restoring and verifying original parameters are back.

**Acceptance Scenarios**:

1. **Given** proposed config text with new parameter values, **When** `GenerateContentConfigHandler.apply(agent, text)` is called, **Then** the agent's `generate_content_config` is updated to the new values.
2. **Given** `apply()` was called successfully, **When** checking the return value, **Then** the original config is returned for potential restore operations.
3. **Given** an original config reference from a previous `apply()`, **When** `restore(agent, original)` is called, **Then** the agent's config reverts to the original state.

---

### User Story 4 - Validate Config Before Acceptance (Priority: P3)

As a GEPA developer, I want proposed config changes to be validated before acceptance, so that invalid parameter values are rejected with clear error messages.

**Why this priority**: Validation prevents runtime errors from invalid configs, but the system can still function with basic type checking.

**Independent Test**: Can be tested by proposing invalid config values (e.g., temperature > 2.0) and verifying rejection with appropriate error messages.

**Acceptance Scenarios**:

1. **Given** proposed config text with temperature=3.0 (out of valid range 0.0-2.0), **When** validation runs, **Then** the proposal is rejected with a clear error message indicating the constraint violation.
2. **Given** proposed config text with an unknown parameter, **When** validation runs, **Then** a warning is logged but the proposal is accepted (unknown parameters may be model-specific).
3. **Given** proposed config text with valid parameters, **When** validation runs, **Then** the proposal passes validation and can be applied.

---

### Edge Cases

- What happens when the agent has no `generate_content_config` set (None/default)?
  - The handler returns a default empty config representation or indicates no config exists.
- What happens when the proposed config contains only a subset of parameters?
  - Partial configs are merged with existing values; unspecified parameters retain their current values.
- What happens when deserialization fails due to malformed text?
  - The handler raises a clear validation error and rejects the proposal.
- What happens when different models support different parameter subsets?
  - Validation warns about unsupported parameters but does not fail for unknown parameters that might be model-specific.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support `generate_content_config` as an evolvable component type in the evolution configuration.
- **FR-002**: System MUST serialize `generate_content_config` to a text format (YAML) that is readable by both humans and LLMs.
- **FR-003**: System MUST deserialize proposed config text back into a valid `GenerateContentConfig` object.
- **FR-004**: System MUST validate proposed config values against known parameter constraints before acceptance:
  - `temperature`: 0.0-2.0
  - `top_p`: 0.0-1.0
  - `top_k`: positive number
  - `max_output_tokens`: positive integer
- **FR-005**: System MUST preserve the original config when applying changes, enabling rollback.
- **FR-006**: System MUST restore the original config if the evolved candidate fails evaluation.
- **FR-007**: System SHOULD provide a dedicated reflection agent capable of reasoning about config parameters (optional enhancement; generic reflection agent works without this).
- **FR-008**: System MUST register the config handler in the default component handler registry.
- **FR-009**: System MUST include parameter descriptions/comments in serialized output to aid reflection agent understanding.

### Key Entities

- **GenerateContentConfig**: The ADK configuration object containing LLM generation parameters (temperature, top_p, top_k, max_output_tokens, safety_settings, response_modalities).
- **GenerateContentConfigHandler**: Component handler implementing serialize, apply, and restore operations for `GenerateContentConfig`.
- **Config Reflection Agent**: A specialized reflection agent that proposes improvements to generation config parameters based on task requirements and observed performance.
- **Component Type Constant**: A constant (`COMPONENT_GENERATE_CONFIG`) identifying this component type in the evolution system.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can successfully evolve `generate_content_config` by adding it to the components list, with the evolution loop completing without errors.
- **SC-002**: The serialization format is understood by the reflection agent, resulting in at least 80% of proposals containing valid parameter modifications.
- **SC-003**: All config changes are validated before application, with 100% of out-of-range values being rejected.
- **SC-004**: The rollback mechanism works reliably, with 100% of failed candidates having their original config restored.
- **SC-005**: The feature integrates seamlessly with existing component evolution patterns, requiring no changes to the core evolution loop.

## Assumptions

- The ADK `GenerateContentConfig` object structure is stable and follows documented parameter constraints.
- YAML format is appropriate for serialization as it is LLM-friendly and human-readable.
- The reflection agent can reason about LLM parameters given appropriate context and descriptions.
- Parameter constraints (e.g., temperature 0.0-2.0) follow Google's documented Gemini API specifications.
- The component handler registry pattern from recent features (#162, #163) is the standard approach for new components.

## Dependencies

- **#163** - Migrate instruction/output_schema to ComponentHandler pattern (blocked by - provides the handler pattern to follow).

## Out of Scope

- Evolving `safety_settings` as a separate component (can be included later).
- Model-specific parameter validation (initial implementation uses general Gemini constraints).
- Automatic parameter constraint discovery based on model capabilities.
- UI or visualization for config evolution progress.
