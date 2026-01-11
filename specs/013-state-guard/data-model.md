# Data Model: StateGuard for State Key Preservation

**Feature**: 013-state-guard  
**Date**: January 11, 2026  
**Status**: Complete

## Overview

StateGuard is a stateless validation utility. It does not persist data or define domain entities. This document describes the internal data structures used during validation.

## Entities

### StateGuard (Class)

The main validation component that checks and repairs mutated instructions.

| Attribute | Type | Description | Default |
|-----------|------|-------------|---------|
| `required_tokens` | `list[str]` | Tokens that must always be present (with braces, e.g., `"{user_id}"`) | `[]` |
| `repair_missing` | `bool` | Whether to re-append missing tokens | `True` |
| `escape_unauthorized` | `bool` | Whether to escape new unauthorized tokens | `True` |
| `_token_pattern` | `re.Pattern` | Compiled regex for token detection (private) | `re.compile(r"\{(\w+)\}")` |

### Token (Conceptual)

A placeholder pattern in the format `{name}` used for ADK state injection.

| Property | Type | Description |
|----------|------|-------------|
| `full_token` | `str` | The complete token including braces, e.g., `"{current_step}"` |
| `token_name` | `str` | The name only, e.g., `"current_step"` |

**Note**: Token is not a class - it's extracted via regex. The distinction between `full_token` and `token_name` is handled in code.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      StateGuard.validate()                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Input:                                                             │
│  ┌────────────────────┐    ┌────────────────────┐                  │
│  │ original: str      │    │ mutated: str       │                  │
│  │ "Use {user_id}..." │    │ "Use the user..." │                  │
│  └────────────────────┘    └────────────────────┘                  │
│           │                         │                               │
│           ▼                         ▼                               │
│  ┌────────────────────┐    ┌────────────────────┐                  │
│  │ Extract tokens     │    │ Extract tokens     │                  │
│  │ {"user_id"}        │    │ {"malicious"}      │                  │
│  └────────────────────┘    └────────────────────┘                  │
│           │                         │                               │
│           └──────────┬──────────────┘                               │
│                      ▼                                              │
│           ┌─────────────────────┐                                  │
│           │ Set Operations      │                                  │
│           │ missing = orig - mut│                                  │
│           │ new = mut - orig    │                                  │
│           └─────────────────────┘                                  │
│                      │                                              │
│         ┌────────────┼────────────┐                                │
│         ▼            │            ▼                                │
│  ┌─────────────┐     │    ┌─────────────┐                         │
│  │ Repair      │     │    │ Escape      │                         │
│  │ (append)    │     │    │ (double {}) │                         │
│  └─────────────┘     │    └─────────────┘                         │
│         │            │            │                                │
│         └────────────┴────────────┘                                │
│                      │                                              │
│                      ▼                                              │
│           ┌─────────────────────┐                                  │
│           │ Output: str         │                                  │
│           │ "Use the user...    │                                  │
│           │                     │                                  │
│           │ {user_id}           │                                  │
│           │ {{malicious}}"      │                                  │
│           └─────────────────────┘                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## State Transitions

StateGuard is stateless - no state transitions. Each `validate()` call is independent.

## Validation Rules

### Token Name Validation

- Must match `\w+` pattern (letters, digits, underscore)
- Case-sensitive matching
- No length limits enforced

### Required Token Validation

- Tokens in `required_tokens` must include braces: `"{token}"` not `"token"`
- Tokens are normalized by stripping braces for comparison

### Repair Rules

- Only tokens from `required_tokens` that were in original AND missing from mutated are repaired
- Tokens not in `required_tokens` are NOT repaired even if missing
- Repair appends `\n\n{token}` to the result

### Escape Rules

- Only tokens in mutated but NOT in original are candidates for escaping
- Tokens in `required_tokens` are authorized (not escaped even if new)
- Escape replaces `{token}` with `{{token}}`

## Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                     StateGuard                              │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ required_tokens │  │ repair_missing│  │ escape_unauth │  │
│  │ list[str]       │  │ bool          │  │ bool          │  │
│  └─────────────────┘  └──────────────┘  └───────────────┘  │
│          │                                                  │
│          ▼                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  validate(original, mutated)         │   │
│  │  Uses: _token_pattern.findall() for extraction       │   │
│  │  Returns: repaired/escaped string                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Persistence

None. StateGuard is purely in-memory computation.
