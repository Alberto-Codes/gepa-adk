# Feature Specification: Multi-Agent Unified Executor

**Feature Branch**: `125-multi-agent-executor`
**Created**: January 19, 2026
**Status**: Draft
**Input**: GitHub Issue #137 - Add unified AgentExecutor support to MultiAgentAdapter and evolve_group

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Multi-Agent Evolution (Priority: P1)

As a gepa-adk user evolving multi-agent pipelines, I want `evolve_group()` to use the unified `AgentExecutor`, so that all agent types (generator, critic, reflection) share consistent session management and feature parity with single-agent evolution.

**Why this priority**: This is the core capability that enables consistent execution across all multi-agent evolution scenarios. Without this, multi-agent evolution uses different execution paths than single-agent evolution, leading to subtle behavioral differences and maintenance burden.

**Independent Test**: Can be fully tested by calling `evolve_group()` with multiple agents and a critic, then verifying all agents execute through the unified executor with consistent session management.

**Acceptance Scenarios**:

1. **Given** a list of multiple LlmAgents, **When** I call `evolve_group(agents, primary, trainset, critic=critic)`, **Then** all agents execute through AgentExecutor and critic agent uses the same executor instance.

2. **Given** a multi-agent evolution in progress, **When** the execution logs are examined, **Then** all log entries show `uses_executor=True` for all agent executions.

3. **Given** agents that share state during execution, **When** evolution runs with the unified executor, **Then** session state is properly shared between agents in the same execution context.

---

### User Story 2 - MultiAgentAdapter Executor Integration (Priority: P1)

As a developer building custom multi-agent workflows, I want `MultiAgentAdapter` to accept an executor parameter, so that I can control session management and maintain consistency with single-agent patterns.

**Why this priority**: This enables advanced users to provide custom executor configurations and ensures the adapter layer properly supports the unified execution pattern.

**Independent Test**: Can be fully tested by instantiating `MultiAgentAdapter` with an explicit executor and verifying all internal agent executions use that executor.

**Acceptance Scenarios**:

1. **Given** a MultiAgentAdapter instance, **When** I pass `executor=AgentExecutor()` to the constructor, **Then** all internal agent executions use the provided executor.

2. **Given** a MultiAgentAdapter with an executor and a critic scorer, **When** scoring occurs, **Then** the CriticScorer receives and uses the same executor instance.

3. **Given** no executor is explicitly provided, **When** MultiAgentAdapter is instantiated, **Then** it continues to work with default execution (backward compatibility).

---

### User Story 3 - Workflow Evolution Executor Support (Priority: P2)

As a developer using `evolve_workflow()` for workflow agent optimization, I want the underlying infrastructure to use the unified AgentExecutor, so that workflow evolution benefits from the same execution consistency as other evolution modes.

**Why this priority**: Workflow evolution builds on `evolve_group()`, so this functionality is inherited once the core multi-agent executor support is implemented.

**Independent Test**: Can be fully tested by calling `evolve_workflow()` with a SequentialAgent containing multiple LlmAgents and verifying all discovered agents execute through the unified executor.

**Acceptance Scenarios**:

1. **Given** a SequentialAgent workflow with LlmAgent sub-agents, **When** I call `evolve_workflow(workflow, trainset, critic=critic)`, **Then** all discovered LlmAgents execute through AgentExecutor.

2. **Given** a workflow evolution with a critic, **When** the critic evaluates workflow outputs, **Then** the critic uses the same executor instance as the workflow agents.

---

### Edge Cases

- What happens when an executor is provided but one agent fails mid-execution? Session state should be properly cleaned up.
- How does the system handle agents with conflicting session requirements? Each agent should get isolated sessions unless explicitly shared via `existing_session_id`.
- What happens when `evolve_workflow()` discovers zero LlmAgents? The existing error handling should remain unchanged.
- How does timeout handling work across multiple agents? Each agent execution should respect its own timeout through the executor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `MultiAgentAdapter` MUST accept an optional `executor` parameter of type `AgentExecutorProtocol | None`
- **FR-002**: When an executor is provided to `MultiAgentAdapter`, all agent executions MUST use that executor
- **FR-003**: `evolve_group()` MUST create an `AgentExecutor` instance when one is not provided
- **FR-004**: `evolve_group()` MUST pass the executor to `MultiAgentAdapter`, `CriticScorer`, and reflection functions
- **FR-005**: `CriticScorer` instances created within `evolve_group()` MUST receive the same executor instance
- **FR-006**: Reflection functions created via `create_adk_reflection_fn()` in `evolve_group()` MUST receive the executor
- **FR-007**: `evolve_workflow()` MUST inherit executor support automatically by delegating to `evolve_group()`
- **FR-008**: All agent executions MUST log `uses_executor=True` when using the unified execution path
- **FR-009**: The system MUST maintain backward compatibility when no executor is explicitly provided

### Key Entities

- **AgentExecutor**: The unified execution adapter that manages session lifecycle, timeout handling, and output extraction for any ADK agent type.
- **MultiAgentAdapter**: The adapter that coordinates execution of multiple agents together, now extended to use AgentExecutor.
- **ExecutorProtocol**: The protocol interface that defines the executor contract, ensuring consistent behavior across implementations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All multi-agent evolution scenarios use the unified executor (verified by log inspection showing `uses_executor=True` for every agent execution)
- **SC-002**: Existing multi-agent tests continue to pass without modification (backward compatibility verified)
- **SC-003**: New integration tests demonstrate executor sharing across generator, critic, and reflection agents in multi-agent context
- **SC-004**: `evolve_workflow()` automatically benefits from unified execution without additional code changes
- **SC-005**: Example scripts are updated to document the unified execution path for multi-agent scenarios

## Assumptions

- The `AgentExecutor` from issue #135/PR #138 is already implemented and available in the codebase
- The existing `MultiAgentAdapter` structure can be extended without breaking changes
- `evolve_workflow()` delegates to `evolve_group()` internally (no separate implementation needed)

## Dependencies

- Issue #135 / PR #138: Unified AgentExecutor implementation (must be merged first)
- Issue #136: Remove legacy execution paths (can be done after this feature)

## Out of Scope

- Changes to single-agent `evolve()` API (already has executor support)
- Changes to `AgentExecutor` implementation (use as-is from PR #138)
- Changes to workflow discovery logic in `evolve_workflow()`
