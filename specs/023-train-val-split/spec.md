# Feature Specification: Train/Val Split for Evolution Scoring

**Feature Branch**: `023-train-val-split`  
**Created**: 2026-01-14  
**Status**: Draft  
**Input**: User description: "Add validation set (valset) support separate from trainset"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Separate reflection vs scoring datasets (Priority: P1)

As a user running evolution, I want reflection to use a trainset while scoring uses a separate valset so that acceptance decisions are based on generalization rather than overfitting.

**Why this priority**: This is the core behavioral change that enables more reliable evolution outcomes.

**Independent Test**: Can be fully tested by running evolution with distinct trainset/valset and verifying reflection and scoring are sourced from the correct datasets.

**Acceptance Scenarios**:

1. **Given** a trainset with 10 examples and a valset with 50 examples, **When** evolution runs, **Then** reflection uses the trainset examples while baseline/proposal scoring uses the valset examples.
2. **Given** a trainset and a valset, **When** evolution evaluates acceptance, **Then** the acceptance decision uses the valset score only.

---

### User Story 2 - Backward-compatible defaults (Priority: P2)

As a user running simple experiments, I want valset to default to trainset when not provided so that existing workflows keep working without extra configuration.

**Why this priority**: Backward compatibility avoids breaking existing users and reduces friction for casual use.

**Independent Test**: Can be fully tested by running evolution with only a trainset and confirming behavior matches prior runs.

**Acceptance Scenarios**:

1. **Given** only a trainset is provided, **When** evolution runs, **Then** the trainset is used for both reflection and scoring.

---

### User Story 3 - Candidate selection uses valset (Priority: P3)

As a user using candidate selection and Pareto scoring, I want those scores to be computed from the valset so that selection reflects generalization performance.

**Why this priority**: It aligns candidate selection with the same scoring basis as acceptance decisions.

**Independent Test**: Can be fully tested by enabling candidate selection with a distinct valset and confirming Pareto scores derive from valset results.

**Acceptance Scenarios**:

1. **Given** candidate selection is enabled and a valset is provided, **When** candidates are evaluated, **Then** Pareto scores are computed from valset scores.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- What happens when a valset is provided but is empty?
- How does the system handle scoring failures on the valset while reflection succeeds on the trainset?
- What happens when trainset and valset have incompatible schemas or formats?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST accept a valset that is distinct from the trainset for evolution runs.
- **FR-002**: System MUST use trainset examples for reflection-only activities.
- **FR-003**: System MUST use valset examples for baseline scoring, proposal scoring, and acceptance decisions.
- **FR-004**: System MUST default valset to trainset when no valset is provided.
- **FR-005**: System MUST compute candidate selection and Pareto scores from valset results when valset is provided.
- **FR-006**: System MUST report scoring outcomes in a way that clearly distinguishes valset-based scores from reflection data.

### Key Entities *(include if feature involves data)*

- **Trainset**: The example set used to drive reflection and learning signals.
- **Valset**: The example set used to score baselines, proposals, and selections.
- **Reflection Dataset**: The collected information derived from trainset evaluations to guide evolution.
- **Scoring Results**: The outcomes produced from valset evaluations that determine acceptance and selection.

### Assumptions

- Trainset and valset use compatible schemas so they can be evaluated by the same workflow.
- Users can provide a valset at run time when they want separate scoring.

### Out of Scope

- Changing how scoring metrics are computed beyond swapping the dataset used.
- Creating new user interfaces for dataset management.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: In runs with a provided valset, 100% of acceptance decisions are based on valset scores.
- **SC-002**: In runs with distinct trainset and valset, 100% of reflection data is derived from trainset evaluations only.
- **SC-003**: When no valset is provided, evolution completes with outcomes equivalent to using the trainset for both reflection and scoring.
- **SC-004**: For candidate selection runs with a valset, 100% of Pareto scores are computed from valset results.
