# Feature Specification: Required Field Preservation for Output Schema Evolution

**Feature Branch**: `198-schema-field-preservation`
**Created**: 2026-01-22
**Status**: Draft
**Input**: GitHub Issue #190 - Add required field preservation for output_schema evolution

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Critical Fields in Critic Agents (Priority: P1)

As a gepa-adk user evolving critic agents, I need the `score` and `feedback` fields to remain intact during schema evolution so that the evolution engine continues to function correctly.

Critic agents are the backbone of evolution workflows. The `SchemaBasedScorer` and `CriticScorer` depend on extracting numeric scores from the output schema. If evolution removes or changes the type of `score`, subsequent evolution runs will fail completely.

**Why this priority**: Without this, schema evolution can break the entire evolution pipeline. This is a critical stability requirement.

**Independent Test**: Can be fully tested by evolving a critic agent with `required_fields=["score"]` and verifying that mutations removing `score` are rejected while other fields can evolve freely.

**Acceptance Scenarios**:

1. **Given** a critic agent with output_schema containing "score" (float) and "feedback" (str), **When** schema_constraints specifies `required_fields=["score", "feedback"]` and the reflection agent proposes a schema without "score", **Then** the proposed schema is rejected and the original schema is preserved with a warning logged.

2. **Given** a critic agent with output_schema containing "score", "feedback", and "details" fields, **When** schema_constraints only requires "score" and "feedback", and the reflection agent proposes removing "details", **Then** the proposed schema is accepted and evolution proceeds normally.

3. **Given** a critic agent with schema constraints configured, **When** evolution completes multiple iterations, **Then** all required fields remain present in the final evolved schema.

---

### User Story 2 - Preserve Field Types During Evolution (Priority: P2)

As a gepa-adk user, I need to ensure that certain fields maintain their data types during evolution so that downstream consumers can reliably parse the output.

For example, a `score` field must remain numeric (float or int) and an `order_id` must remain a string. Type changes would break integrations that depend on specific data formats.

**Why this priority**: Type preservation prevents subtle runtime errors in downstream systems. Important but secondary to field existence.

**Independent Test**: Can be fully tested by evolving an agent with `preserve_types={"score": float}` and verifying that mutations changing `score` to `str` are rejected.

**Acceptance Scenarios**:

1. **Given** an agent with output_schema where "score" is float, **When** schema_constraints specifies `preserve_types={"score": float}` and the reflection agent proposes "score: str", **Then** the proposed schema is rejected and a type mismatch warning is logged.

2. **Given** an agent with output_schema where "total" is float, **When** schema_constraints specifies `preserve_types={"total": (float, int)}` (allowing compatible numeric types) and the reflection agent proposes "total: int", **Then** the proposed schema is accepted.

3. **Given** a field with no type constraint, **When** the reflection agent proposes changing its type, **Then** the change is accepted.

---

### User Story 3 - Preserve Field Constraints/Bounds (Priority: P3)

As a gepa-adk user, I need to optionally preserve field validation constraints (like min/max bounds) during evolution so that evolved schemas maintain business rules.

For example, a `score` field with `ge=0.0, le=1.0` should keep those bounds to ensure scores remain valid percentages.

**Why this priority**: Constraint preservation is a refinement that ensures data quality. Useful but less critical than field existence and type preservation.

**Independent Test**: Can be fully tested by evolving an agent with bound constraints and verifying the bounds are preserved in the final schema.

**Acceptance Scenarios**:

1. **Given** an agent with "score" field having constraints `ge=0.0, le=1.0`, **When** constraint preservation is enabled for "score" and evolution proposes removing the bounds, **Then** the proposal is rejected and bounds are preserved.

2. **Given** an agent with "score" field having constraints, **When** constraint preservation is NOT enabled, **Then** the reflection agent may modify or remove constraints freely.

---

### Edge Cases

- What happens when ALL proposed changes are rejected due to constraints? The original schema is preserved unchanged, and a warning indicates no valid mutation was found for this iteration.
- What happens when a required field exists but with an incompatible type? The mutation is rejected, same as a missing field.
- What happens when constraints specify a field that doesn't exist in the original schema? The constraint is ignored with a debug log (cannot require a field that was never there).
- What happens when the user specifies contradictory constraints? The system validates constraints at configuration time and raises a clear error before evolution begins.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to specify required fields that cannot be removed during output_schema evolution via a `schema_constraints` parameter in the `evolve()` function.
- **FR-002**: System MUST reject schema mutations that remove any field listed in `required_fields`.
- **FR-003**: System MUST allow users to specify field type constraints via `preserve_types` mapping (field name to allowed type or tuple of types).
- **FR-004**: System MUST reject schema mutations that change a field's type to one not in the allowed types.
- **FR-005**: System MUST log a warning when a schema mutation is rejected due to constraint violations.
- **FR-006**: System MUST preserve the original schema when a mutation is rejected.
- **FR-007**: System MUST allow non-constrained fields to evolve freely (add, remove, modify).
- **FR-008**: System MUST validate constraint configuration at evolution start and raise clear errors for invalid configurations (e.g., referencing non-existent fields, contradictory constraints).
- **FR-009**: System SHOULD support type compatibility checking (e.g., `int` is compatible with `float` for numeric fields) when specified via tuple of types.
- **FR-010**: System MAY support field constraint/bounds preservation as an optional enhancement. **DEFERRED**: Not implemented in this iteration; architecture supports future extension.

### Key Entities

- **SchemaConstraints**: Configuration object specifying which fields must be preserved, their required types, and optionally their validation bounds.
- **OutputSchemaHandler**: The component handler responsible for applying schema mutations, which will gain validation logic against constraints.
- **ValidationResult**: Outcome of constraint checking (valid/invalid with reasons).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of schema mutations that would remove a required field are rejected and logged.
- **SC-002**: 100% of schema mutations that would change a constrained field's type to an incompatible type are rejected and logged.
- **SC-003**: Non-constrained fields can still be freely evolved (add, remove, modify) in 100% of cases.
- **SC-004**: Users can configure and run schema-constrained evolution without any additional steps beyond specifying `schema_constraints` parameter.
- **SC-005**: Invalid constraint configurations are detected and reported before evolution begins (fail-fast).
- **SC-006**: Existing evolution workflows without `schema_constraints` continue to work unchanged (backward compatibility).

## Assumptions

- Users are familiar with Pydantic schema definitions and understand field types.
- The `OutputSchemaHandler` is the appropriate integration point for validation logic.
- Constraint validation happens at the point of applying mutations, not during reflection proposal generation.
- The reflection agent is NOT modified to be aware of constraints (validation is post-hoc).
- Compatible numeric types means `int` can satisfy a `float` constraint (widening is allowed).

## Dependencies

- Depends on existing `OutputSchemaHandler` in `component_handlers.py`.
- Depends on existing `evolve()` API in `api.py`.
- Related to issue #49 which mentioned field preservation requirements.

## Out of Scope

- Modifying reflection agent prompts to be aware of constraints (future enhancement).
- Persisting constraint configurations (in-memory only per evolution run).
- GUI or interactive constraint configuration.
- Automatic detection of "critical" fields (user must explicitly specify).
