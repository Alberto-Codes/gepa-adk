# Feature Specification: Shared ADK Event Output Extraction Utility

**Feature Branch**: `033-event-output-extraction`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User description: "gh issue 82. make sure to read comments. Latest is a bug we found might as well centralize and solve for bug. The dep gh issue needs this bug resolved."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Output Extraction Across Adapters (Priority: P1)

As a developer using gepa-adk adapters, I need consistent behavior when extracting final output text from ADK events so that I get reliable results regardless of which adapter I use or which model generates the response.

**Why this priority**: This is the core value proposition. Four different code paths currently extract output differently, leading to inconsistent behavior and bugs when models emit reasoning content.

**Independent Test**: Can be tested by creating a shared utility function and verifying it returns correct output for various event types, including events with `part.thought` reasoning content.

**Acceptance Scenarios**:

1. **Given** an ADK event with `event.actions.response_content` populated, **When** I call the output extraction utility, **Then** it returns the response content text.
2. **Given** an ADK event without `response_content` but with `event.content.parts` containing text, **When** I call the output extraction utility, **Then** it returns the text from the parts.
3. **Given** an ADK event with parts that include both `thought=True` (reasoning) and `thought=False` (actual output), **When** I call the output extraction utility, **Then** it returns only the non-thought text, skipping reasoning content.

---

### User Story 2 - Bug Fix for Models Emitting Reasoning Content (Priority: P1)

As a user running gepa-adk with local/OSS models that emit reasoning content (e.g., `gpt-oss:20b`), I need the system to filter out thought/reasoning parts so that I get the actual JSON output instead of captured reasoning text.

**Why this priority**: This is a critical bug causing complete failures (72 parse errors with scores returning 0.0) when using models that emit reasoning content. The fix must be included in the shared utility.

**Independent Test**: Can be tested by simulating events with `part.thought=True` markers and verifying they are filtered out.

**Acceptance Scenarios**:

1. **Given** an event where the first part has `thought=True` with reasoning text and the second part has `thought=False` with JSON output, **When** I extract output, **Then** I get the JSON output, not the reasoning.
2. **Given** only parts with `thought=True` (edge case), **When** I extract output, **Then** I get an empty result, not reasoning text.
3. **Given** a model response where reasoning appears before the final answer, **When** I extract output, **Then** the final answer is returned without reasoning prefix.

---

### User Story 3 - Streaming JSON Concatenation Support (Priority: P2)

As the CriticScorer component, I need to concatenate all event text parts when processing streaming responses so that I can handle streaming JSON scenarios correctly.

**Why this priority**: This is a specific use case needed by CriticScorer. It extends the basic extraction with a flag for concatenation behavior.

**Independent Test**: Can be tested by passing multiple events with partial text and verifying concatenation produces complete output.

**Acceptance Scenarios**:

1. **Given** multiple events each containing partial JSON text and `prefer_concatenated=True`, **When** I extract output, **Then** I get all parts concatenated together.
2. **Given** multiple events and `prefer_concatenated=False` (default), **When** I extract output, **Then** I get only the final event's output.

---

### User Story 4 - Adapter Consolidation (Priority: P2)

As a maintainer of gepa-adk, I need all four adapters (ADKAdapter, MultiAgentAdapter x2, CriticScorer) to use the shared utility so that I only have one place to update when ADK event structure changes.

**Why this priority**: This is the refactoring goal that reduces maintenance burden and prevents future bugs from inconsistent implementations.

**Independent Test**: Can be tested by verifying each adapter calls the shared utility and no longer contains duplicated extraction logic.

**Acceptance Scenarios**:

1. **Given** ADKAdapter._run_single_example, **When** I inspect the code, **Then** it uses the shared utility instead of inline extraction logic.
2. **Given** MultiAgentAdapter._run_shared_session and _run_isolated_sessions, **When** I inspect the code, **Then** both use the shared utility.
3. **Given** CriticScorer.async_score, **When** I inspect the code, **Then** it uses the shared utility with appropriate flags.

---

### Edge Cases

- What happens when event has no `actions`, no `content`, and no `parts`? Returns empty string.
- What happens when all parts have `thought=True`? Returns empty string (no actual output available).
- What happens when `event.content.parts` exists but is empty? Returns empty string.
- What happens when `part.text` is None or empty string? Skips that part, continues to next.
- What happens when `prefer_concatenated=True` but there's only one event? Returns that event's output normally.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a function `extract_final_output` in `gepa_adk.utils.events` module.
- **FR-002**: The function MUST accept a list of ADK events as input and return a string.
- **FR-003**: The function MUST first check for `event.actions.response_content` as the preferred output source.
- **FR-004**: The function MUST fall back to `event.content.parts` when `response_content` is not available.
- **FR-005**: The function MUST filter out parts where `part.thought` is True, consistent with ADK standard patterns.
- **FR-006**: The function MUST support an optional `prefer_concatenated` parameter (default False) for streaming scenarios.
- **FR-007**: When `prefer_concatenated=True`, the function MUST concatenate all non-thought text parts from all events.
- **FR-008**: ADKAdapter._run_single_example MUST use the shared utility instead of inline extraction.
- **FR-009**: MultiAgentAdapter._run_shared_session MUST use the shared utility instead of inline extraction.
- **FR-010**: MultiAgentAdapter._run_isolated_sessions MUST use the shared utility instead of inline extraction.
- **FR-011**: CriticScorer.async_score MUST use the shared utility instead of inline extraction.
- **FR-012**: The function MUST handle missing attributes gracefully using `getattr` or `hasattr` checks.
- **FR-013**: The function MUST return an empty string when no valid output can be extracted.

### Key Entities

- **ADK Event**: The event object emitted by ADK agents containing actions and content.
- **Event Actions**: Container for `response_content` and other action metadata.
- **Event Content**: Container for `parts` array containing text and thought markers.
- **Part**: Individual content element with `text` attribute and optional `thought` boolean marker.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All duplicated output extraction logic is removed from the four adapter locations, reducing code duplication to a single implementation.
- **SC-002**: Models that emit reasoning content (with `thought=True` markers) have their output correctly extracted without capturing reasoning text.
- **SC-003**: All existing tests continue to pass after refactoring to use the shared utility.
- **SC-004**: The shared utility achieves 100% test coverage for the documented acceptance scenarios.
- **SC-005**: Parse error rate for models emitting reasoning content drops from observed failures to zero when using the updated extraction logic.

## Assumptions

- ADK event structure follows the documented patterns where `event.actions.response_content` and `event.content.parts` are the primary output sources.
- The `part.thought` attribute follows ADK's standard boolean convention where `True` indicates reasoning/thinking content.
- The existing `extract_trajectory` utility in `gepa_adk.utils.events` provides a precedent for the module location and coding patterns.
- No external dependencies are needed; this uses Python stdlib only per ADR-000.

## Dependencies

- **Blocks**: Issue #78 (Formalize robust JSON extraction strategy) - The robust JSON parser in #78 should use this shared utility for consistent output extraction before parsing. The dependency is inverse to what was originally documented - this bug fix provides the foundation that #78 can build upon.
