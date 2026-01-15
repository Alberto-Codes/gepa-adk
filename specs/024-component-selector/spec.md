# Feature Specification: Multi-Component Evolution with Component Selectors

**Feature Branch**: `024-component-selector`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Add multi-component evolution with component selector strategies (GitHub Issue #56)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Round-Robin Component Evolution (Priority: P1)

As a gepa-adk user evolving candidates with multiple components (instruction, output_schema, per-agent prompts), I want the system to automatically cycle through components each iteration so that all components receive balanced evolution attention without manual intervention.

**Why this priority**: This is the core capability that enables schema evolution and ensures no single component dominates the evolution process. Without balanced component selection, users would need to manually manage which components evolve, reducing automation benefits.

**Independent Test**: Can be fully tested by running evolution for multiple iterations on a multi-component candidate and verifying that different components are mutated in sequence, delivering predictable and reproducible evolution behavior.

**Acceptance Scenarios**:

1. **Given** a candidate with components `instruction` and `output_schema`, and component selector set to "round_robin", **When** evolution runs for 4 iterations, **Then** iteration 1 mutates `instruction`, iteration 2 mutates `output_schema`, iteration 3 mutates `instruction` (cycles back), and iteration 4 mutates `output_schema`.

2. **Given** a candidate with only `instruction` component, **When** evolution runs with any selector, **Then** `components_to_update` contains only `instruction` each iteration (single component behavior preserved).

3. **Given** a candidate with three components (`instruction`, `output_schema`, `context`), and round-robin selector, **When** evolution runs for 6 iterations, **Then** each component is mutated exactly twice in sequential order.

---

### User Story 2 - All-Components Simultaneous Evolution (Priority: P2)

As a user who wants aggressive evolution of all components at once, I want a selector that proposes mutations to all components in a single iteration so that I can explore broader solution spaces faster when evolution budget is limited.

**Why this priority**: Provides an alternative strategy for users who prefer comprehensive changes per iteration over incremental component-by-component evolution. Useful for exploratory phases or when components are tightly coupled.

**Independent Test**: Can be fully tested by configuring all-components selector and verifying that a single evolution iteration proposes changes to every component in the candidate.

**Acceptance Scenarios**:

1. **Given** a candidate with components `instruction` and `output_schema`, and component selector set to "all", **When** evolution proposes a mutation, **Then** both `instruction` and `output_schema` are included in the mutation proposal.

2. **Given** a candidate with five components, and all-components selector, **When** evolution runs for 1 iteration, **Then** all five components are passed to the reflection process together.

---

### User Story 3 - Multi-Agent Workflow Evolution (Priority: P2)

As a multi-agent workflow user, I want the component selector to recognize and cycle through per-agent instruction components (e.g., `generator_instruction`, `critic_instruction`) so that the entire workflow improves rather than just the primary agent.

**Why this priority**: Multi-agent workflows are a key use case for gepa-adk. Without per-agent component selection, only the primary agent evolves while secondary agents remain static, limiting overall workflow improvement.

**Independent Test**: Can be fully tested by creating a multi-agent candidate with distinct per-agent instruction components and verifying that round-robin selection cycles through each agent's components.

**Acceptance Scenarios**:

1. **Given** a multi-agent candidate with `generator_instruction` and `critic_instruction`, and component selector set to "round_robin", **When** evolution runs for 2 iterations, **Then** iteration 1 mutates `generator_instruction` and iteration 2 mutates `critic_instruction`.

2. **Given** a multi-agent candidate with both a generic `instruction` alias and agent-specific instructions, **When** evolution detects this configuration, **Then** the generic `instruction` alias is excluded to prevent double-mutation when other instruction components exist.

3. **Given** a workflow with 3 agents (generator, critic, refiner) each with their own instruction component, **When** round-robin evolution runs for 6 iterations, **Then** each agent's instruction is mutated exactly twice.

---

### User Story 4 - Selector Configuration via API (Priority: P3)

As a developer integrating gepa-adk, I want to specify the component selector strategy when calling the evolution functions so that I can choose the appropriate selection behavior for my use case.

**Why this priority**: Enables users to explicitly control selection behavior. While defaults cover most cases, power users need direct configuration access.

**Independent Test**: Can be fully tested by calling evolution functions with different selector configurations and verifying the expected selection behavior is applied.

**Acceptance Scenarios**:

1. **Given** I call `evolve()` with `component_selector="round_robin"`, **When** evolution runs, **Then** round-robin selection behavior is applied.

2. **Given** I call `evolve()` with `component_selector="all"`, **When** evolution runs, **Then** all-components selection behavior is applied.

3. **Given** I call `evolve()` without specifying `component_selector`, **When** evolution runs, **Then** the default round-robin behavior is applied.

---

### Edge Cases

- What happens when a candidate has zero components? System should raise an appropriate error indicating no components are available for evolution.
- How does the system handle component removal during evolution (component exists in iteration 1 but not iteration 3)? System should skip removed components and continue cycling through available components.
- What happens if round-robin iteration counter exceeds the number of components many times over? System should use modulo arithmetic to cycle correctly without overflow.
- How does the selector behave when components are dynamically added mid-evolution? New components should be included in the next selection cycle.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a round-robin component selection strategy that cycles through available components sequentially across iterations.
- **FR-002**: System MUST support an all-components selection strategy that selects all components for mutation in each iteration.
- **FR-003**: System MUST default to round-robin selection when no selector is explicitly configured.
- **FR-004**: System MUST preserve single-component behavior (selecting that one component every iteration) when candidates have only one component.
- **FR-005**: System MUST allow users to specify the component selector strategy via the public evolution functions (`evolve`, `evolve_group`, `evolve_workflow`).
- **FR-006**: System MUST build the component list from candidate keys for multi-agent candidates (e.g., `generator_instruction`, `critic_instruction`).
- **FR-007**: System MUST exclude generic instruction aliases when more specific per-agent instruction components exist to prevent double-mutation.
- **FR-008**: System MUST maintain iteration state to ensure reproducible round-robin ordering across evolution runs.
- **FR-009**: System MUST handle edge cases gracefully: zero components (error), removed components (skip), added components (include in next cycle).

### Key Entities

- **Component**: A named element of a candidate that can be mutated during evolution (e.g., `instruction`, `output_schema`, `generator_instruction`). Identified by string key.
- **Component Selector**: A strategy that determines which component(s) to mutate in a given iteration. Takes the list of available components and iteration number as input, returns the subset to mutate.
- **Candidate**: An entity being evolved that contains one or more components. May represent a single agent or a multi-agent workflow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Multi-component candidates evolve all components within N iterations where N equals the number of components (round-robin achieves full coverage).
- **SC-002**: Users can configure component selection strategy with a single parameter in evolution function calls.
- **SC-003**: Multi-agent workflows show improvement across all agents' metrics, not just the primary agent, after sufficient evolution iterations.
- **SC-004**: Component selection is deterministic and reproducible - same candidate, same iteration number, same selector always produces same component selection.
- **SC-005**: Single-component candidates continue to work identically to current behavior with no configuration changes required.
- **SC-006**: Evolution of a 3-component candidate for 12 iterations results in exactly 4 mutations per component when using round-robin selection.

## Assumptions

- Upstream GEPA's `RoundRobinReflectionComponentSelector` and `AllReflectionComponentSelector` provide reference behavior that this feature should mirror.
- Existing adapters already accept `components_to_update` parameter, so the core mutation infrastructure supports multi-component updates.
- Component names follow a consistent naming convention (snake_case with optional agent prefix).
- Users running multi-agent workflows have meaningful per-agent instruction components defined in their candidates.

## Dependencies

- Relies on existing `make_reflective_dataset` and `propose_new_texts` adapter methods that accept `components_to_update` parameter.
- Must integrate with `AsyncGEPAEngine` mutation flow which currently hardcodes component selection.
