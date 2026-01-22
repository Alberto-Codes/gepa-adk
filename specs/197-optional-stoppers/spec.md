# Feature Specification: Optional Stoppers (MaxEvaluations and File-based)

**Feature Branch**: `197-optional-stoppers`
**Created**: 2026-01-22
**Status**: Draft
**Input**: User description: "MaxEvaluationsStopper and FileStopper - optional stoppers for API budget control and external orchestration"
**Parent Issue**: #51 - Pluggable stop conditions

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Control API Costs with Evaluation Limits (Priority: P1)

As a gepa-adk user running evolution on expensive models, I want to limit the total number of evaluations so that I can control API costs and stay within budget.

**Why this priority**: API cost control is the primary driver for this stopper. Users running evolution with paid model APIs need predictable cost limits to prevent runaway expenses.

**Independent Test**: Can be fully tested by configuring an evaluation limit, running evolution, and verifying it stops at the specified count. Delivers immediate value by preventing unexpected API costs.

**Acceptance Scenarios**:

1. **Given** a MaxEvaluationsStopper configured with 100 evaluations, **When** the evolution reaches 100 total evaluations, **Then** the evolution stops immediately
2. **Given** a MaxEvaluationsStopper configured with 100 evaluations, **When** the evolution has completed 50 evaluations, **Then** the evolution continues running
3. **Given** a MaxEvaluationsStopper with an invalid value (0 or negative), **When** the stopper is created, **Then** an appropriate error is raised

---

### User Story 2 - External Orchestration with File-based Stop Signal (Priority: P2)

As a system operator running gepa-adk in an automated pipeline, I want to signal a stop by creating a file so that external orchestration tools can gracefully terminate evolution without sending process signals.

**Why this priority**: File-based stopping enables integration with external systems (CI/CD, job schedulers, monitoring tools) that cannot easily send process signals but can create files.

**Independent Test**: Can be fully tested by configuring a stop file path, creating the file during evolution, and verifying the evolution stops. Delivers value for automated pipelines.

**Acceptance Scenarios**:

1. **Given** a FileStopper configured with a stop file path, **When** the stop file exists, **Then** the evolution stops
2. **Given** a FileStopper configured with a stop file path, **When** the stop file does not exist, **Then** the evolution continues running
3. **Given** a FileStopper configured with remove_on_stop enabled, **When** the stop file exists and evolution stops, **Then** the stop file is automatically removed
4. **Given** a FileStopper configured with remove_on_stop disabled (default), **When** the stop file exists and evolution stops, **Then** the stop file remains in place

---

### User Story 3 - Manual Stop File Cleanup (Priority: P3)

As a developer debugging evolution runs, I want to manually remove the stop file so that I can reset the stop condition without restarting the system.

**Why this priority**: This is a convenience feature for development and debugging workflows, not critical for production use.

**Independent Test**: Can be tested by creating a stop file, calling the cleanup method, and verifying the file is removed.

**Acceptance Scenarios**:

1. **Given** a FileStopper with an existing stop file, **When** the cleanup method is called, **Then** the stop file is removed
2. **Given** a FileStopper with no existing stop file, **When** the cleanup method is called, **Then** no error occurs (idempotent operation)

---

### Edge Cases

- What happens when the evaluation count exceeds the limit between checks? (Should still stop on next check)
- How does FileStopper handle the stop file being removed between existence check and deletion? (Should handle gracefully)
- What happens if the stop file path is in a directory that doesn't exist? (Should handle gracefully - no stop triggered)
- How does the system behave when multiple stoppers are combined? (Relies on existing composite stopper functionality)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a stopper that stops evolution after a configurable number of total evaluations
- **FR-002**: System MUST reject invalid evaluation limits (zero or negative values) at configuration time
- **FR-003**: System MUST provide a stopper that stops evolution when a specified file exists
- **FR-004**: System MUST support optional automatic removal of the stop file after triggering a stop
- **FR-005**: System MUST provide a method to manually remove the stop file
- **FR-006**: Both stoppers MUST conform to the existing stopper protocol/interface
- **FR-007**: Both stoppers MUST work seamlessly with the existing CompositeStopper for combining stop conditions

### Key Entities

- **MaxEvaluationsStopper**: A stopper that monitors total evaluation count and triggers stop when a threshold is reached. Key attributes: maximum evaluation count (positive integer)
- **FileStopper**: A stopper that monitors for the existence of a file at a specified path. Key attributes: file path, optional remove-on-stop behavior
- **StopperState**: Existing entity that provides evaluation count information to stoppers

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure an evaluation limit and evolution stops within 1 check cycle of reaching the limit
- **SC-002**: Users can signal a stop via file creation and evolution stops within 1 check cycle of file appearing
- **SC-003**: Both stoppers integrate with existing stopper infrastructure without requiring changes to the evolution engine
- **SC-004**: Stop file cleanup (automatic or manual) succeeds 100% of the time when file exists and fails gracefully when file doesn't exist

## Assumptions

- The StopperState entity already includes `total_evaluations` tracking (per existing stopper infrastructure)
- The stopper protocol/interface already exists and defines the callable signature
- CompositeStopper from feature #205 is available for combining multiple stoppers
- File system permissions allow reading/writing to the configured stop file path
