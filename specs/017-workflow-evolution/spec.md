# Feature Specification: Workflow Agent Evolution

**Feature Branch**: `017-workflow-evolution`  
**Created**: January 12, 2026  
**Status**: Draft  
**Input**: GitHub Issue #15 - Implement workflow-as-student detection (evolve_workflow)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evolve Sequential Workflow Pipeline (Priority: P1)

As a developer using gepa-adk, I want to optimize a SequentialAgent pipeline containing multiple LlmAgents so that all sub-agents receive improved instructions while the workflow structure remains intact.

**Why this priority**: SequentialAgent is the most common workflow pattern (step-by-step pipelines), and this represents the core use case for workflow evolution. Without this capability, users must manually evolve each agent individually, losing the workflow context.

**Independent Test**: Can be fully tested by creating a SequentialAgent with 2-3 LlmAgent sub-agents, calling `evolve_workflow()`, and verifying all sub-agents have updated instructions while the sequential structure is preserved.

**Acceptance Scenarios**:

1. **Given** a SequentialAgent containing 3 LlmAgent sub-agents with initial instructions, **When** I call `evolve_workflow()` with a training dataset, **Then** all 3 sub-agents have evolved instructions and the SequentialAgent structure is unchanged.

2. **Given** a SequentialAgent with mixed sub-agent types (LlmAgent and non-LlmAgent such as nested workflow agents or custom BaseAgent subclasses), **When** I call `evolve_workflow()`, **Then** only the LlmAgent sub-agents are evolved and other agents remain untouched.

3. **Given** a SequentialAgent with no LlmAgent sub-agents, **When** I call `evolve_workflow()`, **Then** a clear error is raised indicating no evolvable agents were found.

---

### User Story 2 - Detect and Classify Workflow Agent Types (Priority: P1)

As a developer, I want the system to automatically detect whether an agent is a workflow type (SequentialAgent, LoopAgent, or ParallelAgent) so that I can use the appropriate evolution strategy without manual type checking.

**Why this priority**: Type detection is foundational—all workflow evolution depends on correctly identifying workflow agents versus LlmAgents. This enables automatic routing to the correct evolution path.

**Independent Test**: Can be tested by passing various agent types to a detection function and verifying correct classification for each workflow type and LlmAgent.

**Acceptance Scenarios**:

1. **Given** a SequentialAgent instance, **When** I check if it's a workflow agent, **Then** it returns true.

2. **Given** a LoopAgent instance, **When** I check if it's a workflow agent, **Then** it returns true.

3. **Given** a ParallelAgent instance, **When** I check if it's a workflow agent, **Then** it returns true.

4. **Given** an LlmAgent instance, **When** I check if it's a workflow agent, **Then** it returns false.

---

### User Story 3 - Recursively Find Nested LlmAgents (Priority: P2)

As a developer with complex nested workflows, I want the system to recursively discover all LlmAgents within nested workflow structures so that deeply nested agents can also be evolved.

**Why this priority**: Nested workflows are common in advanced use cases (e.g., a SequentialAgent containing a ParallelAgent with multiple LlmAgents). This extends the core functionality to handle real-world complexity.

**Independent Test**: Can be tested by creating a workflow with 3+ levels of nesting and verifying all LlmAgents at each level are discovered.

**Acceptance Scenarios**:

1. **Given** a SequentialAgent containing a LoopAgent that contains 2 LlmAgents, **When** I search for LlmAgents, **Then** both nested LlmAgents are found.

2. **Given** a ParallelAgent containing 3 branches, each with an LlmAgent, **When** I search for LlmAgents, **Then** all 3 LlmAgents are found.

3. **Given** a deeply nested workflow (5 levels deep), **When** I search with default max_depth=5, **Then** all LlmAgents up to depth 5 are found.

4. **Given** a nested workflow 7 levels deep, **When** I search with max_depth=3, **Then** only LlmAgents within the first 3 levels are found.

---

### User Story 4 - Evolve LoopAgent Workflows (Priority: P2)

As a developer using LoopAgent for iterative processes, I want to evolve the LlmAgents within a loop so that iterative workflows benefit from optimized instructions.

**Why this priority**: LoopAgent handles retry/iteration patterns. Evolving loop sub-agents improves reliability of iterative processes.

**Independent Test**: Can be tested by creating a LoopAgent with LlmAgent sub-agents and verifying evolution completes while loop configuration is preserved.

**Acceptance Scenarios**:

1. **Given** a LoopAgent with 2 LlmAgent sub-agents, **When** I call `evolve_workflow()`, **Then** both sub-agents have evolved instructions and the loop configuration remains intact.

---

### User Story 5 - Evolve ParallelAgent Workflows (Priority: P2)

As a developer using ParallelAgent for concurrent processing, I want to evolve all parallel branch agents simultaneously so that parallel workflows receive coordinated improvements.

**Why this priority**: ParallelAgent enables concurrent execution. All parallel branches should be evolved together to maintain coordination.

**Independent Test**: Can be tested by creating a ParallelAgent with multiple LlmAgent branches and verifying all are evolved.

**Acceptance Scenarios**:

1. **Given** a ParallelAgent with 4 parallel LlmAgent branches, **When** I call `evolve_workflow()`, **Then** all 4 branches have evolved instructions.

---

### Edge Cases

- What happens when a workflow contains zero LlmAgents? → Clear error message indicating no evolvable agents found.
- How does the system handle circular references in nested workflows? → Depth limiting prevents infinite recursion; max_depth parameter controls traversal.
- What happens if max_depth is set to 0? → No agents are found (immediate return at depth check).
- How are non-agent objects in sub_agents handled? → Gracefully skipped during traversal.
- What happens if evolution fails for one agent in a workflow? → Fail-fast: evolution stops and raises EvolutionError with context about which agent failed. No partial results returned.
- What happens if LlmAgent.instruction is an InstructionProvider (callable) instead of string? → Skip with warning; only string instructions are evolvable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect whether an agent is a workflow type (SequentialAgent, LoopAgent, or ParallelAgent).
- **FR-002**: System MUST recursively find all LlmAgent instances within a workflow structure.
- **FR-003**: System MUST respect a configurable maximum depth (default: 5) when traversing nested workflows.
- **FR-004**: System MUST preserve the original workflow structure after evolution (agent hierarchy unchanged).
- **FR-005**: System MUST evolve all discovered LlmAgents using the existing `evolve_group` function.
- **FR-006**: System MUST raise a clear error when no LlmAgents are found in a workflow.
- **FR-007**: System MUST support all three workflow types: SequentialAgent, LoopAgent, and ParallelAgent.
- **FR-008**: System MUST accept an optional critic agent for the evolution process.
- **FR-009**: System MUST accept an optional EvolutionConfig for customizing evolution parameters.
- **FR-010**: System MUST use shared session mode when evolving workflow agents (to maintain workflow context).

### Key Entities

- **Workflow Agent**: A container agent (SequentialAgent, LoopAgent, ParallelAgent) that orchestrates sub-agents. Has a `sub_agents` collection.
- **LlmAgent**: A language model agent with instructions that can be evolved. The target of optimization within workflows.
- **MultiAgentEvolutionResult**: The output of the evolution process containing evolved_instructions dict, scores, and iteration history.
- **EvolutionConfig**: Configuration parameters controlling the evolution process (generations, population size, etc.).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can evolve a 3-agent SequentialAgent workflow in a single function call (vs. 3 separate calls manually).
- **SC-002**: All LlmAgents in a workflow with up to 5 levels of nesting are discovered and evolved.
- **SC-003**: Workflow structure (agent hierarchy and configuration) is 100% preserved after evolution.
- **SC-004**: Evolution time for a workflow is comparable to evolving individual agents (within 10% overhead for traversal).
- **SC-005**: Users receive a clear, actionable error message when attempting to evolve a workflow with no LlmAgents.

## Assumptions

- The existing `evolve_group` function is available and working (dependency on issue #14).
- All agents inherit `sub_agents: list[BaseAgent]` from BaseAgent (google-adk 1.22.0, base_agent.py:133).
- Type detection uses `isinstance()` for SequentialAgent/LoopAgent/ParallelAgent (not sub_agents presence).
- LlmAgent.instruction is `Union[str, InstructionProvider]` (llm_agent.py:203); only string instructions are evolvable.
- The `share_session=True` parameter in `evolve_group` enables proper workflow context during evaluation.
