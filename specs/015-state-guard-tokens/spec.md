# Feature Specification: Extended State Token Detection

**Feature Branch**: `015-state-guard-tokens`  
**Created**: 2026-01-12  
**Status**: Draft  
**Input**: User description: "Extend StateGuard to detect ADK prefixed and optional tokens ({app:x}, {user:x}, {temp:x}, {name?})"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Protect Prefixed State Tokens (Priority: P1)

As a gepa-adk user using ADK prefixed state tokens like `{app:settings}`, `{user:preferences}`, or `{temp:session_data}`, I want StateGuard to detect and protect these tokens, so that when an LLM reflection modifies my instruction, my prefixed state tokens are not accidentally removed or broken.

**Why this priority**: Prefixed state tokens are commonly used in production ADK applications for scoped state management. Failure to protect these tokens breaks critical application functionality (accessing app-wide settings, user-specific preferences, or session data).

**Independent Test**: Can be fully tested by providing an instruction containing `{app:config}`, mutating it to remove the token, and verifying the token is re-appended. Delivers the core value of protecting ADK-scoped state.

**Acceptance Scenarios**:

1. **Given** a StateGuard with `required_tokens=["{app:settings}"]`, **When** the original instruction contains `{app:settings}` and the mutated instruction removes it, **Then** the token `{app:settings}` is re-appended to the result.

2. **Given** a StateGuard with `required_tokens=["{user:api_key}"]`, **When** the original instruction contains `{user:api_key}` and the mutated instruction preserves it, **Then** the result is unchanged.

3. **Given** a StateGuard with `required_tokens=["{temp:session_id}"]`, **When** the original instruction contains `{temp:session_id}` and the mutated instruction removes it, **Then** the token `{temp:session_id}` is re-appended to the result.

---

### User Story 2 - Escape Unauthorized Prefixed Tokens (Priority: P2)

As a gepa-adk user, I want StateGuard to escape newly introduced prefixed tokens that are not authorized, so that malicious or unintended state injections like `{user:password}` introduced by LLM reflection are rendered harmless.

**Why this priority**: This is a security feature that prevents prompt injection attacks via unauthorized state access. While slightly lower priority than P1 (repair is more commonly needed), this protects against potential security vulnerabilities.

**Independent Test**: Can be fully tested by providing an instruction without `{user:secret}`, mutating it to add `{user:secret}`, and verifying the token becomes `{{user:secret}}`.

**Acceptance Scenarios**:

1. **Given** a StateGuard with `escape_unauthorized=True`, **When** the mutated instruction introduces `{user:api_key}` that was not in the original, **Then** the token becomes `{{user:api_key}}` (double-braced/escaped).

2. **Given** a StateGuard with `escape_unauthorized=True` and `required_tokens=["{user:api_key}"]`, **When** the mutated instruction introduces `{user:api_key}`, **Then** the token is NOT escaped (it's authorized).

---

### User Story 3 - Protect Optional Tokens (Priority: P3)

As a gepa-adk user using optional tokens like `{name?}`, I want StateGuard to detect and protect these tokens, so that optional state placeholders are preserved during instruction evolution.

**Why this priority**: Optional tokens (`{var?}`) are less commonly used than simple or prefixed tokens, but still represent valid ADK state patterns that should be protected.

**Independent Test**: Can be fully tested by providing an instruction containing `{name?}`, mutating it to remove the token, and verifying the token is re-appended.

**Acceptance Scenarios**:

1. **Given** a StateGuard with `required_tokens=["{name?}"]`, **When** the original instruction contains `{name?}` and the mutated instruction removes it, **Then** the token `{name?}` is re-appended to the result.

2. **Given** a StateGuard with `escape_unauthorized=True`, **When** the mutated instruction introduces `{unauthorized?}` not in the original, **Then** the token becomes `{{unauthorized?}}`.

---

### Edge Cases

- What happens when a prefixed token contains invalid characters (e.g., `{app:invalid-name}`)? (Should not match - ADK requires valid Python identifiers after prefix)
- How does the system handle mixed token formats in the same instruction (e.g., `{simple}`, `{app:scoped}`, `{optional?}`)? (All should be independently detected and processed)
- What happens with nested or malformed braces (e.g., `{{already_escaped}}`, `{incomplete`)? (Already-escaped tokens should pass through unchanged; incomplete tokens should be ignored)
- How does the system handle the `artifact.` prefix (e.g., `{artifact.file_name}`)? (Artifact references have different semantics and should NOT be matched by StateGuard)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect prefixed state tokens with `app:`, `user:`, or `temp:` prefixes (e.g., `{app:settings}`, `{user:name}`, `{temp:data}`)
- **FR-002**: System MUST detect optional state tokens with `?` suffix (e.g., `{name?}`, `{user_id?}`)
- **FR-003**: System MUST support combined prefix and optional syntax (e.g., `{app:config?}`)
- **FR-004**: System MUST repair missing prefixed/optional tokens when `repair_missing=True`
- **FR-005**: System MUST escape unauthorized prefixed/optional tokens when `escape_unauthorized=True`
- **FR-006**: System MUST maintain backward compatibility with existing simple token detection (`{simple_name}`)
- **FR-007**: System MUST NOT match artifact references (e.g., `{artifact.file_name}`) as these have different semantics
- **FR-008**: System MUST NOT match already-escaped tokens (e.g., `{{token}}`)
- **FR-009**: System MUST only match tokens with valid Python identifiers (consistent with ADK's `_is_valid_state_name()`)

### Key Entities

- **Token Pattern**: Regex pattern used to identify valid ADK state tokens. Currently `\{(\w+)\}`, needs extension.
- **Token Prefix**: One of `app:`, `user:`, or `temp:` indicating scope of state storage.
- **Optional Marker**: The `?` suffix indicating a token that may not exist in state.
- **Required Tokens**: User-configured list of tokens that must be preserved during mutation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All prefixed token formats (`{app:x}`, `{user:x}`, `{temp:x}`) are correctly detected and repaired when missing
- **SC-002**: All optional token formats (`{x?}`) are correctly detected and repaired when missing
- **SC-003**: Combined formats (`{app:x?}`) are correctly detected and repaired when missing
- **SC-004**: Existing unit tests for simple tokens (`{x}`) continue to pass (backward compatibility)
- **SC-005**: No false positives on artifact references (`{artifact.x}`) or already-escaped tokens (`{{x}}`)
- **SC-006**: Token detection performance remains under 1ms for typical instruction sizes (10KB strings)
