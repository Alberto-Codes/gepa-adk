# Feature Specification: MergeProposer for Combining Pareto-Optimal Candidates

**Feature Branch**: `028-merge-proposer`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "Add MergeProposer for combining Pareto-optimal candidates - enables genetic crossover by merging strengths of different candidates from the Pareto frontier"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge Complementary Candidates (Priority: P1)

As a gepa-adk user running evolution, I want the system to automatically combine two candidates that excel in different areas, so that I get a new candidate that potentially inherits the strengths of both parents.

**Why this priority**: This is the core value proposition of merge-based evolution (genetic crossover). Without this capability, evolution relies solely on mutation which explores local improvements rather than combining distant strengths.

**Independent Test**: Can be fully tested by running evolution with two known candidates that have complementary performance profiles and verifying a merged candidate is produced with inherited components.

**Acceptance Scenarios**:

1. **Given** candidate A excels at examples 1-5 and candidate B excels at examples 6-10, **When** MergeProposer selects them for merging, **Then** a new candidate is created that combines improved components from both A and B.
2. **Given** candidate A has an improved system instruction and candidate B has an improved task instruction, **When** they are merged, **Then** the resulting candidate contains the improved system instruction from A and the improved task instruction from B.
3. **Given** two candidates with overlapping improvements to the same component, **When** they are merged, **Then** the system selects one version based on performance scoring (preferring the higher-performing variant).

---

### User Story 2 - Track Candidate Genealogy (Priority: P2)

As a gepa-adk user, I want the system to track parent-child relationships between candidates throughout evolution, so that the merge operation can identify common ancestors and determine which components each candidate improved.

**Why this priority**: Without genealogy tracking, the merge operation cannot determine which components were modified by which branch of evolution, making intelligent merging impossible.

**Independent Test**: Can be tested by running evolution for multiple iterations and querying the parent chain of any candidate to verify the ancestry is correctly recorded.

**Acceptance Scenarios**:

1. **Given** a new candidate is created via mutation, **When** it is added to the population, **Then** its parent reference points to the source candidate.
2. **Given** a new candidate is created via merging, **When** it is added to the population, **Then** both parent references are recorded (two parents for merged candidates).
3. **Given** evolution has run for N iterations, **When** I query a candidate's ancestry, **Then** I can traverse back to the original seed candidate(s).

---

### User Story 3 - Find Common Ancestors (Priority: P3)

As a gepa-adk user, I want the system to identify the common ancestor between two candidates being merged, so that it can determine exactly which components each candidate independently improved since diverging.

**Why this priority**: Finding the common ancestor enables precise identification of what each branch contributed, allowing intelligent merging rather than arbitrary selection.

**Independent Test**: Can be tested by creating a known genealogy tree and verifying the common ancestor algorithm returns the correct shared ancestor for any two candidates.

**Acceptance Scenarios**:

1. **Given** candidate A and candidate B both descend from candidate X, **When** the system finds their common ancestor, **Then** candidate X is returned.
2. **Given** candidate A and candidate B have no common ancestor (separate seed candidates), **When** the system attempts to find a common ancestor, **Then** it returns no common ancestor and the merge proceeds with component-level comparison only.
3. **Given** a deep genealogy tree with multiple branches, **When** finding the common ancestor of two distant candidates, **Then** the most recent common ancestor is returned (not an earlier ancestor).

---

### Edge Cases

- What happens when two candidates have identical component values? The merge produces a candidate equivalent to either parent (no improvement, but no regression).
- What happens when no candidates on the frontier have a common ancestor? The system falls back to component-level performance comparison to decide which version of each component to use.
- What happens when all candidates on the frontier are derived from the same single lineage? MergeProposer has no complementary candidates to merge and should yield to other proposers (e.g., mutation).
- How does the system handle circular ancestry or corrupted genealogy data? The system validates genealogy integrity and skips merge for candidates with invalid ancestry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a MergeProposer that creates new candidates by combining components from two parent candidates.
- **FR-002**: System MUST track parent relationships for every candidate created during evolution (single parent for mutation, two parents for merge).
- **FR-003**: System MUST be able to traverse the ancestry chain of any candidate to find its lineage back to seed candidates.
- **FR-004**: System MUST identify the common ancestor of two candidates when performing a merge operation.
- **FR-005**: System MUST determine which components each candidate modified relative to their common ancestor.
- **FR-006**: System MUST create merged candidates by selecting the best-performing version of each component from the two parents.
- **FR-007**: System MUST integrate MergeProposer into the evolution loop as an alternative to mutation-based proposal.
- **FR-008**: System MUST select merge candidates from the Pareto frontier to ensure only high-quality candidates are combined.
- **FR-009**: System MUST handle the case where candidates have no common ancestor by using direct component performance comparison.
- **FR-010**: System MUST preserve all metadata and scoring information when creating merged candidates.

### Key Entities

- **Candidate**: An individual in the evolution population. Extended to include parent reference(s) for genealogy tracking. Key attributes: unique identifier, instruction components, performance scores, parent identifier(s), generation number.
- **Genealogy**: The family tree of candidates showing parent-child relationships. Enables finding common ancestors and tracking evolutionary lineage.
- **Component**: An individual piece of the candidate's instruction set (e.g., system instruction, task instruction). The unit of inheritance during merging.
- **Common Ancestor**: The most recent candidate from which two candidates both descend. Used to identify which components each branch independently improved.
- **Pareto Frontier**: The set of non-dominated candidates in the population. Merge candidates are selected from this set to ensure quality.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Merged candidates successfully combine components from both parents in at least 90% of merge operations (verified by inspecting resulting candidate components).
- **SC-002**: Genealogy tracking correctly records parent relationships with 100% accuracy (every candidate has verifiable ancestry back to seeds).
- **SC-003**: Common ancestor identification returns the correct ancestor in 100% of cases for candidates with shared lineage.
- **SC-004**: Evolution runs that include merge proposals show improvement in overall population fitness compared to mutation-only baselines (measured over equivalent iteration counts).
- **SC-005**: MergeProposer completes candidate generation without requiring additional user input or manual intervention.
- **SC-006**: System handles edge cases (no common ancestor, identical components, single-lineage populations) gracefully without errors or crashes.
