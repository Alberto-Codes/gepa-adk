# Feature Specification: Execute Workflows As-Is (Preserve Structure)

**Feature Branch**: `215-workflow-structure`
**Created**: 2026-01-22
**Status**: Draft
**Input**: User description: "gh issue 215 - Execute workflows as-is instead of flattening to SequentialAgent"
**GitHub Issue**: #215

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LoopAgent Iteration Preservation (Priority: P1)

As a gepa-adk user with a LoopAgent, I want the loop to execute N iterations during evaluation, so that I can evolve refinement agents that improve through iteration.

**Why this priority**: LoopAgents are designed for iterative refinement workflows (e.g., draft-critique-revise cycles). Without preserved iterations, users cannot evolve agents that benefit from multi-pass processing, which is a core use case for refinement-based workflows.

**Independent Test**: Can be fully tested by creating a LoopAgent with max_iterations=3, running evolve_workflow, and verifying that the inner agent executes exactly 3 times per training example.

**Acceptance Scenarios**:

1. **Given** a LoopAgent configured with max_iterations=3, **When** evolve_workflow is called, **Then** the inner agent executes 3 times per training example
2. **Given** a LoopAgent executing, **When** all iterations complete, **Then** the final iteration output is used for scoring
3. **Given** a LoopAgent executing, **When** iterations run, **Then** all iteration outputs are captured in the execution trajectory

---

### User Story 2 - ParallelAgent Concurrent Execution (Priority: P1)

As a user with a ParallelAgent, I want parallel execution to be preserved during evaluation, so that my agents run concurrently as designed.

**Why this priority**: ParallelAgents enable concurrent research/analysis patterns (e.g., multiple researchers gathering information simultaneously). Flattening to sequential execution changes behavior and defeats the purpose of parallel design.

**Independent Test**: Can be fully tested by creating a ParallelAgent with two sub-agents, running evolve_workflow, and verifying both agents execute concurrently with their outputs available in session state.

**Acceptance Scenarios**:

1. **Given** a ParallelAgent with sub_agents=[ResearcherA, ResearcherB], **When** evolve_workflow is called, **Then** ResearcherA and ResearcherB execute concurrently
2. **Given** parallel execution completes, **When** results are retrieved, **Then** both agent outputs are available in session state
3. **Given** a ParallelAgent with a designated primary agent, **When** scoring occurs, **Then** the primary agent's output is used for scoring

---

### User Story 3 - Nested Workflow Structure Preservation (Priority: P2)

As a user with nested workflows, I want the full structure preserved during evaluation, so that the behavior matches my intended design.

**Why this priority**: Complex workflows often combine Sequential, Parallel, and Loop patterns. Preserving structure ensures the evolved behavior matches the designed data flow and execution order.

**Independent Test**: Can be fully tested by creating a nested workflow like Sequential([Parallel([A, B]), Synthesizer, Writer]), running evolve_workflow, and verifying the correct execution order with proper data flow between stages.

**Acceptance Scenarios**:

1. **Given** a nested workflow Sequential([Parallel([A, B]), Synthesizer, Writer]), **When** evolve_workflow is called, **Then** A and B run in parallel first
2. **Given** parallel stage completes, **When** Synthesizer runs, **Then** both parallel outputs are available to it
3. **Given** Synthesizer completes, **When** Writer runs, **Then** it produces the final output and that output is used for scoring

---

### Edge Cases

- What happens when a LoopAgent has max_iterations=0 or negative? System should handle gracefully with a warning or error.
- What happens when a ParallelAgent has only one sub-agent? System should still execute it correctly (effectively sequential).
- How does the system handle deeply nested workflows (e.g., 5+ levels deep)? Recursive cloning should handle arbitrary depth.
- What happens when an LlmAgent appears in multiple places in a workflow? Each instance should be independently cloned with its own instruction overrides.
- What happens when a workflow contains agent types not explicitly supported (custom BaseAgent subclasses)? System should pass through unknown agent types unchanged or raise a clear error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST preserve LoopAgent structure during workflow evolution, maintaining max_iterations configuration
- **FR-002**: System MUST execute LoopAgent inner agents the configured number of iterations per training example
- **FR-003**: System MUST preserve ParallelAgent structure during workflow evolution, maintaining concurrent execution semantics
- **FR-004**: System MUST execute ParallelAgent sub-agents concurrently (not sequentially)
- **FR-005**: System MUST preserve nested workflow structures of arbitrary depth during evolution
- **FR-006**: System MUST apply instruction overrides only to LlmAgent leaf nodes while preserving container agent configurations
- **FR-007**: System MUST store the original workflow structure (not just discovered agents) for accurate cloning
- **FR-008**: System MUST recursively clone workflows, preserving all agent-specific properties (e.g., max_iterations, sub_agents)
- **FR-009**: System MUST capture all iteration outputs in the execution trajectory for LoopAgents
- **FR-010**: System MUST use the final iteration output for scoring when evaluating LoopAgent workflows

### Key Entities

- **Workflow**: A composite agent structure that can contain SequentialAgent, LoopAgent, ParallelAgent, or LlmAgent nodes arranged hierarchically
- **LlmAgent**: A leaf-level agent with an instruction that can be evolved; receives instruction overrides from candidates
- **SequentialAgent**: A container agent that executes sub-agents in sequence; structure must be preserved during cloning
- **LoopAgent**: A container agent that executes a single inner agent N times; max_iterations must be preserved
- **ParallelAgent**: A container agent that executes sub-agents concurrently; parallel semantics must be preserved
- **Candidate**: A set of instruction overrides keyed by agent name (e.g., "AgentName.instruction" -> "new instruction text")

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: LoopAgents execute exactly the configured number of iterations (verifiable by trajectory inspection)
- **SC-002**: ParallelAgent sub-agents execute concurrently, not sequentially (verifiable by execution traces)
- **SC-003**: Nested workflows of at least 4 levels deep execute correctly with preserved structure
- **SC-004**: All existing evolve_workflow tests continue to pass (backward compatibility)
- **SC-005**: Users can evolve iterative refinement workflows without manual workarounds

## Assumptions

- The ADK Runner properly supports LoopAgent and ParallelAgent execution semantics
- Instruction overrides only apply to LlmAgent types (container agents don't have evolvable instructions)
- The existing candidate key format "AgentName.instruction" is preserved
- Dependency on issue #213 (output extraction fix) is resolved before this feature is implemented

## Out of Scope

- Evolving container agent properties (e.g., dynamically changing max_iterations during evolution)
- Custom BaseAgent subclass support beyond the four core types (LlmAgent, SequentialAgent, LoopAgent, ParallelAgent)
- Distributed parallel execution across multiple processes/machines
