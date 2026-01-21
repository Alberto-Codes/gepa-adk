# Feature Specification: Multi-Agent Component Routing

**Feature Branch**: `166-multi-agent-routing`
**Created**: 2026-01-20
**Status**: Draft
**Input**: GitHub Issue #166: Update MultiAgentAdapter for per-agent component routing

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Route Components to Correct Agents (Priority: P1)

As a GEPA developer, I want to evolve different components on different agents in multi-agent scenarios, so that I can optimize specific parts of each agent independently (e.g., evolve generator's output_schema while simultaneously tuning critic's configuration).

**Why this priority**: This is the core capability of the feature - without component routing, the entire feature has no value. It enables the primary use case of per-agent component optimization.

**Independent Test**: Can be fully tested by providing a multi-agent setup with per-agent component mappings and verifying that evolution candidates are applied to the correct agent for each component.

**Acceptance Scenarios**:

1. **Given** agents "generator" and "critic" are configured, **When** evolution applies a candidate with `generator.instruction` and `critic.output_schema`, **Then** the instruction update is applied only to the generator agent and the output_schema update is applied only to the critic agent.

2. **Given** a components mapping specifying `{"generator": ["instruction", "output_schema"], "refiner": ["instruction"]}`, **When** candidates are generated, **Then** each candidate contains qualified names using dot notation (e.g., `generator.instruction`).

3. **Given** per-agent component configuration is provided, **When** the evolution process runs, **Then** each agent's evolved components are tracked and returned with their qualified names in the result.

---

### User Story 2 - Restore All Agents After Evaluation (Priority: P1)

As a GEPA developer, I want all agents to be restored to their original state after each candidate evaluation, so that subsequent candidates are evaluated against the original configuration, not accumulated modifications.

**Why this priority**: This is critical for correctness - without proper restoration, evolution results would be invalid. It shares P1 with routing because both are essential for correct operation.

**Independent Test**: Can be tested by applying a candidate to multiple agents, completing evaluation, then verifying each agent's components match their original values.

**Acceptance Scenarios**:

1. **Given** agents have been modified by applying a candidate, **When** evaluation completes, **Then** all agents are restored to their exact original state before the candidate was applied.

2. **Given** multiple agents with different components have been modified, **When** restoration is triggered, **Then** each agent's original values are correctly restored independently.

3. **Given** an error occurs during evaluation, **When** the error is caught, **Then** all agents are still restored to prevent state corruption.

---

### User Story 3 - Track Originals Per Agent (Priority: P2)

As a GEPA developer, I want the system to track original values for each agent-component combination, so that restoration can correctly revert any combination of agents and components.

**Why this priority**: While essential for the feature to work, this is an internal mechanism that supports User Stories 1 and 2. It has value only in conjunction with routing and restoration.

**Independent Test**: Can be tested by inspecting the originals dictionary after applying candidates to verify it contains the correct agent.component keys with their original values.

**Acceptance Scenarios**:

1. **Given** multiple agents with different components, **When** `_apply_candidate` is called with a multi-agent candidate, **Then** the originals dictionary tracks `agent.component` as keys mapped to their original values.

2. **Given** a populated originals dictionary, **When** `_restore_agents` is called, **Then** all entries in the originals dictionary are used to restore the corresponding agent-component pairs.

---

### Edge Cases

- What happens when a qualified name references a non-existent agent? The system must raise a clear error identifying the invalid agent name.
- What happens when a qualified name references a non-existent component type? The system must raise a clear error identifying the unsupported component.
- How does the system handle empty component mappings for an agent? Agents with no components in the mapping should be ignored during evolution.
- What happens when an agent appears in the agents dict but not in the components mapping? The system MUST require explicit component configuration for all agents (fail-fast, no defaults).
- How does the system handle restoration when a handler's restore operation fails? The system must attempt to restore remaining agents and report all failures.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST route component updates to the correct agent based on qualified component names (using dot notation per ADR-012, e.g., `generator.instruction`).
- **FR-002**: System MUST use `ComponentSpec` from `gepa_adk.domain.types` for parsing and constructing qualified component names.
- **FR-003**: System MUST track original values for each agent-component combination before applying candidates.
- **FR-004**: System MUST restore all agents to their original state after each candidate evaluation completes, regardless of success or failure.
- **FR-005**: System MUST require per-agent component configuration via a `components: dict[str, list[str]]` parameter mapping agent names to their evolvable components.
- **FR-006**: System MUST require agents as `dict[str, LlmAgent]` (named agents); list input is not supported.
- **FR-007**: System MUST require all agents in the agents dict to have corresponding entries in the components mapping (fail-fast validation).
- **FR-008**: System MUST return evolved components with their qualified names (e.g., `generator.instruction`) in the evolution result.
- **FR-009**: System MUST validate that all agent names in the components mapping exist in the agents dict and raise a clear error for mismatches.
- **FR-010**: System MUST validate that all specified component types have registered handlers and raise a clear error for unknown components.

### Key Entities

- **QualifiedComponentName**: A string identifier combining agent name and component name with dot separator (e.g., `generator.instruction`). Type-safe representation per ADR-012.
- **ComponentSpec**: A structured representation of a qualified name with `agent` and `component` fields, providing parsing and construction utilities.
- **MultiAgentAdapter**: The adapter responsible for managing multiple agents and routing component operations to the correct agent.
- **Originals Dictionary**: A mapping of qualified component names to their original values, used for restoration after evaluation.
- **Components Mapping**: A configuration mapping agent names to lists of component names to be evolved for that agent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can evolve components on 3+ agents simultaneously in a single evolution run with each agent receiving only its designated component updates.
- **SC-002**: All agents are restored to original state within the same evolution step, with zero component state leakage between candidate evaluations.
- **SC-003**: Clear error messages identify the specific agent or component causing validation failures, enabling developers to fix configuration issues on first attempt.
- **SC-004**: Evolution results contain all evolved components accessible by their qualified names, allowing developers to retrieve and apply results to specific agents.

## Assumptions

- ADR-012 decisions from issue #165 are finalized and `ComponentSpec`/`QualifiedComponentName` types are available in `gepa_adk.domain.types`.
- Issue #164 (generate_content_config component) is completed, providing a third component type for testing diverse multi-agent scenarios.
- Component handlers follow a consistent interface for apply/restore operations.
- The existing `get_handler` function can retrieve handlers by component name string.
