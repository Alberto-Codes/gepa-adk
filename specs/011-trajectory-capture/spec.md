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

**Independent Test**: Can be tested by running an agent that modifies session state, extracting trajectory, and verifying state delta dictionaries (changed key-value pairs) are recorded.

**Acceptance Scenarios**:

1. **Given** a TrajectoryConfig with include_state_deltas=True, **When** the agent modifies session state, **Then** the trajectory includes state delta dictionaries with changed key-value pairs
2. **Given** a TrajectoryConfig with include_state_deltas=False, **When** the agent modifies session state, **Then** state changes are not captured in the trajectory
3. **Given** multiple state modifications in sequence, **When** trajectory is extracted, **Then** each delta dictionary is captured in chronological order

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

### User Story 4 - Truncate Large Values (Priority: P2)

As a gepa-adk user working with tools that produce large outputs (DOM snapshots, screenshots, API responses), I want long string values to be automatically truncated so that trajectories remain manageable for reflection agents and don't consume excessive memory.

**Why this priority**: Browser automation, screenshot tools, and verbose APIs can produce multi-KB or even MB outputs that overwhelm reflection context. Truncation is essential for practical use.

**Independent Test**: Can be tested by creating a tool call with a 100KB result, extracting trajectory with truncation enabled, and verifying the result is truncated with a marker.

**Acceptance Scenarios**:

1. **Given** a TrajectoryConfig with max_string_length=1000, **When** a tool result exceeds 1000 characters, **Then** the value is truncated and ends with a marker like "...[truncated 99000 chars]"
2. **Given** a TrajectoryConfig with max_string_length=None, **When** tool results are very large, **Then** values are NOT truncated (opt-out)
3. **Given** nested data structures with large string values, **When** truncation is applied, **Then** large strings are truncated at all nesting levels
4. **Given** a tool result that is exactly at the limit, **When** truncation is applied, **Then** the value is NOT truncated (no off-by-one)

---

### User Story 5 - Capture Token Usage (Priority: P3)

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
- What happens when a value is both sensitive AND exceeds max_string_length? Redaction takes precedence; the value becomes "[REDACTED]" regardless of length.
- What happens when truncation is applied to non-string values (lists, dicts)? Only string values are truncated; complex types are processed recursively but not truncated as a whole.
- What happens when a base64 image (screenshot) is in the response? It gets truncated like any other string if it exceeds max_string_length.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a TrajectoryConfig dataclass to configure extraction behavior
- **FR-002**: TrajectoryConfig MUST support include_tool_calls boolean flag (default: True)
- **FR-003**: TrajectoryConfig MUST support include_state_deltas boolean flag (default: True)
- **FR-004**: TrajectoryConfig MUST support include_token_usage boolean flag (default: True)
- **FR-005**: TrajectoryConfig MUST support redact_sensitive boolean flag (default: True)
- **FR-006**: TrajectoryConfig MUST support customizable sensitive_keys tuple (default: ("password", "api_key", "token"))
- **FR-007**: System MUST provide an extract_trajectory function that takes a list of ADK Event objects, final_output string, and TrajectoryConfig
- **FR-008**: extract_trajectory MUST return an ADKTrajectory instance containing the requested trajectory data
- **FR-009**: Tool call extraction MUST capture tool name, arguments, and response for each call
- **FR-010**: State delta extraction MUST capture the delta dict containing changed key-value pairs for each state change
- **FR-011**: Token usage extraction MUST capture input_tokens, output_tokens, and total_tokens
- **FR-012**: Redaction MUST recursively process nested data structures (dicts and lists)
- **FR-013**: Redaction MUST replace sensitive values with a consistent redaction marker (e.g., "[REDACTED]")
- **FR-014**: System MUST gracefully handle missing or null data in ADK responses
- **FR-015**: TrajectoryConfig MUST support max_string_length integer or None (default: 10000)
- **FR-016**: Truncation MUST apply to string values exceeding max_string_length
- **FR-017**: Truncation MUST append a marker indicating how many characters were removed
- **FR-018**: Truncation MUST process nested data structures recursively
- **FR-019**: Redaction MUST take precedence over truncation (sensitive values are redacted, not truncated)

### Key Entities

- **TrajectoryConfig**: Configuration object controlling which trajectory data to capture and how to handle sensitive/large data. Key attributes: include_tool_calls, include_state_deltas, include_token_usage, redact_sensitive, sensitive_keys, max_string_length.
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
- **SC-007**: Large string values (DOM snapshots, screenshots, verbose outputs) are truncated to max_string_length when configured
- **SC-008**: Truncated values clearly indicate the original length via marker (e.g., "...[truncated 50000 chars]")

## Assumptions

- The ADK RunnerResponse object provides access to tool_calls, state_deltas, and usage information through documented attributes
- Tool calls in ADK responses include name, args, and response fields (or equivalent)
- The redaction marker "[REDACTED]" is sufficient for all use cases; custom markers are not required initially
- Exact key matching for sensitive fields is acceptable; regex or fuzzy matching is not required for MVP
- The feature will be used primarily for passing context to reflection agents, not for audit logging
