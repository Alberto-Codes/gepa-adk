# Feature Specification: AsyncReflectiveMutationProposer

**Feature Branch**: `007-async-mutation-proposer`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: User description: "Implement AsyncReflectiveMutationProposer - async proposer that generates instruction mutations via LiteLLM reflection, handles empty reflective datasets, and works with Candidate dataclass for lineage tracking"  
**Parent Issue**: #1  
**GitHub Issue**: #7

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Instruction Mutations (Priority: P1)

As a gepa-adk developer, I want an async proposer that generates instruction mutations from a reflective dataset, so that the evolution engine can produce improved candidate instructions without blocking the application.

**Why this priority**: This is the core value proposition - without mutation generation, the proposer serves no purpose. The engine depends on this capability to evolve instructions.

**Independent Test**: Can be fully tested by providing a mock reflective dataset with feedback examples, calling `await proposer.propose(...)`, and verifying the returned candidate contains mutated instruction text.

**Acceptance Scenarios**:

1. **Given** a proposer with a valid configuration and a reflective dataset containing feedback, **When** I call `await proposer.propose(candidate, reflective_dataset, components_to_update)`, **Then** it returns a new candidate dictionary with mutated instruction text.

2. **Given** a proposer and a reflective dataset with multiple feedback examples, **When** I call propose, **Then** the returned instruction incorporates insights from the reflective data.

3. **Given** a proposer configured with a specific reflection model, **When** I call propose, **Then** it uses the configured model for LLM reflection calls.

---

### User Story 2 - Async LiteLLM Integration (Priority: P2)

As a gepa-adk developer, I want the proposer to call LiteLLM asynchronously, so that instruction mutations are generated without blocking the event loop and can be used in concurrent evolution pipelines.

**Why this priority**: Async-first design is a core architectural principle (ADR-001). Without non-blocking LLM calls, the proposer would become a bottleneck in concurrent evolution runs.

**Independent Test**: Can be tested by mocking `litellm.acompletion()`, calling propose, and verifying the async method was awaited with correct parameters.

**Acceptance Scenarios**:

1. **Given** a proposer with a configured reflection model, **When** I call `await proposer.propose(...)`, **Then** it calls `litellm.acompletion()` asynchronously (not the sync version).

2. **Given** a proposer, **When** multiple propose calls are made concurrently, **Then** they can execute in parallel without blocking each other.

3. **Given** a proposer with model="gemini-2.0-flash", **When** I call propose, **Then** `litellm.acompletion()` is called with `model="gemini-2.0-flash"`.

---

### User Story 3 - Handle Empty Reflective Dataset (Priority: P3)

As a gepa-adk developer, I want the proposer to gracefully handle empty reflective datasets by returning None, so that the engine can skip mutation proposals when no feedback is available.

**Why this priority**: Edge case handling ensures robustness. Without this, the engine would crash or produce invalid proposals when no reflective data exists.

**Independent Test**: Can be tested by calling propose with an empty reflective dataset and verifying it returns None without making any LLM calls.

**Acceptance Scenarios**:

1. **Given** a proposer and an empty reflective dataset ({}), **When** I call `await proposer.propose(...)`, **Then** it returns `None`.

2. **Given** a proposer and a reflective dataset where the requested component has no entries, **When** I call propose with that component, **Then** it returns `None` (no proposal possible).

3. **Given** an empty reflective dataset, **When** I call propose, **Then** no LLM API calls are made (cost optimization).

---

### Edge Cases

- What happens when LiteLLM API call fails (network error, rate limit)?
  - The exception should propagate to the caller (fail-fast behavior, consistent with AsyncGEPAEngine).
- What happens when the LLM returns an empty or malformed response?
  - Return the original instruction text unchanged (safe fallback).
- What happens when components_to_update contains a component not in the candidate?
  - Skip that component (only mutate components that exist).
- What happens when the prompt template is invalid or missing placeholders?
  - Use a sensible default template; log a warning if custom template lacks required placeholders.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Proposer MUST accept a reflection model identifier, optional custom prompt template, and optional configuration at construction.
- **FR-002**: Proposer MUST implement an async `propose()` method that accepts candidate components, reflective dataset, and components to update.
- **FR-003**: Proposer MUST return `None` when the reflective dataset is empty or contains no entries for the requested components.
- **FR-004**: Proposer MUST call `litellm.acompletion()` asynchronously for reflection-based mutation generation.
- **FR-005**: Proposer MUST build reflection messages that include the current instruction and feedback from the reflective dataset.
- **FR-006**: Proposer MUST return a dictionary mapping component names to their proposed new text values.
- **FR-007**: Proposer MUST use the configured reflection model for all LLM calls.
- **FR-008**: Proposer MUST support custom prompt templates for reflection messages.
- **FR-009**: Proposer MUST extract the generated instruction text from the LLM response.
- **FR-010**: Proposer MUST handle LLM response edge cases (empty content) by returning original text.

### Key Entities

- **AsyncReflectiveMutationProposer**: The main proposer class that generates instruction mutations via LLM reflection. Holds model configuration and prompt template.
- **ReflectiveDataset**: A mapping of component names to sequences of feedback examples. Each example contains context about what worked or didn't work (provided by adapter, not defined here).
- **ProposalResult**: The output dictionary mapping component names to proposed text. Returns None when no proposal is possible.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Proposer generates valid instruction mutations in 95%+ of calls when given non-empty reflective datasets.
- **SC-002**: Proposer returns None within 10ms when given empty reflective datasets (no LLM calls made).
- **SC-003**: Proposer correctly uses the configured reflection model for all LLM calls (100% compliance).
- **SC-004**: Proposer integrates seamlessly with AsyncGEPAEngine's mutation workflow without blocking.
- **SC-005**: All acceptance scenarios pass as automated tests with mocked LLM responses.
- **SC-006**: Proposer handles concurrent calls without race conditions or shared state issues.

## Assumptions

- LiteLLM is available as a project dependency and correctly configured with API keys via environment variables.
- The reflective dataset structure follows the format produced by `AsyncGEPAAdapter.make_reflective_dataset()`.
- The proposer does not manage candidate lineage (generation, parent_id) - that responsibility remains with the engine or caller.
- Error handling follows fail-fast: LiteLLM exceptions propagate to the caller without retry logic in v1.
- The default reflection model is "gemini-2.0-flash" (consistent with EvolutionConfig defaults).
- Prompt templates are text strings with placeholder substitution (not Jinja2 or complex templating).
