# Feature Specification: Frontier Types and Valset Evaluation Policies

**Feature Branch**: `027-frontier-eval-policy`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "GitHub Issue #62 - Add frontier types and valset evaluation policies"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Objective-Level Pareto Selection (Priority: P1)

As a user optimizing across multiple objectives, I want frontier tracking to support objective-level dominance, so that Pareto selection reflects multi-metric tradeoffs at the objective level rather than per-instance.

**Why this priority**: This is the core capability enabling true multi-objective optimization. Without objective-level Pareto selection, users cannot effectively balance competing objectives (e.g., accuracy vs. cost) when evolving solutions.

**Independent Test**: Can be fully tested by configuring frontier type to "objective" and verifying that candidate selection uses objective-level dominance scores. Delivers ability to evolve solutions that balance multiple objectives effectively.

**Acceptance Scenarios**:

1. **Given** frontier_type is set to "objective", **When** candidates are evaluated with objective_scores, **Then** Pareto selection uses objective-level dominance (comparing aggregated scores per objective)
2. **Given** frontier_type is set to "objective", **When** a candidate dominates another across all objectives, **Then** the dominated candidate is excluded from the frontier
3. **Given** frontier_type is set to "objective", **When** two candidates have non-dominated tradeoffs, **Then** both remain on the Pareto frontier

---

### User Story 2 - Hybrid Frontier Tracking (Priority: P2)

As a user with complex optimization needs, I want hybrid frontier tracking that combines instance-level and objective-level considerations, so that I can capture nuanced tradeoffs in my evolution runs.

**Why this priority**: Hybrid mode provides flexibility between pure instance-level and pure objective-level tracking, enabling more sophisticated optimization strategies for advanced users.

**Independent Test**: Can be fully tested by configuring frontier type to "hybrid" and verifying that frontier tracking considers both instance and objective dimensions. Delivers flexibility for complex multi-objective scenarios.

**Acceptance Scenarios**:

1. **Given** frontier_type is set to "hybrid", **When** candidates are evaluated, **Then** Pareto tracking considers both instance-level and objective-level dominance
2. **Given** frontier_type is set to "hybrid", **When** comparing candidates, **Then** dominance is determined by a combination of instance and objective scores

---

### User Story 3 - Cartesian Frontier Tracking (Priority: P2)

As a user needing fine-grained multi-objective tracking, I want Pareto tracking maintained per (example, objective) pair, so that I can understand performance at the most granular level.

**Why this priority**: Cartesian mode provides maximum granularity for users who need to track Pareto frontiers across all combinations of examples and objectives.

**Independent Test**: Can be fully tested by configuring frontier type to "cartesian" and verifying that separate Pareto frontiers are maintained for each (example, objective) combination. Delivers granular visibility into solution performance.

**Acceptance Scenarios**:

1. **Given** frontier_type is set to "cartesian", **When** candidates are evaluated, **Then** Pareto tracking is maintained per (example, objective) pair
2. **Given** frontier_type is set to "cartesian", **When** querying the frontier, **Then** results can be filtered by specific example and objective combinations

---

### User Story 4 - Full Valset Evaluation Policy (Priority: P1)

As a user who needs comprehensive evaluation, I want full valset evaluation where every validation example is scored each iteration, so that I have complete visibility into solution performance.

**Why this priority**: Full evaluation is the default expected behavior and ensures complete scoring data for tracking and selection decisions.

**Independent Test**: Can be fully tested by configuring val_evaluation_policy to "full_eval" and verifying that all valset IDs are scored in each evolution iteration. Delivers complete evaluation coverage.

**Acceptance Scenarios**:

1. **Given** val_evaluation_policy is set to "full_eval", **When** evolution runs, **Then** every valset ID is scored each iteration
2. **Given** val_evaluation_policy is set to "full_eval", **When** an iteration completes, **Then** scores exist for all validation examples

---

### User Story 5 - Subset Valset Evaluation Policy (Priority: P2)

As a user with large validation sets, I want configurable subset evaluation policies, so that evaluation cost is controlled while still tracking progress over time.

**Why this priority**: For large valsets, scoring every example each iteration can be prohibitively expensive. Subset evaluation enables scalable optimization by reducing per-iteration cost.

**Independent Test**: Can be fully tested by configuring val_evaluation_policy to "subset" and verifying that only a subset of valset IDs is scored per iteration. Delivers cost-effective evaluation for large validation sets.

**Acceptance Scenarios**:

1. **Given** val_evaluation_policy is set to "subset", **When** evolution runs, **Then** only a subset of valset IDs is scored per iteration
2. **Given** val_evaluation_policy is set to "subset", **When** multiple iterations complete, **Then** all valset IDs are eventually covered over time
3. **Given** val_evaluation_policy is set to "subset", **When** configuring the policy, **Then** the subset size or sampling strategy can be specified

---

### Edge Cases

- What happens when frontier_type is set to "objective" but no objective_scores are provided? System should validate and raise an informative error.
- What happens when a subset evaluation policy is configured but the subset size exceeds the valset size? System should fall back to full evaluation and optionally warn the user.
- How does the system handle an empty validation set when evaluation policies are configured? System should handle gracefully without errors.
- What happens when switching frontier types mid-evolution run? System MUST prevent this by raising ConfigurationError if frontier_type is changed after ParetoState initialization. Frontier type is immutable per evolution run; users must start a new evolution run to use a different frontier type.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support multiple frontier types: "instance" (default), "objective", "hybrid", and "cartesian"
- **FR-002**: System MUST use objective-level dominance for Pareto selection when frontier_type is "objective"
- **FR-003**: System MUST maintain separate Pareto frontiers per (example, objective) pair when frontier_type is "cartesian"
- **FR-004**: System MUST combine instance and objective considerations when frontier_type is "hybrid"
- **FR-005**: System MUST support valset evaluation policies: "full_eval" (default) and "subset"
- **FR-006**: System MUST score all valset IDs each iteration when val_evaluation_policy is "full_eval"
- **FR-007**: System MUST score only a configurable subset of valset IDs per iteration when val_evaluation_policy is "subset". The subset_size parameter accepts: (1) int (absolute count of examples to evaluate per iteration), or (2) float in range [0.0, 1.0] (fraction of total valset size). Default: 0.2 (20% of valset per iteration). System MUST use round-robin selection to ensure all valset IDs are eventually covered across iterations.
- **FR-008**: System MUST validate that objective_scores are present when frontier_type requires them (objective, hybrid, cartesian)
- **FR-009**: System MUST maintain backward compatibility by defaulting to "instance" frontier type and "full_eval" evaluation policy
- **FR-010**: System MUST expose frontier_type and val_evaluation_policy configuration options to users

### Key Entities

- **FrontierType**: Enumeration defining frontier tracking modes (instance, objective, hybrid, cartesian)
- **EvaluationPolicy**: Configuration for valset evaluation behavior (full_eval, subset), including subset size/strategy parameters
- **ObjectiveScores**: Scores aggregated at the objective level for multi-objective Pareto comparisons
- **ParetoFrontier**: Collection of non-dominated candidates according to the configured frontier type

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure any of the four frontier types and observe corresponding selection behavior within a single evolution run
- **SC-002**: Users with large validation sets (1000+ examples) can reduce per-iteration evaluation cost by 80% or more using subset evaluation policies
- **SC-003**: All existing workflows using default settings continue to work without modification (100% backward compatibility)
- **SC-004**: Users can switch between frontier types across different evolution runs without data corruption or configuration errors
- **SC-005**: Multi-objective optimization runs show improved diversity in final solutions when using appropriate frontier types compared to instance-only tracking. Measured by: (1) number of unique non-dominated candidates in final frontier is ≥20% higher with objective/hybrid/cartesian types vs instance-only, or (2) final solution set covers ≥3 distinct objective tradeoff regions when using objective-based frontier types

## Assumptions

- The existing FrontierType enum can be extended to include new types (objective, hybrid, cartesian)
- Objective scores follow an established data structure from the 026-objective-scores feature
- The upstream GEPA library provides reference implementations for frontier tracking and evaluation policies
- Users understand multi-objective optimization concepts when using advanced frontier types
