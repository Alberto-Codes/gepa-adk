# Feature Specification: Pass CriticScorer Metadata to Reflection Agent

**Feature Branch**: `019-critic-metadata-passthrough`
**Created**: 2026-01-13
**Status**: Draft
**Input**: User description: "Pass CriticScorer metadata (feedback, actionable_guidance) to reflection agent"
**GitHub Issue**: #45
**Depends on**: #9 (CriticScorer), #10 (ADK Reflection Agent)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rich Feedback in Reflection Context (Priority: P1)

As a gepa-adk user, I want the reflection agent to receive critic feedback and actionable guidance, so that it can generate better instruction improvements based on WHY scores are low, not just the numeric values.

**Why this priority**: This is the core value proposition - without this, the reflection agent only sees "score: 0.5" instead of "Score 0.5 - Response was too verbose, reduce length by 30%". The rich context is essential for meaningful reflection.

**Independent Test**: Can be fully tested by running an evaluation with a CriticScorer that returns feedback, then verifying the reflection agent's execution_feedback includes that feedback text.

**Acceptance Scenarios**:

1. **Given** a CriticScorer returns metadata containing `feedback` text, **When** the evaluation batch is passed to the reflection agent, **Then** the feedback text is included in the execution_feedback for each example.
2. **Given** a CriticScorer returns `actionable_guidance`, **When** the reflection agent receives the feedback, **Then** it includes the actionable guidance in the context for generating improved instructions.
3. **Given** multiple evaluations with different feedback texts, **When** building the reflection dataset, **Then** each example preserves its corresponding feedback without mixing.

---

### User Story 2 - Dimension Scores in Reflection (Priority: P2)

As a gepa-adk user, I want dimension scores (e.g., accuracy, relevance, clarity) passed to the reflection agent, so that I can get targeted improvements for specific weak areas.

**Why this priority**: Granular dimension scores enable more precise reflection - the agent can focus on improving specific aspects rather than making generic changes.

**Independent Test**: Can be tested by configuring a critic that returns dimension_scores, evaluating samples, and verifying the reflection agent receives the dimension breakdown.

**Acceptance Scenarios**:

1. **Given** a critic returns `dimension_scores` like `{"accuracy": 0.8, "clarity": 0.6}`, **When** the feedback is passed to reflection, **Then** the dimension scores are included in a readable format.
2. **Given** dimension scores indicate one dimension is significantly lower, **When** the reflection agent proposes improvements, **Then** it has the context to focus on that specific dimension.

---

### User Story 3 - Backward Compatibility with Non-Critic Scorers (Priority: P3)

As a gepa-adk user using non-critic scorers (e.g., simple function-based scorers), I want the system to continue working without errors when no metadata is available.

**Why this priority**: Backward compatibility ensures existing workflows continue to function without modification.

**Independent Test**: Can be tested by running an evaluation with a simple scorer that returns only numeric scores (no metadata), and verifying the reflection pipeline completes successfully.

**Acceptance Scenarios**:

1. **Given** a scorer that returns no metadata, **When** building the reflection example, **Then** the example is built using only the numeric score (existing behavior).
2. **Given** an EvaluationBatch with `metadata=None`, **When** the reflection dataset is constructed, **Then** no errors occur and processing continues normally.

---

### Edge Cases

- What happens when metadata is present for some samples but not others? System includes metadata where available and falls back to score-only for others.
- How does the system handle metadata with empty feedback ("") or missing keys? Empty strings are treated as "no feedback"; missing keys are simply not included in the reflection context.
- What happens when actionable_guidance is very long (e.g., 1000+ characters)? System passes through without truncation; prompt length management is the reflection agent's responsibility.
- How does the system handle malformed metadata (non-dict type)? System logs a warning and falls back to score-only for that example.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: EvaluationBatch MUST support an optional `metadata` field to store scorer metadata for each evaluated sample.
- **FR-002**: ADKAdapter.evaluate() MUST capture and store metadata returned by CriticScorer alongside scores.
- **FR-003**: ADKAdapter._build_reflection_example() MUST include `feedback` text in the execution feedback when present in metadata.
- **FR-004**: ADKAdapter._build_reflection_example() MUST include `actionable_guidance` in the execution feedback when present in metadata.
- **FR-005**: ADKAdapter._build_reflection_example() MUST include `dimension_scores` in the execution feedback when present in metadata.
- **FR-006**: System MUST maintain backward compatibility when metadata is None or not provided.
- **FR-007**: Metadata MUST be aligned with scores by index (metadata[i] corresponds to scores[i]).
- **FR-008**: System MUST gracefully handle partial metadata (some samples have metadata, others don't).

### Key Entities

- **EvaluationBatch**: Extended to include an optional `metadata` field containing a list of dictionaries, one per evaluated sample.
- **Scorer Metadata**: Dictionary containing optional keys: `feedback` (str), `actionable_guidance` (str), `dimension_scores` (dict[str, float]).
- **Reflection Example**: String representation of an evaluation result, now enriched with critic feedback when available.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reflection agents receive critic feedback text for all evaluations performed by CriticScorer.
- **SC-002**: Existing tests using non-critic scorers continue to pass without modification.
- **SC-003**: Reflection-generated instruction improvements demonstrate awareness of specific feedback (verifiable through reflection output analysis).
- **SC-004**: Metadata passthrough adds negligible overhead (less than 5% increase in evaluation time).

## Assumptions

- CriticScorer already extracts and returns metadata correctly (per spec #9).
- The reflection agent's prompt can accommodate additional feedback context without requiring prompt modifications.
- Session state serialization (JSON) can handle the metadata dictionary structure.
- Feedback and actionable_guidance are typically short enough (under 500 characters) to fit in standard context windows.

## Out of Scope

- Modifying the CriticScorer implementation (already works correctly per spec #9).
- Modifying the reflection agent's prompt or instructions to utilize the new context.
- Aggregating or summarizing metadata across multiple samples.
- Filtering or prioritizing which metadata fields to include.
- Persisting metadata beyond the current evaluation-reflection cycle.
