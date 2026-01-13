# Feature Specification: Wire Adapters to AsyncReflectiveMutationProposer

**Feature Branch**: `016-wire-adapters-proposer`  
**Created**: 2026-01-12  
**Status**: Draft  
**Input**: User description: "Wire adapters to use AsyncReflectiveMutationProposer - enable ADKAdapter and MultiAgentAdapter to generate actual instruction mutations via LLM, with optional custom proposer injection"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ADKAdapter Delegates to Proposer (Priority: P1)

As a gepa-adk user, I want the ADKAdapter to generate actual instruction mutations via LLM, so that the evolution loop produces improved candidates instead of returning unchanged values.

**Why this priority**: This is the core functionality - without actual LLM-based mutation, the evolution loop cannot improve agent instructions. This enables the fundamental value proposition of GEPA.

**Independent Test**: Can be fully tested by creating an ADKAdapter with default proposer, calling `propose_new_texts()` with a reflective dataset, and verifying the returned text differs from the original (when feedback suggests changes).

**Acceptance Scenarios**:

1. **Given** an ADKAdapter with default proposer, **When** I call `propose_new_texts()` with a reflective dataset containing feedback, **Then** it delegates to `AsyncReflectiveMutationProposer.propose()` and returns mutated instruction text based on LLM reflection.

2. **Given** an ADKAdapter with default proposer, **When** I call `propose_new_texts()` with feedback indicating poor performance, **Then** the returned instruction addresses issues identified in the feedback.

---

### User Story 2 - MultiAgentAdapter Delegates to Proposer (Priority: P1)

As a gepa-adk user, I want the MultiAgentAdapter to generate actual instruction mutations via LLM for all agents in the pipeline, so that multi-agent co-evolution uses intelligent mutation instead of simple heuristics.

**Why this priority**: Equal priority with US1 since multi-agent evolution is a key use case. Both adapters need this functionality for the system to work correctly.

**Independent Test**: Can be fully tested by creating a MultiAgentAdapter with default proposer, calling `propose_new_texts()` with multi-agent reflective data, and verifying each agent's instruction is mutated appropriately.

**Acceptance Scenarios**:

1. **Given** a MultiAgentAdapter with default proposer, **When** I call `propose_new_texts()` with a reflective dataset containing feedback for multiple agents, **Then** it delegates to `AsyncReflectiveMutationProposer.propose()` and returns mutated instruction texts for each agent.

2. **Given** a MultiAgentAdapter with components `["generator_instruction", "critic_instruction"]`, **When** feedback suggests the generator needs improvement, **Then** the `generator_instruction` is mutated while preserving the spirit of the original.

---

### User Story 3 - Custom Proposer Injection (Priority: P2)

As a gepa-adk developer, I want to optionally inject a custom proposer into adapters, so that I can customize mutation behavior (model, temperature, prompt template).

**Why this priority**: Secondary to core functionality but essential for customization and testing. Enables advanced users to tune mutation behavior.

**Independent Test**: Can be tested by creating an adapter with a custom proposer (different model/temperature), calling `propose_new_texts()`, and verifying the custom proposer is used instead of the default.

**Acceptance Scenarios**:

1. **Given** an ADKAdapter initialized with a custom proposer (custom model, temperature), **When** I call `propose_new_texts()`, **Then** it uses the injected proposer instead of the default.

2. **Given** a MultiAgentAdapter initialized with a custom proposer, **When** I call `propose_new_texts()`, **Then** it uses the injected proposer for all agent instruction mutations.

3. **Given** an adapter with no proposer parameter specified, **When** I call `propose_new_texts()`, **Then** it uses a default `AsyncReflectiveMutationProposer()` instance.

---

### User Story 4 - Graceful Fallback on Empty Dataset (Priority: P2)

As a gepa-adk user, I want the adapters to handle empty reflective datasets gracefully, so that the evolution loop continues without errors when no feedback is available.

**Why this priority**: Important for robustness but not core functionality. The system should degrade gracefully rather than fail.

**Independent Test**: Can be tested by calling `propose_new_texts()` with an empty dataset and verifying unchanged candidate values are returned without errors.

**Acceptance Scenarios**:

1. **Given** an adapter with a proposer, **When** I call `propose_new_texts()` with an empty reflective dataset (`{}`), **Then** the proposer returns `None` and the adapter returns unchanged candidate values.

2. **Given** an adapter with a proposer, **When** I call `propose_new_texts()` with a dataset missing entries for requested components, **Then** unchanged values are returned for missing components.

3. **Given** an adapter with a proposer, **When** the proposer returns `None` for any reason, **Then** the adapter falls back to unchanged candidate values without raising exceptions.

---

### Edge Cases

- What happens when the proposer raises an exception during LLM call?
  - Exception should propagate to caller; adapter should not swallow errors from proposer.
  
- What happens when `components_to_update` contains components not in the candidate?
  - Those components should be skipped (existing behavior in proposer).
  
- What happens when the LLM returns an empty or whitespace-only response?
  - Proposer already handles this by falling back to original text; adapter preserves this behavior.
  
- What happens when custom proposer doesn't implement the expected interface?
  - Validation at init time should catch this with clear error message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: ADKAdapter MUST accept an optional `proposer` parameter in its `__init__` method, typed as `AsyncReflectiveMutationProposer | None`.

- **FR-002**: MultiAgentAdapter MUST accept an optional `proposer` parameter in its `__init__` method, typed as `AsyncReflectiveMutationProposer | None`.

- **FR-003**: When `proposer` parameter is `None` (default), adapters MUST instantiate a default `AsyncReflectiveMutationProposer()` automatically.

- **FR-004**: ADKAdapter's `propose_new_texts()` method MUST delegate to `self._proposer.propose()` instead of the current stub implementation.

- **FR-005**: MultiAgentAdapter's `propose_new_texts()` method MUST delegate to `self._proposer.propose()` instead of the current heuristic-based implementation.

- **FR-006**: When proposer returns `None` (empty dataset), adapters MUST return unchanged candidate values for the requested components.

- **FR-007**: When proposer returns a partial result (some components missing), adapters MUST preserve original candidate values for missing components.

- **FR-008**: Adapters MUST log when falling back to unchanged values due to `None` proposer result.

- **FR-009**: Adapter docstrings MUST document the new `proposer` parameter with usage examples.

- **FR-010**: Existing tests MUST continue to pass (backward compatibility maintained).

### Key Entities

- **AsyncReflectiveMutationProposer**: The proposer that generates instruction mutations via LLM reflection. Already implemented in `src/gepa_adk/engine/proposer.py`.

- **ADKAdapter**: Adapter for single-agent evaluation. Located at `src/gepa_adk/adapters/adk_adapter.py`.

- **MultiAgentAdapter**: Adapter for multi-agent pipeline evaluation. Located at `src/gepa_adk/adapters/multi_agent.py`.

- **Candidate**: Dictionary mapping component names (e.g., "instruction", "generator_instruction") to text values.

- **ReflectiveDataset**: Dictionary mapping component names to sequences of feedback examples.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ADKAdapter's `propose_new_texts()` produces different instruction text when reflective feedback suggests improvements, demonstrating actual LLM-based mutation.

- **SC-002**: MultiAgentAdapter's `propose_new_texts()` produces different instruction texts for multi-agent pipelines when reflective feedback suggests improvements.

- **SC-003**: Custom proposer injection works for both adapters, verified by tests using a mock proposer with predictable output.

- **SC-004**: Empty dataset handling returns unchanged values in 100% of test cases without raising exceptions.

- **SC-005**: All existing adapter tests pass without modification (backward compatibility).

- **SC-006**: New unit tests achieve line coverage for the modified `propose_new_texts()` methods.

## Assumptions

- `AsyncReflectiveMutationProposer` is fully implemented and tested (Issue #7 completed).
- The proposer's `propose()` method signature matches what adapters expect.
- LiteLLM configuration (API keys, models) is handled externally and not part of this feature.
- Default proposer uses reasonable defaults (model: "ollama/gpt-oss:20b", temperature: 0.7).
