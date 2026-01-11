# Quickstart: StateGuard for State Key Preservation

**Feature**: 013-state-guard  
**Date**: January 11, 2026

## Overview

StateGuard protects ADK state injection tokens during instruction evolution. When LLM reflection modifies instructions, it may accidentally remove required `{token}` placeholders or introduce new ones. StateGuard validates mutated instructions and:

1. **Repairs** missing required tokens by re-appending them
2. **Escapes** unauthorized new tokens to prevent injection issues

## Installation

StateGuard is included in the `gepa-adk` package - no additional installation required.

```python
from gepa_adk.utils.state_guard import StateGuard
```

## Basic Usage

### Simple Validation

```python
from gepa_adk.utils.state_guard import StateGuard

# Create guard with required tokens
guard = StateGuard(required_tokens=["{user_id}", "{context}"])

# Original instruction with tokens
original = "Hello {user_id}, your context is: {context}"

# Mutated instruction (LLM removed {context})
mutated = "Hello {user_id}, welcome!"

# Validate and repair
result = guard.validate(original, mutated)
# result == "Hello {user_id}, welcome!\n\n{context}"
```

### Escaping Unauthorized Tokens

```python
guard = StateGuard(required_tokens=["{user_id}"])

original = "Process for {user_id}"
mutated = "Process for {user_id} with {malicious_token}"

result = guard.validate(original, mutated)
# result == "Process for {user_id} with {{malicious_token}}"
# Note: {malicious_token} became {{malicious_token}} (escaped)
```

### Configuring Behavior

```python
# Disable repair (only escape)
guard = StateGuard(
    required_tokens=["{user_id}"],
    repair_missing=False,
    escape_unauthorized=True
)

# Disable escaping (only repair)
guard = StateGuard(
    required_tokens=["{user_id}"],
    repair_missing=True,
    escape_unauthorized=False
)

# Passthrough mode (no modifications)
guard = StateGuard(
    repair_missing=False,
    escape_unauthorized=False
)
```

## Integration with Evolution Pipeline

### With MutationProposer

```python
from gepa_adk.utils.state_guard import StateGuard

class SafeMutationProposer:
    def __init__(self, base_proposer, required_tokens: list[str]):
        self.base_proposer = base_proposer
        self.guard = StateGuard(required_tokens=required_tokens)
    
    async def propose(self, instruction: str) -> str:
        # Get mutation from base proposer (LLM)
        mutated = await self.base_proposer.propose(instruction)
        
        # Validate and repair
        return self.guard.validate(instruction, mutated)
```

### With Reflection Agent

```python
guard = StateGuard(required_tokens=["{current_step}", "{user_input}"])

async def reflect_and_evolve(original_instruction: str) -> str:
    # LLM reflection may modify tokens
    evolved = await reflection_agent.evolve(original_instruction)
    
    # Ensure tokens are preserved
    safe_evolved = guard.validate(original_instruction, evolved)
    
    return safe_evolved
```

## API Reference

### StateGuard Class

```python
class StateGuard:
    def __init__(
        self,
        required_tokens: list[str] | None = None,
        repair_missing: bool = True,
        escape_unauthorized: bool = True,
    ) -> None:
        """Initialize StateGuard with configuration.
        
        Args:
            required_tokens: List of tokens that must be preserved,
                including braces (e.g., ["{user_id}", "{context}"]).
            repair_missing: If True, re-append missing required tokens.
            escape_unauthorized: If True, escape new unauthorized tokens.
        """
        ...
    
    def validate(self, original: str, mutated: str) -> str:
        """Validate and repair mutated instruction.
        
        Args:
            original: The instruction before mutation (reference for tokens).
            mutated: The instruction after mutation (to be validated).
        
        Returns:
            The mutated instruction with repairs and escapes applied.
        """
        ...
```

## Examples

### Example 1: ADK Agent Instructions

```python
guard = StateGuard(required_tokens=["{current_step}", "{user_query}"])

original = """
You are a helpful assistant.
Current step: {current_step}
User query: {user_query}
Respond helpfully.
"""

# LLM accidentally removed placeholders
mutated = """
You are a helpful and friendly assistant.
Respond with empathy and care.
"""

result = guard.validate(original, mutated)
# Result includes the missing tokens appended
```

### Example 2: Preventing Token Injection

```python
guard = StateGuard(required_tokens=["{approved_param}"])

original = "Process {approved_param}"
mutated = "Process {approved_param} and also {secret_key}"

result = guard.validate(original, mutated)
# {secret_key} is escaped to {{secret_key}}
```

### Example 3: ADK Prefixed State Tokens

ADK supports prefixed state variables (`app:`, `user:`, `temp:`). While the MVP pattern
doesn't auto-detect these, you can protect them by adding to `required_tokens`:

```python
# Protecting ADK prefixed tokens
guard = StateGuard(required_tokens=[
    "{user_id}",           # Simple token
    "{app:settings}",      # App-scoped state
    "{user:preferences}",  # User-scoped state
    "{temp:session_data}", # Temporary state
])

original = "Settings: {app:settings}, Prefs: {user:preferences}"
mutated = "Your settings are configured."

result = guard.validate(original, mutated)
# Appends missing prefixed tokens
```

## ADK Compatibility Notes

StateGuard is designed to work with Google ADK's state injection system
(`google.adk.utils.instructions_utils.inject_session_state`).

| ADK Feature | StateGuard Behavior |
|-------------|---------------------|
| Simple tokens `{name}` | ✅ Auto-detected and protected |
| Prefixed tokens `{app:x}` | ⚠️ Add to `required_tokens` explicitly |
| Optional tokens `{name?}` | ⚠️ Add to `required_tokens` explicitly |
| Artifact refs `{artifact.x}` | ❌ Not state variables, ignored |
| Escaped `{{literal}}` | ✅ Ignored (already escaped) |

## Troubleshooting

### Token Not Being Repaired

**Symptom**: Missing token is not re-appended.

**Cause**: Token is not in `required_tokens` list.

**Fix**: Add the token to `required_tokens`:
```python
guard = StateGuard(required_tokens=["{missing_token}"])
```

### Token Being Escaped Unexpectedly

**Symptom**: A valid new token is being escaped.

**Cause**: Token is new (not in original) and not in `required_tokens`.

**Fix**: Add it to `required_tokens` to authorize it:
```python
guard = StateGuard(required_tokens=["{new_valid_token}"])
```

### Malformed Tokens Ignored

**Symptom**: Tokens like `{invalid-name}` are not detected.

**Expected**: Only word-character tokens (`\w+`) are detected. Hyphens are not word characters.

**Solution**: Use underscores: `{invalid_name}` instead of `{invalid-name}`.

### Prefixed/Optional Tokens Not Detected

**Symptom**: Tokens like `{app:config}` or `{name?}` aren't auto-protected.

**Expected**: MVP pattern only matches simple `{identifier}` tokens.

**Solution**: Add them explicitly to `required_tokens`:
```python
guard = StateGuard(required_tokens=["{app:config}", "{name?}"])
```
