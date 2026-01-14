# Feature Specification: Wire ADK Reflection Agent into evolve() API

**Feature Branch**: `021-adk-reflection-evolve`
**Created**: 2026-01-14
**Status**: Implemented
**Input**: User description: "GitHub Issue #48 - Wire ADK reflection agent into evolve() API"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Custom ADK Reflection Agent (Priority: P1)

As a gepa-adk user, I want to pass an ADK agent as the reflection agent to `evolve()`, so that I get ADK observability and configurable prompts for instruction improvement.

**Why this priority**: This is the core feature request. Users need the ability to use their own configured ADK LlmAgent for reflection to gain full observability through ADK's tracing infrastructure and to customize the reflection prompts for their specific use cases.

**Independent Test**: Can be fully tested by calling `evolve()` with a custom reflection agent and verifying that the agent is invoked for reflection operations, with session state properly populated.

**Acceptance Scenarios**:

1. **Given** I have an ADK LlmAgent configured as a reflection agent, **When** I call `evolve(agent, trainset, reflection_agent=my_reflection_agent)`, **Then** the proposer uses `my_reflection_agent` via the ADK Runner for reflection.
2. **Given** I have an ADK LlmAgent configured as a reflection agent, **When** the reflection agent is invoked, **Then** the session state contains `current_instruction` and `execution_feedback` context.
3. **Given** I have configured ADK tracing, **When** I call `evolve()` with a custom reflection agent, **Then** reflection operations appear in the ADK trace output.

---

### User Story 2 - Default LiteLLM Reflection Behavior (Priority: P2)

As a gepa-adk user, I want the system to continue working without requiring a reflection agent, so that existing workflows remain unchanged and I only opt-in to ADK reflection when needed.

**Why this priority**: Backward compatibility is essential. Users who don't specify a reflection agent should experience no change in behavior.

**Independent Test**: Can be fully tested by calling `evolve()` without any reflection agent parameter and verifying the default LiteLLM-based reflection behavior continues to work.

**Acceptance Scenarios**:

1. **Given** I don't specify a `reflection_agent`, **When** I call `evolve(agent, trainset)`, **Then** the proposer uses the default LiteLLM completion for reflection (current behavior preserved).
2. **Given** I don't specify a `reflection_agent`, **When** I call `evolve()`, **Then** no warning or deprecation message is logged about missing reflection agent.

---

### User Story 3 - Clear Error Handling (Priority: P3)

As a gepa-adk user, I want clear feedback when I provide an invalid reflection agent, so that I can quickly diagnose and fix configuration issues.

**Why this priority**: Good error messages improve developer experience and reduce debugging time when configuration is incorrect.

**Independent Test**: Can be tested by providing various invalid inputs as the reflection agent and verifying appropriate error messages.

**Acceptance Scenarios**:

1. **Given** I provide an invalid object as `reflection_agent`, **When** I call `evolve()`, **Then** the system provides a clear error message indicating what type of agent is expected.

---

### Edge Cases

- **Reflection agent exception**: When the reflection agent raises an exception during reflection, the system MUST catch the exception, log it with context, and re-raise as `EvolutionError` with the original exception as cause. Evolution fails; no silent fallback to LiteLLM.
- **Malformed response**: When the reflection agent returns a non-string or empty string, the system MUST raise `EvolutionError` with a message indicating the expected return type.
- **Explicit None**: When `reflection_agent=None` is explicitly passed, the system MUST treat it identically to omitting the parameter (use default LiteLLM behavior).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional `reflection_agent` parameter in the `evolve()` function.
- **FR-002**: System MUST use the provided reflection agent for generating instruction improvements when `reflection_agent` is specified.
- **FR-003**: System MUST use the default LiteLLM-based reflection when `reflection_agent` is not specified or is `None`.
- **FR-004**: System MUST populate session state with `current_instruction` and `execution_feedback` before invoking the reflection agent.
- **FR-005**: System MUST NOT log "not yet implemented" warnings when `reflection_agent` is provided.
- **FR-006**: System MUST integrate with ADK's observability infrastructure when using an ADK reflection agent.
- **FR-007**: System MUST provide clear error messages when an invalid reflection agent is provided.

### Key Entities

- **Reflection Agent**: An ADK LlmAgent configured to analyze execution feedback and propose instruction improvements. It receives context via session state.
- **Session State**: Contains `current_instruction` (the agent's current system instruction) and `execution_feedback` (results and feedback from executing the agent on training examples).
- **evolve() API**: The public function that orchestrates agent evolution, now accepting an optional reflection agent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully call `evolve()` with a custom ADK reflection agent and see reflection operations in ADK traces.
- **SC-002**: Existing workflows without `reflection_agent` continue to function identically to before this feature (100% backward compatibility).
- **SC-003**: All acceptance scenarios pass automated testing.
- **SC-004**: Users can configure custom reflection prompts through their ADK LlmAgent and see those prompts used during evolution.

## Assumptions

- The ADK reflection infrastructure (`create_adk_reflection_fn()`) already exists and works correctly.
- The `AsyncReflectiveMutationProposer` already accepts an `adk_reflection_fn` parameter.
- Users providing a reflection agent will use a valid ADK LlmAgent instance.
- Session state management via ADK's InMemorySessionService is already implemented.

## Dependencies

- Depends on existing ADK reflection infrastructure (feature 010-adk-reflection-agent).
- Depends on public API infrastructure (feature 018-public-api).
