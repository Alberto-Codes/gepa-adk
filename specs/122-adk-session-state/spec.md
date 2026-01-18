# Feature Specification: ADK Session State Management for Reflection Agent

**Feature Branch**: `122-adk-session-state`
**Created**: 2026-01-18
**Status**: Draft
**Input**: User description: "gh issue 100"
**Related Issue**: GitHub Issue #100

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Session State Data Flow (Priority: P1)

As a GEPA developer, I want the reflection agent to receive input data (component_text and trials) through ADK session state, so that the framework handles data flow instead of manual user message construction.

**Why this priority**: This is the foundational change that enables all other ADK state management features. Without session state injection, the reflection agent cannot leverage ADK's built-in patterns.

**Independent Test**: Can be fully tested by configuring a reflection agent with session state injection, passing component_text and trials, and verifying the agent accesses data via ADK's state templating syntax.

**Acceptance Scenarios**:

1. **Given** a reflection agent configured with ADK session state, **When** component_text and trials are passed to the agent, **Then** the data is accessible through session.state properties
2. **Given** a reflection agent with state templating in its instructions, **When** the agent executes, **Then** it can access {component_text} and {trials} values via ADK's inject_session_state()
3. **Given** input data provided via session state, **When** the agent processes it, **Then** no manual user message construction is required

---

### User Story 2 - Automatic Output Storage via output_key (Priority: P2)

As a GEPA developer, I want the reflection agent to store its proposal output automatically in session state using ADK's output_key mechanism, so that downstream components can retrieve results from a predictable state location.

**Why this priority**: Once data flows into the agent via state (P1), the natural next step is ensuring outputs flow back out via state. This completes the bidirectional state flow pattern.

**Independent Test**: Can be fully tested by configuring a reflection agent with output_key, running it, and verifying the proposal is retrievable from session.state[output_key].

**Acceptance Scenarios**:

1. **Given** a reflection agent with output_key configured, **When** the agent produces a proposal, **Then** the result is stored in session.state at the configured key
2. **Given** a completed reflection agent execution, **When** extract_final_output is called, **Then** it retrieves the proposal from session state instead of parsing messages
3. **Given** an output_key of "proposed_instruction", **When** the agent completes, **Then** session.state["proposed_instruction"] contains the proposal text

---

### User Story 3 - Multi-Agent Workflow State Integration (Priority: P3)

As a GEPA developer, I want the critic and reflection agents to share state through ADK's session management when executing in sequence, so that multi-agent workflows operate without manual message passing between agents.

**Why this priority**: This enables the full vision of ADK-native multi-agent workflows, building on the foundation of P1 and P2. It's critical for parallel Pareto evolution which requires proper state isolation.

**Independent Test**: Can be fully tested by running a workflow with critic and reflection agents in sequence and verifying state flows automatically between them without manual construction.

**Acceptance Scenarios**:

1. **Given** a workflow with critic and reflection agents, **When** they execute in sequence, **Then** the critic's output is available to the reflection agent via session state
2. **Given** ADK session state management, **When** multiple agents run in a workflow, **Then** each agent can read from and write to shared session state
3. **Given** a multi-agent workflow, **When** execution completes, **Then** final results are accessible from session state without parsing individual agent messages

---

### Edge Cases

- What happens when required session state keys (component_text, trials) are missing or null?
- How does the system handle malformed or invalid data in session state?
- What happens when output_key is not configured but state retrieval is attempted?
- How does state behave when an agent fails mid-execution?
- What happens when state templating references a non-existent key?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST inject component_text and trials into ADK session state before reflection agent execution
- **FR-002**: System MUST configure reflection agent instructions to use ADK state templating syntax ({key})
- **FR-003**: System MUST configure output_key on the reflection agent to automatically store proposals in session state
- **FR-004**: System MUST provide a mechanism to retrieve the final proposal output from session state
- **FR-005**: System MUST use InMemorySessionService to maintain state across agent calls within a workflow
- **FR-006**: System MUST eliminate manual user message construction for passing data to the reflection agent
- **FR-007**: System MUST enable state to flow between critic and reflection agents in sequential workflows
- **FR-008**: System MUST handle missing or null session state values gracefully with appropriate error messages
- **FR-009**: System MUST preserve backward compatibility with existing reflection agent interfaces during transition

### Key Entities

- **Session State**: The ADK-managed state container that persists data across agent calls within a workflow; contains component_text, trials, and agent outputs
- **Reflection Agent**: The LlmAgent that generates instruction proposals; configured with state templating and output_key
- **Component Text**: The text content being evolved; stored in session.state.component_text
- **Trials**: The scored trial data informing reflection; stored in session.state.trials
- **Proposed Instruction**: The agent's output proposal; stored at session.state[output_key]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All reflection agent input data flows through session state with zero manual user message construction required
- **SC-002**: Agent proposals are retrievable from session state in 100% of successful executions
- **SC-003**: Multi-agent workflows operate with state passed entirely through ADK session management
- **SC-004**: Existing tests continue to pass during transition, maintaining backward compatibility
- **SC-005**: Development effort for new multi-agent workflows is reduced by eliminating boilerplate message construction code

## Assumptions

- ADK's InMemorySessionService is suitable for the current use case (no persistence required across process restarts)
- The existing reflection agent can be modified to accept state-templated instructions without breaking existing functionality
- ADK's state templating syntax ({key}) is stable and documented
- Output_key mechanism works as documented in ADK for LlmAgent types
- State isolation between concurrent workflows is handled by ADK's session management

## Dependencies

- Google ADK version 1.22.0 or higher (current dependency)
- Existing reflection agent implementation in src/gepa_adk/engine/adk_reflection.py
- Existing ADK adapter in src/gepa_adk/adapters/adk_adapter.py
- Related issue #83 (output_schema for reflection agent) may influence implementation
- Related issue #84 (ADK reflection agents) represents current implementation state
