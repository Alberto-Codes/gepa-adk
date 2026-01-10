# Feature Specification: CriticScorer - Structured Feedback from ADK Critic Agents

**Feature Branch**: `009-critic-scorer`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: User description: "[Feature] Implement CriticScorer (structured feedback from ADK critic agents)"  
**GitHub Issue**: #9  
**Parent**: #1  
**Depends on**: #5 (Scorer Protocol)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Structured Scoring (Priority: P1)

As a gepa-adk user, I want to use an ADK agent as a critic to evaluate outputs, so that I receive a structured score with actionable feedback instead of a simple 0/1 binary score.

**Why this priority**: This is the core value proposition - without structured scoring, the feature has no purpose. Users need meaningful feedback to improve their agent outputs.

**Independent Test**: Can be fully tested by creating a simple critic agent, calling the scorer with sample input/output, and verifying that a numeric score and feedback string are returned.

**Acceptance Scenarios**:

1. **Given** a critic agent with an output schema that includes `score` and `feedback` fields, **When** I call `score(input, output)`, **Then** it returns a numeric score extracted from the structured JSON response.
2. **Given** a critic agent returns structured JSON, **When** I retrieve the scoring result, **Then** feedback text is included in the metadata dictionary.
3. **Given** an input-output pair to evaluate, **When** the critic agent processes it, **Then** the score is a float value between 0.0 and 1.0 (normalized).

---

### User Story 2 - Workflow Critic Support (Priority: P2)

As a gepa-adk user, I want to use multi-step workflow agents (like SequentialAgent with validator + scorer) as critics, so that complex evaluation pipelines can produce structured scores.

**Why this priority**: Many real-world evaluation scenarios require multi-step validation before scoring. This extends the basic capability to composite agent architectures.

**Independent Test**: Can be tested by creating a SequentialAgent with two sub-agents (validator and scorer), calling the CriticScorer, and verifying the final score is extracted from the last sub-agent's output.

**Acceptance Scenarios**:

1. **Given** a SequentialAgent critic composed of a validator agent and a scorer agent, **When** I call `score()`, **Then** it executes the full workflow in sequence.
2. **Given** a workflow critic completes execution, **When** I retrieve the result, **Then** the score is extracted from the final sub-agent's output.
3. **Given** a validator agent in the workflow fails validation, **When** the workflow completes, **Then** the scorer handles the validation state appropriately in the final score.

---

### User Story 3 - Multi-Dimensional Scoring with Guidance (Priority: P3)

As a gepa-adk user, I want to receive dimension scores (e.g., accuracy, relevance, clarity) and actionable guidance from the critic, so that I can understand which aspects need improvement and how to improve them.

**Why this priority**: Advanced users need granular feedback for reflection and improvement. This enables more sophisticated optimization loops.

**Independent Test**: Can be tested by configuring a critic agent to return `dimension_scores` and `actionable_guidance` fields, then verifying these are captured in the metadata.

**Acceptance Scenarios**:

1. **Given** a critic agent returns `dimension_scores` (e.g., `{"accuracy": 0.8, "clarity": 0.6}`), **When** I get the metadata, **Then** it includes all dimension scores as a dictionary.
2. **Given** a critic agent returns `actionable_guidance` text, **When** I get the metadata, **Then** it includes the guidance string for reflection.
3. **Given** a critic returns multiple structured fields, **When** I access the metadata, **Then** all structured fields from the JSON output are preserved.

---

### User Story 4 - Session State Sharing (Priority: P4)

As a gepa-adk user, I want the critic to optionally share session state with the main agent, so that evaluation can access conversation history and context.

**Why this priority**: Session sharing enables context-aware evaluation but is not required for basic functionality.

**Independent Test**: Can be tested by passing an existing session ID to the scorer and verifying the critic has access to prior conversation context.

**Acceptance Scenarios**:

1. **Given** an existing session ID from a prior agent interaction, **When** I pass it to the critic scorer, **Then** the critic has access to the session's conversation history.
2. **Given** no session ID is provided, **When** I call the scorer, **Then** a new isolated session is created for the critic.

---

### Edge Cases

- What happens when the critic agent returns malformed JSON that cannot be parsed?
- How does the system handle when the `score` field is missing from the structured output?
- What happens when the critic agent times out or fails to respond?
- How does the system handle scores outside the expected 0.0-1.0 range?
- What happens when dimension_scores contains non-numeric values?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an ADK agent (LlmAgent or workflow agent) as the critic for scoring.
- **FR-002**: System MUST execute the critic agent with a formatted input containing the original input, output, and optionally the expected output.
- **FR-003**: System MUST parse the critic agent's structured JSON output to extract the score.
- **FR-004**: System MUST return a tuple of `(score: float, metadata: dict)` from the scoring operation.
- **FR-005**: System MUST include `feedback` in the metadata when present in the critic output.
- **FR-006**: System MUST include `dimension_scores` in the metadata when present in the critic output.
- **FR-007**: System MUST include `actionable_guidance` in the metadata when present in the critic output.
- **FR-008**: System MUST support an optional `session_id` parameter to share session state with the critic.
- **FR-009**: System MUST use a default session service (InMemorySessionService) when none is provided.
- **FR-010**: System MUST implement the Scorer protocol interface (from #5) for compatibility with the scoring framework.
- **FR-011**: System MUST handle JSON parsing errors gracefully with meaningful error messages.
- **FR-012**: System MUST support both simple LlmAgent critics and composite workflow agents (e.g., SequentialAgent).

### Key Entities

- **CriticScorer**: The main scorer implementation that wraps an ADK critic agent and implements the Scorer protocol. Responsible for formatting inputs, executing the critic, and parsing structured outputs.
- **Critic Agent**: An ADK agent (LlmAgent, SequentialAgent, etc.) configured with an output schema that produces structured JSON including at minimum a `score` field.
- **Scoring Result**: A tuple containing the numeric score (float) and metadata dictionary with optional feedback, dimension scores, and actionable guidance.
- **Session Service**: An ADK service that manages session state; can be shared between the main agent and critic for context-aware evaluation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can obtain structured scoring results (score + feedback) from any ADK agent within a single function call.
- **SC-002**: Metadata dictionary contains all structured fields returned by the critic (feedback, dimension_scores, actionable_guidance) when present.
- **SC-003**: CriticScorer seamlessly integrates with existing gepa-adk optimization loops that use the Scorer protocol.
- **SC-004**: Users can evaluate 100 input-output pairs without manual intervention or session management.
- **SC-005**: Error cases (malformed JSON, missing score field, timeout) produce clear, actionable error messages.
- **SC-006**: Multi-step workflow critics (SequentialAgent) complete execution and return valid scores.

## Assumptions

- The Scorer protocol (#5) is implemented and available for CriticScorer to implement.
- ADK's `Runner`, `LlmAgent`, `SequentialAgent`, and `InMemorySessionService` are stable and available for use.
- Critic agents are pre-configured with appropriate output schemas that include at minimum a `score` field.
- Score values from critics are expected to be in the 0.0-1.0 range (normalized); out-of-range handling is implementation-specific.
- Session services are compatible between the main agent workflow and the critic evaluation.

## Out of Scope

- Creating or managing the critic agent's prompt or output schema (user responsibility).
- Automatic retry logic for failed critic evaluations.
- Caching of critic responses.
- Parallel/batch scoring of multiple input-output pairs (single-call interface only).
- Training or fine-tuning critic agents.
