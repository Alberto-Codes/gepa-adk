# Feature Specification: Trajectory Capture from ADK Sessions

**Feature Branch**: `011-trajectory-capture`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: User description: "Implement trajectory capture from ADK sessions - rich trajectory data including tool calls, state deltas, and sensitive data redaction for reflection context"  
**Parent Issue**: GitHub Issue #11

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Tool Call History (Priority: P1)

As a gepa-adk user running agent evaluations, I want to capture detailed tool call information from ADK sessions so that reflection agents have full context about what tools the agent used, with what arguments, and what responses were received.

**Why this priority**: Tool calls are the primary actions an agent takes. Without capturing them, reflection has no insight into agent behavior and decision-making. This is the core value proposition of trajectory capture.

**Independent Test**: Can be fully tested by running an agent that uses tools, extracting the trajectory, and verifying tool_name, arguments, and response are present for each call.

**Acceptance Scenarios**:

1. **Given** a TrajectoryConfig with include_tool_calls=True, **When** the agent uses tools during evaluation, **Then** the trajectory includes tool name, args, and response for each tool call
2. **Given** a TrajectoryConfig with include_tool_calls=False, **When** the agent uses tools during evaluation, **Then** the trajectory does not include any tool call information
3. **Given** an agent that makes multiple tool calls, **When** trajectory is extracted, **Then** all tool calls are captured in chronological order

---

### User Story 2 - Capture State Deltas (Priority: P2)

As a gepa-adk user, I want to capture state changes that occur during agent execution so that reflection can understand how the agent modified session state over time.

**Why this priority**: State deltas provide context about side effects and data transformations. Important for understanding agent behavior but secondary to tool calls which represent explicit actions.

**Independent Test**: Can be tested by running an agent that modifies session state, extracting trajectory, and verifying before/after state changes are recorded.

**Acceptance Scenarios**:

1. **Given** a TrajectoryConfig with include_state_deltas=True, **When** the agent modifies session state, **Then** the trajectory includes before/after state changes
2. **Given** a TrajectoryConfig with include_state_deltas=False, **When** the agent modifies session state, **Then** state changes are not captured in the trajectory
3. **Given** multiple state modifications in sequence, **When** trajectory is extracted, **Then** each delta is captured with the previous and new values

---

### User Story 3 - Redact Sensitive Data (Priority: P2)

As a gepa-adk user handling data that may contain PII or secrets, I want sensitive fields to be automatically redacted from trajectories so that reflection agents don't have access to or inadvertently expose sensitive information.

**Why this priority**: Security and privacy are critical but only relevant when sensitive data is present. This is a safety net feature that runs after capture.

**Independent Test**: Can be tested by including known sensitive keys (password, api_key, token) in tool call args or state, extracting trajectory with redaction enabled, and verifying values are redacted.

**Acceptance Scenarios**:

1. **Given** a TrajectoryConfig with redact_sensitive=True and default sensitive_keys, **When** trajectories contain fields matching "password", "api_key", or "token", **Then** those field values are replaced with a redaction marker
2. **Given** a TrajectoryConfig with custom sensitive_keys=["ssn", "credit_card"], **When** trajectories contain those fields, **Then** those field values are redacted
3. **Given** a TrajectoryConfig with redact_sensitive=False, **When** trajectories contain sensitive fields, **Then** values remain unredacted
4. **Given** nested data structures containing sensitive keys, **When** redaction is applied, **Then** sensitive values are redacted at all nesting levels

---

### User Story 4 - Capture Token Usage (Priority: P3)

As a gepa-adk user monitoring costs and efficiency, I want to capture token usage statistics so that I can analyze model consumption patterns and optimize prompts.

**Why this priority**: Token usage is useful for cost analysis and optimization but is supplementary information that doesn't directly impact reflection quality.

**Independent Test**: Can be tested by running an agent, extracting trajectory with token usage enabled, and verifying prompt_tokens and completion_tokens are present.

**Acceptance Scenarios**:

1. **Given** a TrajectoryConfig with include_token_usage=True, **When** the agent completes execution, **Then** the trajectory includes prompt_tokens and completion_tokens
2. **Given** a TrajectoryConfig with include_token_usage=False, **When** trajectory is extracted, **Then** token usage information is not included

---

### Edge Cases

- What happens when the ADK response has no tool calls? The trajectory should return an empty tool_calls list, not error.
- What happens when state_deltas is not available in the response? The trajectory should gracefully handle missing data and return an empty or absent state_deltas field.
- What happens when sensitive key patterns match partial field names (e.g., "password_hash" vs "password")? The default behavior matches exact key names; partial matching is not performed unless explicitly configured.
- What happens when token usage information is not available? The trajectory should omit or provide null values for token fields rather than erroring.
- What happens when trajectory extraction is called with an invalid/null response? The function should raise a clear validation error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a TrajectoryConfig dataclass to configure extraction behavior
- **FR-002**: TrajectoryConfig MUST support include_tool_calls boolean flag (default: True)
- **FR-003**: TrajectoryConfig MUST support include_state_deltas boolean flag (default: True)
- **FR-004**: TrajectoryConfig MUST support include_token_usage boolean flag (default: True)
- **FR-005**: TrajectoryConfig MUST support redact_sensitive boolean flag (default: True)
- **FR-006**: TrajectoryConfig MUST support customizable sensitive_keys list (default: ["password", "api_key", "token"])
- **FR-007**: System MUST provide an extract_trajectory function that takes an ADK response and config
- **FR-008**: extract_trajectory MUST return a dictionary containing the requested trajectory data
- **FR-009**: Tool call extraction MUST capture tool name, arguments, and response for each call
- **FR-010**: State delta extraction MUST capture before and after values for each state change
- **FR-011**: Token usage extraction MUST capture prompt_tokens and completion_tokens
- **FR-012**: Redaction MUST recursively process nested data structures (dicts and lists)
- **FR-013**: Redaction MUST replace sensitive values with a consistent redaction marker (e.g., "[REDACTED]")
- **FR-014**: System MUST gracefully handle missing or null data in ADK responses

### Key Entities

- **TrajectoryConfig**: Configuration object controlling which trajectory data to capture and how to handle sensitive data. Key attributes: include_tool_calls, include_state_deltas, include_token_usage, redact_sensitive, sensitive_keys.
- **Trajectory**: The extracted data dictionary containing tool_calls, state_deltas, and token_usage based on configuration.
- **ToolCall**: Represents a single tool invocation with name, args, and response.
- **StateDelta**: Represents a state change with before and after values.
- **TokenUsage**: Represents model token consumption with prompt_tokens and completion_tokens.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can extract trajectory data from any ADK RunnerResponse within a single function call
- **SC-002**: All configured trajectory components (tool calls, state deltas, token usage) are accurately captured
- **SC-003**: Sensitive data redaction correctly identifies and masks 100% of configured sensitive keys at any nesting depth
- **SC-004**: Trajectory extraction completes without errors when optional data is missing from the ADK response
- **SC-005**: Reflection agents receive complete context about agent behavior when trajectories are passed to them
- **SC-006**: No sensitive data (matching configured keys) appears in extracted trajectories when redaction is enabled

## Assumptions

- The ADK RunnerResponse object provides access to tool_calls, state_deltas, and usage information through documented attributes
- Tool calls in ADK responses include name, args, and response fields (or equivalent)
- The redaction marker "[REDACTED]" is sufficient for all use cases; custom markers are not required initially
- Exact key matching for sensitive fields is acceptable; regex or fuzzy matching is not required for MVP
- The feature will be used primarily for passing context to reflection agents, not for audit logging
