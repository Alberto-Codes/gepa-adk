# Feature Specification: Unified Agent Executor

**Feature Branch**: `124-unified-agent-executor`
**Created**: 2026-01-19
**Status**: Draft
**Input**: User description: "gh issue 135"
**Related Issue**: [#135](https://github.com/Alberto-Codes/gepa-adk/issues/135) - Treat reflection agent as first-class ADK agent with full feature parity

## Problem Statement

Currently, there is a DRY (Don't Repeat Yourself) violation in how different agent types are instantiated within the evolution framework:

- **Generator and Critic agents** receive full access to ADK features (tools, callbacks, output schemas, etc.)
- **Reflection agents** go through a factory function that strips away most ADK features, leaving them with limited capabilities

This inconsistency creates friction when adding new features, as each ADK capability must be explicitly plumbed through the reflection agent factory. The reflection agent should be treated as a first-class citizen with the same privileges as generator and critic agents.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Agent Execution (Priority: P1)

As a GEPA developer, I want all agent types (generator, critic, reflection) to execute through a single unified mechanism so that I can configure any ADK feature on any agent type without special handling.

**Why this priority**: This is the foundational capability that enables all other feature parity improvements. Without a unified execution path, every new feature requires separate implementation for each agent type.

**Independent Test**: Can be fully tested by configuring an agent with any ADK feature (e.g., tools, output_key) and verifying the feature works identically whether the agent is used as a generator, critic, or reflection agent.

**Acceptance Scenarios**:

1. **Given** a reflection agent configured with tools, **When** the agent executes during evolution, **Then** the tools are available and can be called during execution
2. **Given** a generator agent configured with output_key, **When** the agent executes, **Then** the output is extracted from the correct session state key
3. **Given** any agent type, **When** execution completes, **Then** a consistent result structure is returned containing status, output, events, and timing information

---

### User Story 2 - Session Sharing Between Agents (Priority: P2)

As a GEPA developer, I want agents to optionally share session state so that a critic agent can access data produced by the generator agent without additional configuration.

**Why this priority**: Session sharing enables richer evaluation scenarios where critics can assess not just the output but also intermediate state, tool usage, and reasoning traces.

**Independent Test**: Can be tested by running a generator that sets session state values, then running a critic with the same session ID and verifying it can read those values.

**Acceptance Scenarios**:

1. **Given** a generator agent that sets session state values, **When** a critic agent reuses the same session, **Then** the critic can read the generator's state values
2. **Given** a reflection agent with session state parameters, **When** reflection executes, **Then** the template variables are correctly substituted from session state

---

### User Story 3 - Runtime Configuration Overrides (Priority: P3)

As a GEPA developer, I want to override agent instructions or output schemas at runtime so that the evolution engine can test mutations without modifying the original agent definition.

**Why this priority**: Runtime overrides are essential for the evolution process where the system needs to test candidate instructions against the current agent configuration.

**Independent Test**: Can be tested by providing an instruction override during execution and verifying the agent uses the override instead of its original instruction.

**Acceptance Scenarios**:

1. **Given** an agent with a defined instruction, **When** execution includes an instruction override, **Then** the agent uses the override instruction for that execution only
2. **Given** an agent with a defined output schema, **When** execution includes a schema override, **Then** the agent uses the override schema for that execution only
3. **Given** an execution with overrides, **When** the execution completes, **Then** the original agent definition remains unchanged

---

### User Story 4 - Configurable Timeout and Error Handling (Priority: P4)

As a GEPA developer, I want configurable timeout handling for agent execution so that long-running agents don't block the evolution process indefinitely.

**Why this priority**: Timeouts are important for robustness but are not blocking for basic functionality.

**Independent Test**: Can be tested by configuring a short timeout and verifying that execution terminates gracefully with a timeout status.

**Acceptance Scenarios**:

1. **Given** an agent execution with a timeout configured, **When** execution exceeds the timeout, **Then** the execution terminates with a TIMEOUT status
2. **Given** an agent that fails during execution, **When** the error occurs, **Then** a consistent error result is returned with details

---

### Edge Cases

- What happens when an agent is executed with an invalid session ID? The system returns an error with a clear message indicating the session was not found
- How does the system handle concurrent executions sharing the same session? The system supports concurrent reads and serializes writes to prevent race conditions
- What happens if instruction override results in invalid agent configuration? The system validates overrides before execution and returns an error if invalid
- How does the system behave when tools fail during execution? Tool errors are captured in the execution result and made available for debugging

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a unified execution interface for all agent types (generator, critic, reflection)
- **FR-002**: System MUST return consistent execution results regardless of agent type, including status, output value, error message, execution time, and captured events
- **FR-003**: System MUST support optional session reuse via session identifier parameter
- **FR-004**: System MUST support runtime instruction overrides without modifying the original agent
- **FR-005**: System MUST support runtime output schema overrides without modifying the original agent
- **FR-006**: System MUST support configurable execution timeouts with a reasonable default
- **FR-007**: System MUST preserve all ADK agent features (tools, callbacks, output_key) when executing through the unified interface
- **FR-008**: System MUST support session state injection for template variable substitution
- **FR-009**: System MUST capture execution events for trajectory recording and debugging
- **FR-010**: System MUST maintain backward compatibility with existing evolution API

### Key Entities

- **ExecutionResult**: Represents the outcome of any agent execution, containing status (success/failed/timeout), session identifier, extracted output value, error message (if any), execution duration, and captured events
- **AgentExecutor**: The unified component responsible for executing any agent type with consistent behavior and full feature support
- **Session**: Manages state between agent executions, supports sharing and isolation as configured

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All agent types (generator, critic, reflection) can use any ADK feature (tools, callbacks, output_key) without code changes specific to agent type
- **SC-002**: Developers can add new ADK features to the executor once and have them available to all agent types automatically
- **SC-003**: Session sharing between agents works correctly, with critic agents able to access generator state
- **SC-004**: Runtime overrides (instruction, schema) work for all agent types without side effects on original agent definitions
- **SC-005**: Existing evolution tests continue to pass without modification (backward compatibility)
- **SC-006**: New features (tools support via #133, callbacks via #134) can be implemented by adding parameters to the unified executor rather than modifying multiple code paths

## Assumptions

- The Google ADK Runner API will remain stable and continue to support the features being unified
- Session state is stored in memory or a compatible session service (InMemorySessionService is the default)
- All agents use the same underlying LlmAgent class from Google ADK
- The evolution engine will be updated to use the new unified executor as part of this feature

## Dependencies

- Google ADK >= 1.22.0
- This feature unblocks #133 (tools support) and #134 (callbacks)
- Reference architecture documented in `docs/architecture/unified-agent-execution-comparison.md`
