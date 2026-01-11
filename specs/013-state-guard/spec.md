# Feature Specification: StateGuard for State Key Preservation

**Feature Branch**: `013-state-guard`  
**Created**: January 11, 2026  
**Status**: Draft  
**Input**: User description: "Implement StateGuard for state key preservation - safe instruction mutation so evolved instructions do not break ADK state injection"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Repair Missing State Tokens (Priority: P1)

As a gepa-adk user running instruction evolution, I want missing state tokens to be automatically repaired when reflection inadvertently removes them, so that my evolved instructions continue to work with ADK state injection.

**Why this priority**: This is the core safety mechanism. Without token repair, evolved instructions could silently break at runtime when ADK tries to inject state values into missing placeholders. This is the most common failure mode during instruction mutation.

**Independent Test**: Can be fully tested by providing an original instruction containing `{current_step}` token, mutating it to remove the token, and verifying StateGuard re-appends the missing token.

**Acceptance Scenarios**:

1. **Given** an original instruction containing `{current_step}` token, **When** reflection produces a mutated instruction that removes the token, **Then** StateGuard re-appends the missing token to the result
2. **Given** an original instruction with multiple required tokens `{user_id}` and `{context}`, **When** mutation removes one token, **Then** only the missing token is re-appended
3. **Given** an instruction with no required tokens removed, **When** StateGuard validates it, **Then** the instruction remains unchanged

---

### User Story 2 - Escape Unauthorized Tokens (Priority: P2)

As a gepa-adk user, I want new unauthorized tokens introduced by reflection to be escaped, so that they don't accidentally trigger ADK state injection with undefined keys.

**Why this priority**: This prevents potential injection attacks or undefined behavior when reflection introduces new placeholder patterns. While less common than missing tokens, unauthorized tokens could cause runtime errors or security issues.

**Independent Test**: Can be fully tested by providing a mutated instruction that introduces a new `{malicious}` token not present in the original, and verifying it becomes `{{malicious}}` (escaped).

**Acceptance Scenarios**:

1. **Given** reflection adds a new `{malicious}` token not in the original instruction, **When** StateGuard validates the instruction, **Then** the token becomes `{{malicious}}` (double-braced/escaped)
2. **Given** reflection adds multiple new unauthorized tokens, **When** StateGuard validates, **Then** all unauthorized tokens are escaped
3. **Given** a new token that matches a required token in the allowlist, **When** StateGuard validates, **Then** the token is NOT escaped (it's authorized)

---

### User Story 3 - Preserve All Required Tokens (Priority: P1)

As a gepa-adk user configuring StateGuard, I want to specify a list of required tokens that must always be present, so that I can ensure critical state keys are never lost during evolution.

**Why this priority**: This is tied to P1 as it defines the contract for what tokens are considered "required" - it's the configuration mechanism that drives the repair behavior.

**Independent Test**: Can be fully tested by configuring `required_tokens=["{user_id}", "{context}"]` and verifying that any mutation missing these tokens gets them re-appended.

**Acceptance Scenarios**:

1. **Given** `required_tokens=["{user_id}", "{context}"]` is configured, **When** an instruction is validated that's missing `{user_id}`, **Then** `{user_id}` is appended to the result
2. **Given** required tokens are configured, **When** all required tokens are already present, **Then** the instruction remains unchanged
3. **Given** an empty `required_tokens` list, **When** validation occurs, **Then** only tokens from the original instruction are considered for repair

---

### User Story 4 - Configurable Behavior (Priority: P3)

As a gepa-adk user, I want to configure whether repair and escaping behaviors are enabled, so that I can customize StateGuard for different use cases.

**Why this priority**: This is a nice-to-have flexibility feature. Most users will want both behaviors enabled (the default), but power users may need fine-grained control.

**Independent Test**: Can be tested by setting `repair_missing=False` and verifying missing tokens are NOT repaired, or setting `escape_unauthorized=False` and verifying new tokens are NOT escaped.

**Acceptance Scenarios**:

1. **Given** `repair_missing=False` is configured, **When** a token is missing from mutated instruction, **Then** the token is NOT repaired
2. **Given** `escape_unauthorized=False` is configured, **When** new unauthorized tokens appear, **Then** they are NOT escaped
3. **Given** both behaviors are disabled, **When** validation occurs, **Then** the mutated instruction is returned unchanged

---

### Edge Cases

- What happens when the original instruction has no tokens? → Validation passes through unchanged; any new tokens in mutation are escaped (if enabled)
- What happens when a token appears multiple times in the original? → Token is considered "present" if it appears at least once; repair adds it once if completely missing
- What happens when the mutated instruction is empty? → Missing required tokens from original are appended to the empty result
- How does system handle nested braces like `{{already_escaped}}`? → The regex pattern `\{(\w+)\}` only matches single-braced tokens, so already-escaped tokens are ignored
- What happens with malformed tokens like `{invalid-name}` (with hyphen)? → The `\w+` pattern only matches word characters (letters, digits, underscore), so hyphens are not matched as tokens
- What about ADK prefixed tokens like `{app:user_name}`? → MVP pattern matches simple tokens only; prefixed tokens (`app:`, `user:`, `temp:`) pass through unchanged but can be added to `required_tokens` for explicit protection
- What about optional tokens like `{name?}`? → The `?` suffix is ADK-specific for "return empty if not found"; MVP treats `{name?}` as not matching (no `?` in `\w+`), which is safe (ADK handles it)
- What about artifact tokens like `{artifact.file}`? → Artifact references have different semantics in ADK and are not state variables; they pass through unchanged

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST identify all state tokens in an instruction using the pattern `{token_name}` where `token_name` consists of word characters (letters, digits, underscores)
- **FR-002**: System MUST detect tokens present in the original instruction but missing from the mutated instruction
- **FR-003**: System MUST detect new tokens in the mutated instruction that were not present in the original
- **FR-004**: System MUST re-append missing required tokens to the mutated instruction when `repair_missing=True`
- **FR-005**: System MUST escape unauthorized new tokens by doubling the braces (`{x}` → `{{x}}`) when `escape_unauthorized=True`
- **FR-006**: System MUST allow configuration of required tokens via a list parameter
- **FR-007**: System MUST allow toggling of repair behavior via `repair_missing` parameter (default: True)
- **FR-008**: System MUST allow toggling of escape behavior via `escape_unauthorized` parameter (default: True)
- **FR-009**: System MUST NOT modify tokens that are both in the required list AND newly introduced (authorized additions)
- **FR-010**: System MUST preserve the original content of the mutated instruction, only appending or escaping as needed

### Key Entities

- **StateGuard**: The validator component that checks and repairs mutated instructions. Configurable with required tokens and behavior flags.
- **Token**: A placeholder pattern in the format `{name}` that ADK uses for state injection. Identified by regex `\{(\w+)\}`.
- **Original Instruction**: The instruction before mutation, used as the reference for which tokens are authorized.
- **Mutated Instruction**: The instruction after reflection/evolution, which may have lost or gained tokens.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of missing required tokens are detected and repaired when `repair_missing=True`
- **SC-002**: 100% of unauthorized new tokens are escaped when `escape_unauthorized=True`
- **SC-003**: Zero false positives - tokens present in both original and mutated are never modified
- **SC-004**: Validation completes in under 1ms wall clock time (single-threaded) for typical instruction lengths (under 10KB)
- **SC-005**: All three Gherkin scenarios from the original issue pass acceptance testing

## Assumptions

- Token names follow the `\w+` pattern (word characters only: a-z, A-Z, 0-9, underscore)
- The `{{escaped}}` double-brace format is the standard way to escape tokens in the target system (confirmed by ADK source: `instructions_utils.py`)
- Required tokens are specified in the format `{token_name}` (with braces) for clarity
- When repairing missing tokens, appending to the end with `\n\n{token}` is acceptable formatting
- The original instruction is always available when validating a mutation
- ADK prefixed tokens (`{app:x}`, `{user:x}`, `{temp:x}`) and optional tokens (`{x?}`) are out of scope for MVP but can be protected via explicit `required_tokens` configuration
- Artifact references (`{artifact.filename}`) are a separate concern and not handled by StateGuard
