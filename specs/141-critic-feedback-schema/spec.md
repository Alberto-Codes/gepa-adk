# Feature Specification: Standardize Critic Feedback Schema

**Feature Branch**: `141-critic-feedback-schema`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "GitHub issue 141 - Standardize critic feedback schema with KISS normalization"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simple Critic Returns Score and String (Priority: P1)

A developer implementing a basic critic scorer returns a simple tuple of (score, feedback_string) without needing to understand complex data structures. The system automatically normalizes this into a consistent format for the reflection agent.

**Why this priority**: This is the most common use case - simple users should have the lowest barrier to entry. The KISS principle demands that the basic case be trivially simple.

**Independent Test**: Can be fully tested by creating a scorer that returns `(0.45, "Too clinical, needs personal voice")` and verifying the normalized output contains both `score` and `feedback_text` fields.

**Acceptance Scenarios**:

1. **Given** a scorer returns `(0.75, "Good clarity but needs more examples")`, **When** the feedback is processed, **Then** the normalized output contains `{"score": 0.75, "feedback_text": "Good clarity but needs more examples"}`
2. **Given** a scorer returns `(0.0, "")` (empty feedback string), **When** the feedback is processed, **Then** the normalized output contains `{"score": 0.0, "feedback_text": ""}`
3. **Given** a scorer returns `(1.0, "Perfect response!")`, **When** the feedback is processed, **Then** the normalized output contains `{"score": 1.0, "feedback_text": "Perfect response!"}`

---

### User Story 2 - Advanced Critic Returns Score and Dictionary (Priority: P2)

A power user implementing a sophisticated critic returns a tuple of (score, dictionary) with detailed feedback including optional dimensions and guidance. The system normalizes this while preserving all provided fields.

**Why this priority**: Power users need flexibility for advanced use cases, but this should not complicate the simple case.

**Independent Test**: Can be fully tested by creating a scorer that returns `(0.45, {"feedback_text": "Too clinical", "dimensions": {"voice": 0.2}, "guidance": "Add I statements"})` and verifying all fields pass through.

**Acceptance Scenarios**:

1. **Given** a scorer returns `(0.45, {"feedback_text": "Too clinical, needs personal voice", "dimensions": {"voice": 0.2, "urgency": 0.4}, "guidance": "Add first-person 'I' statements"})`, **When** the feedback is processed, **Then** the normalized output contains all provided fields including `score`, `feedback_text`, `dimensions`, and `guidance`
2. **Given** a scorer returns `(0.6, {"feedback_text": "Mostly good", "custom_field": "user-defined value"})`, **When** the feedback is processed, **Then** the normalized output preserves the custom field alongside required fields
3. **Given** a scorer returns `(0.5, {"dimensions": {"accuracy": 0.8}})` (missing feedback_text), **When** the feedback is processed, **Then** the normalized output contains `feedback_text` as an empty string and preserves the dimensions

---

### User Story 3 - Reflector Receives Consistent Format (Priority: P1)

The reflection agent always receives feedback in a consistent, predictable format regardless of whether the critic used simple or advanced output. This enables the reflector to process feedback uniformly.

**Why this priority**: Consistency at the reflector interface is critical for reliable system behavior - tied with P1 because both simple input and consistent output are fundamental.

**Independent Test**: Can be fully tested by running both simple and advanced scorers through the system and verifying the reflector receives identically-structured feedback objects.

**Acceptance Scenarios**:

1. **Given** feedback from a simple scorer (string format), **When** the reflector receives it, **Then** the feedback structure matches the documented schema with `score` and `feedback_text` at minimum
2. **Given** feedback from an advanced scorer (dict format), **When** the reflector receives it, **Then** the feedback structure includes all provided optional fields in addition to required fields
3. **Given** multiple trials with mixed feedback formats, **When** the reflector processes them, **Then** all feedback objects have consistent required fields (`score`, `feedback_text`) regardless of origin

---

### Edge Cases

- What happens when feedback_text is None instead of missing? System treats None as empty string.
- What happens when score is outside 0.0-1.0 range? Score validation is handled elsewhere; normalization passes through the value.
- What happens when the dictionary contains a `score` key? The explicit score parameter takes precedence over any score in the dictionary.
- How does system handle non-string feedback_text in dictionary? System converts to string representation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept critic feedback as a tuple of (float, string) for simple use cases
- **FR-002**: System MUST accept critic feedback as a tuple of (float, dict) for advanced use cases
- **FR-003**: System MUST normalize simple string feedback into a dictionary with `score` and `feedback_text` keys
- **FR-004**: System MUST preserve all keys from advanced dictionary feedback during normalization
- **FR-005**: System MUST ensure `feedback_text` key exists in all normalized output (defaulting to empty string if missing)
- **FR-006**: System MUST ensure `score` key exists in all normalized output (using the explicit score parameter)
- **FR-007**: System MUST pass through optional keys (`dimensions`, `guidance`, and custom fields) when present in advanced feedback
- **FR-008**: System MUST provide consistent feedback format to the reflection agent regardless of input format
- **FR-009**: System MUST document both feedback formats clearly for scorer implementers

### Key Entities

- **CriticFeedback**: The normalized feedback object containing `score` (float 0.0-1.0), `feedback_text` (string), and optional fields (`dimensions`, `guidance`, custom fields)
- **SimpleFeedback**: Raw input format as tuple (score, string)
- **AdvancedFeedback**: Raw input format as tuple (score, dict with required `feedback_text` and optional additional fields)
- **Trial**: Contains normalized feedback alongside trajectory (input/output pair)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can implement a working critic scorer with simple format in under 5 minutes by following documentation
- **SC-002**: All existing scorers continue to work without modification after normalization is introduced
- **SC-003**: 100% of feedback reaching the reflector contains both `score` and `feedback_text` fields
- **SC-004**: Advanced users can add custom fields that pass through to the reflector without system modification
- **SC-005**: Documentation examples demonstrate both simple and advanced formats clearly

## Assumptions

- Score validation (0.0-1.0 range) is handled by a separate component, not by the normalization function
- The normalization function is a pure utility that does not perform I/O or side effects
- Existing scorer implementations return data in one of the two supported formats
- The reflection agent's instruction template will be updated separately to reference the normalized field names

## Dependencies

- Related to GitHub issue #140 (DRY consolidation of trial-building logic) - normalization should be part of that consolidation
