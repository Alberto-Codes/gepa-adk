# Research: API StateGuard Validation

**Feature**: 020-api-stateguard-validation  
**Date**: January 13, 2026  
**Status**: Complete

## Overview

This research documents the existing StateGuard implementation and how it should be wired into the public API. No external research was required as this is internal code integration.

## Existing Implementation Analysis

### StateGuard Class (`src/gepa_adk/utils/state_guard.py`)

The StateGuard class is fully implemented and tested (specs 013 and 015):

```python
class StateGuard:
    def __init__(
        self,
        required_tokens: list[str] | None = None,
        repair_missing: bool = True,
        escape_unauthorized: bool = True,
    ) -> None: ...

    def validate(self, original: str, mutated: str) -> str:
        """Validate and repair mutated instruction."""
        ...
```

**Key behaviors**:
1. **Token extraction**: Uses regex `(?<!\{)\{(\w+(?::\w+)?(?:\?)?)\}(?!\})` to find tokens
2. **Missing token repair**: Appends tokens from original instruction that are missing in mutated
3. **Unauthorized token escape**: Double-braces new tokens not in original: `{x}` → `{{x}}`
4. **Configurable**: Both behaviors can be disabled via constructor parameters

### Current API State

The `evolve()` function already accepts `state_guard` parameter but has a TODO:

```python
# Line 837-843 in api.py
if state_guard is not None:
    # TODO: Implement state guard validation when StateGuard is available
    logger.debug(
        "evolve.state_guard.provided",
        agent_name=agent.name,
        message="state_guard parameter provided but validation not yet implemented",
    )
```

### Functions Requiring StateGuard Integration

| Function | File Location | Has `state_guard` param? | Needs Integration |
|----------|---------------|--------------------------|-------------------|
| `evolve()` | api.py:667 | ✅ Yes | ✅ Yes |
| `evolve_sync()` | api.py:867 | ✅ Yes (passes to evolve) | ❌ No (automatic) |
| `evolve_group()` | api.py:306 | ❌ No | ✅ Yes (add param) |
| `evolve_workflow()` | api.py:510 | ❌ No | ✅ Yes (add param) |

## Design Decisions

### Decision 1: Where to Apply StateGuard Validation

**Decision**: Apply StateGuard validation **after** evolution completes, **before** returning the result.

**Rationale**:
- StateGuard operates on final instruction strings (no I/O)
- Validating only the final result is sufficient (intermediate candidates don't matter)
- Keeps validation logic simple and isolated

**Alternatives considered**:
- Per-iteration validation: Rejected - unnecessary overhead, intermediate results discarded
- Pre-evolution validation: Rejected - nothing to validate before evolution

### Decision 2: Original Instruction Reference

**Decision**: Use `agent.instruction` captured at the start of evolution as the "original" reference for StateGuard.

**Rationale**:
- The original instruction is the baseline for token detection
- Capturing at start ensures we compare against the pre-evolution state
- Already available via `agent.instruction` attribute

### Decision 3: Multi-Agent StateGuard Handling

**Decision**: Apply StateGuard validation to **each agent's evolved instruction** using that agent's **original instruction** as reference.

**Rationale**:
- Each agent has different tokens in its original instruction
- A single StateGuard config applies to all agents (shared required_tokens)
- Per-agent original instruction ensures correct token detection

### Decision 4: Logging Strategy

**Decision**: Log at `info` level when StateGuard modifies the instruction, `debug` level when no changes needed.

**Rationale**:
- Token repair/escape is significant and should be visible in normal logs
- No-op validation is noise and belongs in debug

**Log format**:
```python
logger.info(
    "evolve.state_guard.applied",
    agent_name=agent.name,
    tokens_repaired=["user_id"],
    tokens_escaped=["malicious"],
    original_length=len(original),
    final_length=len(validated),
)
```

## Implementation Approach

### Step 1: Modify `evolve()` Function

Replace the TODO block with actual StateGuard validation:

```python
# Apply state guard if provided (for token preservation)
if state_guard is not None:
    original_instruction = str(agent.instruction)
    validated_instruction = state_guard.validate(
        original_instruction,
        result.evolved_instruction
    )
    
    if validated_instruction != result.evolved_instruction:
        logger.info(
            "evolve.state_guard.applied",
            agent_name=agent.name,
            instruction_modified=True,
        )
        # Create new result with validated instruction
        result = EvolutionResult(
            original_score=result.original_score,
            final_score=result.final_score,
            evolved_instruction=validated_instruction,
            iteration_history=result.iteration_history,
            total_iterations=result.total_iterations,
        )
```

### Step 2: Add `state_guard` to `evolve_group()` and `evolve_workflow()`

Add parameter and apply validation to each agent's instruction in the result dict.

### Step 3: Add Tests

- Unit tests with fake evolution results
- Test token repair behavior
- Test token escape behavior
- Test no-op when state_guard=None

## Dependencies

No new dependencies required. Uses existing:
- `gepa_adk.utils.StateGuard` (already implemented)
- `structlog` (already used throughout)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Low | Medium | Run full test suite before/after |
| Performance regression | Very Low | Low | StateGuard is O(n) string operations |
| Incorrect original instruction | Low | High | Capture `agent.instruction` at function entry |

## Conclusion

This is a straightforward wiring task. The StateGuard class is fully implemented and tested. The implementation requires:

1. ~20 lines of code in `evolve()` to replace the TODO
2. ~10 lines each in `evolve_group()` and `evolve_workflow()` to add parameter and apply validation
3. ~50 lines of unit tests

No external research or dependencies needed.
