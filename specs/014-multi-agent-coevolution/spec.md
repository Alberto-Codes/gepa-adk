# Feature Specification: Multi-Agent Co-Evolution (evolve_group)

**Feature Branch**: `014-multi-agent-coevolution`  
**Created**: January 11, 2026  
**Status**: Draft  
**Input**: User description: "Implement multi-agent co-evolution (evolve_group) - evolve multiple agents together to optimize generator + critic + validator systems holistically"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evolve Multiple Agents Together (Priority: P1)

As a gepa-adk user, I want to evolve multiple agents together so that I can optimize a generator + critic + validator pipeline as a unified system rather than individually.

**Why this priority**: This is the core feature - without multi-agent evolution, the entire feature has no value. Users need to be able to pass multiple agents and get all their instructions optimized together.

**Independent Test**: Can be fully tested by creating three simple agents (generator, critic, validator), calling `evolve_group()`, and verifying all three instructions are returned in the result.

**Acceptance Scenarios**:

1. **Given** a generator, critic, and validator agent, **When** I call `evolve_group(agents=[generator, critic, validator], primary="validator")`, **Then** all three agents' instructions are evolved and returned in the result
2. **Given** multiple agents with different instructions, **When** evolution completes, **Then** the optimization targets the primary agent's score while co-evolving supporting agents
3. **Given** an `evolve_group()` call, **When** no critic is provided but the primary agent has an output schema, **Then** the system uses schema-based scoring automatically

---

### User Story 2 - Share Session State Between Agents (Priority: P2)

As a gepa-adk user, I want agents to share session state during execution so that later agents in the pipeline can access outputs and context from earlier agents.

**Why this priority**: Session sharing enables sophisticated multi-agent workflows where agents build upon each other's work. Without this, agents would operate in isolation, limiting the value of co-evolution.

**Independent Test**: Can be tested by creating two agents where the second agent references output from the first, running with `share_session=True`, and verifying the second agent receives the first agent's output.

**Acceptance Scenarios**:

1. **Given** `share_session=True`, **When** agents execute in sequence, **Then** later agents can access earlier agents' state and outputs
2. **Given** `share_session=False`, **When** agents execute, **Then** each agent operates with independent session state
3. **Given** a shared session, **When** an earlier agent produces output, **Then** subsequent agents can reference that output in their processing

---

### User Story 3 - Retrieve All Evolved Instructions (Priority: P1)

As a gepa-adk user, I want to retrieve all evolved instructions for every agent after evolution completes so that I can update my agents with their optimized instructions.

**Why this priority**: This is essential for using the evolution results - users must be able to access the evolved instructions to apply them to their agents.

**Independent Test**: Can be tested by calling `evolve_group()` with multiple agents and verifying `result.evolved_instructions` is a dictionary keyed by agent name containing each agent's evolved instruction.

**Acceptance Scenarios**:

1. **Given** multiple agents evolved, **When** I get the result, **Then** `result.evolved_instructions` is a dictionary with all agents' names as keys
2. **Given** three agents named "generator", "critic", "validator", **When** evolution completes, **Then** I can access `result.evolved_instructions["generator"]`, `result.evolved_instructions["critic"]`, and `result.evolved_instructions["validator"]`
3. **Given** evolution results, **When** I examine the result object, **Then** it also includes `original_score` and `final_score` to measure improvement

---

### Edge Cases

- What happens when an empty agents list is provided? System should raise a validation error.
- What happens when the primary agent name doesn't match any agent in the list? System should raise a validation error.
- How does the system handle when one agent fails during execution? System should handle gracefully with appropriate error reporting.
- What happens when agents have duplicate names? System should raise a validation error.
- What happens when share_session=True but agents don't produce compatible outputs? System should execute but later agents may receive empty/null state from earlier agents.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a list of agents to evolve together
- **FR-002**: System MUST accept a `primary` parameter specifying which agent's output is used for scoring
- **FR-003**: System MUST accept a `trainset` parameter containing training examples for evaluation
- **FR-004**: System MUST accept an optional `critic` agent for scoring when the primary agent lacks an output schema
- **FR-005**: System MUST accept a `share_session` parameter (default: True) controlling whether agents share execution state
- **FR-006**: System MUST accept an optional `config` parameter for evolution configuration
- **FR-007**: System MUST build a seed candidate containing all agent instructions keyed by `{agent.name}_instruction`
- **FR-008**: System MUST return an evolution result containing `evolved_instructions` as a dictionary keyed by agent name
- **FR-009**: System MUST return `original_score` and `final_score` in the result to measure improvement
- **FR-010**: System MUST validate that the `primary` agent name exists in the provided agents list
- **FR-011**: System MUST validate that all agents have unique names
- **FR-012**: System MUST use critic-based scoring when a critic agent is provided, otherwise use schema-based scoring

### Key Entities

- **Agent**: An agent with a name, instruction, and optional output_schema
- **EvolutionResult**: Contains evolved_instructions (dict), original_score, final_score, and evolution metadata
- **MultiAgentAdapter**: Orchestrates execution of multiple agents, handles session sharing, and provides scoring interface
- **Seed Candidate**: Dictionary mapping `{agent_name}_instruction` to each agent's current instruction text

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can evolve 3+ agents together in a single `evolve_group()` call and retrieve all evolved instructions
- **SC-002**: Session state sharing enables later agents to access earlier agents' outputs when `share_session=True`
- **SC-003**: Evolution produces measurable score improvement (final_score > original_score) for primary agent on representative test cases
- **SC-004**: Users can apply evolved instructions to their original agents and observe improved end-to-end pipeline performance
- **SC-005**: Multi-agent evolution completes within acceptable time bounds relative to single-agent evolution (linear scaling with agent count)

## Assumptions

- Agents follow a consistent interface with `name` and `instruction` attributes
- The existing evolution engine and configuration can be reused with the new multi-agent adapter
- Critic-based scoring is available for scoring agent outputs
- Agents execute sequentially in the order provided when session sharing is enabled
- The trainset format is compatible with multi-agent evaluation workflows

## Dependencies

- **#6**: AsyncGEPAEngine - Required for running the evolution loop
- **#8**: ADK Adapter - Required for agent execution interface
- **#9**: CriticScorer - Required for scoring when critic agent is provided
