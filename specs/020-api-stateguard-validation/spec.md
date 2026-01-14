# Feature Specification: API StateGuard Validation

**Feature Branch**: `020-api-stateguard-validation`  
**Created**: January 13, 2026  
**Status**: Draft  
**Input**: User description: "[Tech Debt] Implement StateGuard validation in public API - Wire the existing StateGuard utility into the public API evolve() and evolve_sync() functions so that state injection tokens are protected during instruction evolution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Token Repair During Evolution (Priority: P1)

As a gepa-adk user running instruction evolution, I want the public API to automatically repair missing ADK state tokens when a `state_guard` is provided, so that my evolved instructions don't silently break ADK state injection.

**Why this priority**: This is the core safety feature. Without automatic token repair, evolved instructions could lose critical placeholders (like `{user_id}` or `{context}`) that ADK needs for state injection at runtime. This would cause runtime failures that are hard to debug.

**Independent Test**: Can be fully tested by providing a StateGuard with required tokens, running evolution, and verifying that if the evolved instruction is missing any required tokens, they are automatically appended before the result is returned.

**Acceptance Scenarios**:

1. **Given** I call `evolve(agent, trainset, state_guard=StateGuard(required_tokens=["{user_id}"]))`, **When** the evolved instruction is missing `{user_id}`, **Then** the token is automatically appended to the evolved instruction in the result.
2. **Given** I call `evolve_sync()` with a state_guard parameter, **When** evolution produces an instruction missing required tokens, **Then** the sync wrapper applies the same token repair as the async version.
3. **Given** I provide a state_guard with `repair_missing=False`, **When** tokens are missing from the evolved instruction, **Then** no automatic repair is applied (explicit opt-out honored).

---

### User Story 2 - Unauthorized Token Escaping (Priority: P2)

As a gepa-adk user, I want the public API to escape any unauthorized tokens introduced by the LLM during evolution, so that they don't accidentally trigger undefined ADK state injection behavior.

**Why this priority**: While less common than missing tokens, unauthorized tokens (like `{malicious}`) could cause undefined behavior or security issues if passed to ADK. This is a secondary safety mechanism.

**Independent Test**: Can be fully tested by running evolution where the LLM introduces new tokens not in the original instruction, and verifying those tokens are escaped with double braces (`{{token}}`).

**Acceptance Scenarios**:

1. **Given** I call `evolve()` with a state_guard, **When** the evolved instruction contains a new `{injected}` token not in the original, **Then** it is escaped to `{{injected}}`.
2. **Given** I provide a state_guard with `escape_unauthorized=False`, **When** new unauthorized tokens appear, **Then** they are NOT escaped (explicit opt-out honored).
3. **Given** a new token that matches a token in the `required_tokens` list, **When** state_guard validates, **Then** it is NOT escaped (authorized addition).

---

### User Story 3 - StateGuard in Multi-Agent Evolution (Priority: P2)

As a gepa-adk user evolving multiple agents in a group, I want state_guard protection to apply to each agent's evolved instruction, so that all agents maintain proper state token handling.

**Why this priority**: Multi-agent evolution (`evolve_group`) processes multiple agents simultaneously. Without per-agent StateGuard validation, any of those agents could produce broken instructions.

**Independent Test**: Can be tested by calling `evolve_group()` with a state_guard and verifying that each agent's evolved instruction in the result has proper token handling applied.

**Acceptance Scenarios**:

1. **Given** I call `evolve_group(agents, trainset, state_guard=StateGuard(...))`, **When** any agent's evolved instruction is missing required tokens, **Then** those tokens are repaired for that agent.
2. **Given** multiple agents with different original instructions, **When** state_guard validates each, **Then** only tokens from each agent's respective original instruction are considered for repair.

---

### User Story 4 - StateGuard in Workflow Evolution (Priority: P3)

As a gepa-adk user evolving an ADK workflow (SequentialAgent/LoopAgent), I want state_guard protection to apply to the LlmAgents within the workflow, so that workflow state dependencies are preserved.

**Why this priority**: Workflow evolution targets LlmAgents within complex agent structures. These agents often rely on state tokens passed between workflow steps, making protection important but secondary to core API functionality.

**Independent Test**: Can be tested by calling `evolve_workflow()` with a state_guard and verifying the final instruction of each evolved LlmAgent has proper token handling.

**Acceptance Scenarios**:

1. **Given** I call `evolve_workflow(workflow_agent, trainset, state_guard=StateGuard(...))`, **When** an internal LlmAgent's evolved instruction loses required tokens, **Then** those tokens are repaired.

---

### Edge Cases

- What happens when `state_guard=None` is passed? → Evolution proceeds as before with no token validation (backward compatible).
- What happens when `state_guard` is provided but has empty `required_tokens`? → Only tokens from the original instruction are used for repair detection.
- How does StateGuard validation handle the original instruction reference? → The original instruction from the agent before evolution is used as the reference for token detection.
- What happens when evolution produces no improvement (returns original instruction)? → StateGuard validation still runs for consistency, but produces no changes since tokens are already present.
- What if the evolved instruction is identical to the original? → StateGuard validation still runs but produces no changes (same as above - validation is always applied when state_guard is provided).
- How does StateGuard interact with iteration history? → StateGuard validation is applied to the final evolved instruction only, not intermediate candidates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional `state_guard` parameter of type `StateGuard | None` in the `evolve()` function.
- **FR-002**: System MUST accept an optional `state_guard` parameter of type `StateGuard | None` in the `evolve_sync()` function.
- **FR-003**: When `state_guard` is provided and evolution completes, system MUST call `state_guard.validate(original_instruction, evolved_instruction)` to get the validated instruction.
- **FR-004**: System MUST use the validated instruction (from StateGuard) as the `evolved_instruction` in the returned `EvolutionResult`.
- **FR-005**: System MUST log when StateGuard validation is applied, including whether tokens were repaired or escaped.
- **FR-006**: When `state_guard=None` (default), system MUST skip all StateGuard validation and return the evolved instruction unchanged.
- **FR-007**: System MUST accept an optional `state_guard` parameter in `evolve_group()` and apply validation to each agent's evolved instruction.
- **FR-008**: System MUST accept an optional `state_guard` parameter in `evolve_workflow()` and apply validation to each internal LlmAgent's evolved instruction.
- **FR-009**: System MUST NOT modify the StateGuard instance (it is stateless and reusable).
- **FR-010**: System MUST handle the case where evolved instruction equals original instruction gracefully (validation produces no changes).

### Key Entities

- **StateGuard**: Existing utility class (`gepa_adk.utils.StateGuard`) that validates and repairs mutated instructions. Takes `required_tokens`, `repair_missing`, and `escape_unauthorized` configuration.
- **EvolutionResult**: The output of evolution containing `evolved_instruction`. After StateGuard validation, this field contains the validated/repaired instruction.
- **evolve()**: Primary async function in public API. Currently accepts `state_guard` parameter but has a TODO for implementation.
- **evolve_sync()**: Sync wrapper that calls `evolve()` internally. Will automatically benefit from StateGuard validation once wired in async version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users providing a `state_guard` parameter receive evolved instructions with all required tokens present 100% of the time.
- **SC-002**: Unauthorized tokens introduced by LLM mutation are escaped before being returned to the user.
- **SC-003**: Existing tests and functionality continue to work unchanged when `state_guard=None` (default behavior preserved).
- **SC-004**: StateGuard validation adds negligible overhead (sub-millisecond) since it operates only on final instruction strings.
- **SC-005**: All existing evolve API tests pass without modification.
- **SC-006**: New tests verify StateGuard integration with at least 90% coverage of the new code paths.

## Assumptions

- The existing `StateGuard` class is fully implemented and tested (per spec 013-state-guard and 015-state-guard-tokens).
- The `state_guard` parameter is already defined in the function signatures but marked with a TODO for implementation.
- The original agent instruction is available via `agent.instruction` at the start of evolution.
- StateGuard validation should be applied after evolution completes but before returning the result.
- Multi-agent and workflow evolution functions follow the same pattern as single-agent `evolve()`.
