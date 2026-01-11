# Feature Specification: ADK-First Reflection Agent Support

**Feature Branch**: `010-adk-reflection-agent`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "Implement ADK-first reflection agent support - Enable gepa-adk users to use ADK agents for reflection, providing better instruction proposals with configurable prompts and observability."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ADK Agent Reflection (Priority: P1)

As a gepa-adk user, I want to configure an ADK agent for reflection so that I get better instruction proposals with configurable prompts and full ADK observability (tracing, session state).

**Why this priority**: This is the core value proposition - enabling ADK-first reflection with all the benefits of the ADK ecosystem (configurable agents, session services, observability).

**Independent Test**: Can be fully tested by configuring an ADK LlmAgent with a custom instruction prompt and verifying that the proposer uses it to generate mutations with proper session state handling.

**Acceptance Scenarios**:

1. **Given** an ADK reflection agent is configured with custom instructions, **When** the proposer generates a mutation, **Then** it uses the ADK agent via Runner.run_async() instead of raw LiteLLM
2. **Given** an ADK reflection agent with a custom SessionService, **When** the reflection runs, **Then** the SessionService is used for session management
3. **Given** an ADK reflection agent is configured, **When** the reflection runs, **Then** the session state contains current_instruction and execution_feedback

---

### User Story 2 - Context Passing to Reflection Agent (Priority: P2)

As a gepa-adk user, I want the reflection agent to receive the current instruction and execution feedback via session state so that it has full context for generating improved instructions.

**Why this priority**: Context availability is essential for meaningful reflection - without it, the ADK agent cannot provide useful suggestions.

**Independent Test**: Can be fully tested by verifying that session_state dictionary contains expected keys and values before Runner.run_async() is called.

**Acceptance Scenarios**:

1. **Given** current instruction text and a list of feedback items, **When** the reflection agent runs, **Then** session state contains "current_instruction" with the instruction text
2. **Given** execution feedback as a list of dictionaries, **When** the reflection agent runs, **Then** session state contains "execution_feedback" as JSON-serialized string

---

### User Story 3 - LiteLLM Fallback (Priority: P3)

As a gepa-adk user, I want the proposer to fall back to LiteLLM when no ADK reflection agent is configured so that existing workflows continue to work without modification.

**Why this priority**: Backwards compatibility ensures existing users are not disrupted and allows gradual adoption.

**Independent Test**: Can be fully tested by creating a proposer without an ADK reflection function and verifying it still works via litellm.acompletion().

**Acceptance Scenarios**:

1. **Given** no ADK reflection agent is configured (adk_reflection_fn is None), **When** the proposer generates a mutation, **Then** it uses litellm.acompletion() as before
2. **Given** a proposer created with default parameters, **When** propose() is called, **Then** behavior is identical to the current implementation

---

### Edge Cases

- What happens when the ADK agent returns an empty response? System falls back to original candidate text (consistent with LiteLLM behavior).
- What happens when the ADK runner raises an exception? Exception propagates to caller (same as LiteLLM error handling).
- What happens when session_service is not provided? Default to InMemorySessionService.
- What happens when feedback list is empty? Early return None without calling ADK agent (preserve existing optimization).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a factory function to create a reflection callable from an ADK LlmAgent
- **FR-002**: System MUST allow optional SessionService injection for custom session management
- **FR-003**: System MUST default to InMemorySessionService when no SessionService is provided
- **FR-004**: System MUST pass current_instruction as a string in session state
- **FR-005**: System MUST pass execution_feedback as a JSON-serialized string in session state
- **FR-006**: System MUST use a standard input text prompt for the reflection agent (e.g., "Propose an improved instruction based on the feedback.")
- **FR-007**: AsyncReflectiveMutationProposer MUST accept an optional adk_reflection_fn callable parameter
- **FR-008**: System MUST use adk_reflection_fn when provided, otherwise fall back to litellm.acompletion()
- **FR-009**: System MUST return only the improved instruction text (stripped of whitespace) from reflection
- **FR-010**: System MUST handle empty/None ADK agent responses by falling back to original candidate text

### Key Entities

- **Reflection Function**: A callable that takes (current_instruction: str, feedback: list[dict]) and returns the improved instruction text
- **Session State**: Dictionary containing context for the reflection agent with keys "current_instruction" and "execution_feedback"

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure ADK reflection agents with custom prompts and observe reflection behavior through ADK tracing
- **SC-002**: All existing tests pass without modification (backwards compatibility maintained)
- **SC-003**: New integration tests verify ADK agent path with 100% coverage of acceptance scenarios
- **SC-004**: Reflection context (instruction + feedback) is correctly available to ADK agents in all scenarios

## Assumptions

- Users are familiar with Google ADK concepts (LlmAgent, Runner, SessionService)
- The reflection agent's instruction prompt is configured at agent creation time, not at runtime
- The input_text parameter to Runner.run_async() serves as a trigger prompt, not the main context (context comes from session_state)
- JSON serialization of feedback is acceptable for session state (ADK session state supports strings)
- user_id for reflection sessions can be a fixed value like "reflection" since reflection is not user-specific

## Dependencies

- Depends on: #7 (AsyncReflectiveMutationProposer must exist)
- Parent: #1 (Phase 2 milestone)
