# Feature Specification: ADK Session State Template Substitution

**Feature Branch**: `035-adk-session-template`
**Created**: 2026-01-18
**Status**: Draft
**Input**: User description: "Add ADK session state template substitution for agent instructions"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Template Substitution (Priority: P1)

A GEPA developer wants to use ADK's native template substitution syntax in reflection agent instructions instead of manually constructing user messages with f-strings. The agent instruction contains `{state.component_text}` placeholder, and when the agent runs with session state containing the `component_text` value, the placeholder is automatically replaced.

**Why this priority**: This is the core functionality that replaces the current workaround of manually embedding data in user messages. Without this, the feature has no value.

**Independent Test**: Can be fully tested by creating an agent with a templated instruction, populating session state, running the agent, and verifying the placeholder was substituted correctly.

**Acceptance Scenarios**:

1. **Given** a reflection agent with instruction containing `{state.component_text}`, **When** session state contains `component_text` value and the agent runs, **Then** the placeholder is replaced with the session state value in the agent's context.
2. **Given** a reflection agent with instruction containing `{state.component_text}`, **When** session state does NOT contain `component_text` value, **Then** the system handles the missing state gracefully (logs warning, falls back to empty or original placeholder).

---

### User Story 2 - Multiple Placeholder Substitution (Priority: P1)

A GEPA developer wants to use multiple session state values in a single instruction. The instruction contains both `{state.component_text}` and `{state.trials}` placeholders, and both are substituted correctly from session state.

**Why this priority**: Real-world reflection agents require multiple data inputs (component text to improve AND trial results). This is essential for practical use.

**Independent Test**: Can be tested by creating an agent with multiple placeholders, populating session state with all values, and verifying all placeholders are substituted.

**Acceptance Scenarios**:

1. **Given** an instruction with `{state.component_text}` and `{state.trials}`, **When** session state contains both values, **Then** both placeholders are substituted correctly.
2. **Given** an instruction with multiple placeholders, **When** session state is missing one value, **Then** the present placeholder is substituted and the missing one is handled gracefully.

---

### User Story 3 - Documentation for Template Syntax (Priority: P2)

A GEPA developer who wants to use template substitution can find clear documentation explaining the `{state.key}` syntax, how to populate session state, and examples of common patterns.

**Why this priority**: Documentation enables adoption but is not required for the feature to work technically.

**Independent Test**: Can be tested by having a new developer follow the documentation to successfully implement template substitution in a new agent.

**Acceptance Scenarios**:

1. **Given** a developer checks the reflection prompts guide, **When** they look for template syntax, **Then** they find clear examples of the `{state.key}` syntax with code samples.
2. **Given** documentation exists, **When** a developer follows the examples, **Then** they can successfully implement template substitution without additional support.

---

### Edge Cases

- What happens when a placeholder key contains special characters or nested paths (e.g., `{state.data.nested}`)?
- How does the system handle when session state value is not a string (e.g., list, dict)?
- What happens if the template syntax conflicts with other curly-brace patterns in the instruction?
- How does substitution behave across different LLM model providers (Gemini, Ollama, OpenAI)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support `{state.key}` syntax in agent instructions for session state value substitution.
- **FR-002**: System MUST substitute all matching placeholders when session state contains the corresponding keys.
- **FR-003**: System MUST handle missing session state keys gracefully without crashing (log warning, use fallback behavior).
- **FR-004**: System MUST support multiple placeholders in a single instruction.
- **FR-005**: System MUST serialize non-string session state values (dict, list) to JSON format before substitution.
- **FR-006**: System MUST preserve existing agent instructions that don't contain template placeholders (backward compatibility).
- **FR-007**: System MUST work consistently across all supported LLM model providers.

### Key Entities

- **Session State**: A key-value store associated with an ADK session containing runtime data to inject into agent instructions.
- **Template Placeholder**: A `{state.key}` pattern in an agent instruction that references a session state key.
- **Reflection Agent**: An LlmAgent that proposes improvements to component text based on trial feedback.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reflection agents using template substitution produce equivalent outputs to the current user-message workaround for the same inputs.
- **SC-002**: All unit tests for template substitution pass across all supported model providers.
- **SC-003**: Documentation enables a developer to implement template substitution within 15 minutes of reading.
- **SC-004**: No increase in agent execution time due to template substitution (performance neutral).
- **SC-005**: Zero regressions in existing reflection agent functionality after migration to template syntax.

## Assumptions

- ADK's `LlmAgent` supports `{state.key}` syntax in the `instruction` parameter (to be verified during implementation research).
- `InMemorySessionService` correctly propagates state values for templating.
- The syntax `{state.key}` is the correct pattern (alternatives like `{key}` or `{{state.key}}` may need investigation).
- Template substitution occurs before the instruction is sent to the LLM, not at prompt construction time.

## Out of Scope

- Custom template syntax beyond ADK's native support.
- Template substitution in places other than agent instructions (e.g., tool descriptions).
- Dynamic session state updates during agent execution.
