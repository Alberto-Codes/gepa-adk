# API Contract: Adapter Proposer Integration

**Feature**: 016-wire-adapters-proposer  
**Phase**: 1 - Design  
**Date**: 2026-01-12

## ADKAdapter Constructor Contract

### Signature

```python
def __init__(
    self,
    agent: LlmAgent,
    scorer: Scorer,
    max_concurrent_evals: int = 5,
    session_service: BaseSessionService | None = None,
    app_name: str = "gepa_adk_eval",
    trajectory_config: TrajectoryConfig | None = None,
    proposer: AsyncReflectiveMutationProposer | None = None,  # NEW
) -> None
```

### Parameter: proposer

| Property | Value |
|----------|-------|
| Type | `AsyncReflectiveMutationProposer \| None` |
| Default | `None` |
| Required | No |
| Position | Last keyword argument |

### Behavior

| Condition | Behavior |
|-----------|----------|
| `proposer=None` | Instantiate `AsyncReflectiveMutationProposer()` with defaults |
| `proposer=<instance>` | Use provided instance |

### Validation

- No explicit type checking (duck typing)
- Proposer stored in `self._proposer`

---

## MultiAgentAdapter Constructor Contract

### Signature

```python
def __init__(
    self,
    agents: list[LlmAgent],
    primary: str,
    scorer: Scorer | None = None,
    share_session: bool = True,
    session_service: BaseSessionService | None = None,
    app_name: str = "multi_agent_eval",
    trajectory_config: TrajectoryConfig | None = None,
    proposer: AsyncReflectiveMutationProposer | None = None,  # NEW
) -> None
```

### Parameter: proposer

| Property | Value |
|----------|-------|
| Type | `AsyncReflectiveMutationProposer \| None` |
| Default | `None` |
| Required | No |
| Position | Last keyword argument |

### Behavior

Same as ADKAdapter.

---

## ADKAdapter.propose_new_texts Contract

### Signature (unchanged)

```python
async def propose_new_texts(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str]
```

### Behavior (updated)

| Step | Action |
|------|--------|
| 1 | Call `await self._proposer.propose(candidate, reflective_dataset, components_to_update)` |
| 2a | If result is `None`: log fallback, return `{c: candidate.get(c, "") for c in components_to_update}` |
| 2b | If result is `dict`: merge with candidate for missing keys, return complete dict |

### Return Value

Always returns `dict[str, str]` mapping each component in `components_to_update` to:
- Proposed text (from proposer), OR
- Original candidate value (fallback)

### Logging

| Event | Level | When |
|-------|-------|------|
| `propose_new_texts.delegating` | DEBUG | Before calling proposer |
| `propose_new_texts.fallback` | INFO | When proposer returns None |
| `propose_new_texts.complete` | INFO | After successful proposal |

### Error Handling

| Error Source | Behavior |
|--------------|----------|
| Proposer raises exception | Propagate unchanged |
| Invalid candidate | Proposer handles (returns None) |
| Empty components_to_update | Return empty dict `{}` |

---

## MultiAgentAdapter.propose_new_texts Contract

### Signature (unchanged)

```python
async def propose_new_texts(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str]
```

### Behavior (updated)

Same delegation pattern as ADKAdapter.

**Replaces**: Current heuristic-based implementation that selects highest-scoring outputs.

---

## Test Contract Verification

### Unit Test Requirements

| Test Case | Verifies |
|-----------|----------|
| `test_propose_new_texts_delegates_to_proposer` | US1/US2: Delegation occurs |
| `test_propose_new_texts_uses_custom_proposer` | US3: Injected proposer used |
| `test_propose_new_texts_fallback_on_none` | US4: Graceful fallback |
| `test_propose_new_texts_merges_partial_result` | FR-007: Partial result handling |
| `test_constructor_creates_default_proposer` | FR-003: Default instantiation |

### Mock Strategy

Use `AsyncMock` for proposer in unit tests:

```python
@pytest.fixture
def mock_proposer():
    proposer = AsyncMock(spec=AsyncReflectiveMutationProposer)
    proposer.propose = AsyncMock(return_value={"instruction": "improved text"})
    return proposer
```

---

## Backward Compatibility

| Aspect | Status | Notes |
|--------|--------|-------|
| Constructor signature | ✅ Compatible | New optional param at end |
| Method signatures | ✅ Unchanged | Same async signature |
| Return types | ✅ Unchanged | Still `dict[str, str]` |
| Existing tests | ✅ Pass | No breaking changes |
| Import paths | ✅ Unchanged | Same public API |

---

## Reference: GEPA Library Alignment

This contract aligns with patterns from the original GEPA library (`gepa>=0.0.24`):

### Signature Compatibility

Our `propose_new_texts()` signature matches GEPA's `ProposalFn` protocol:
```python
# GEPA's ProposalFn (from gepa/core/adapter.py)
class ProposalFn(Protocol):
    def __call__(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]: ...
```

### Component Skipping Pattern

Adopted from GEPA's `ReflectiveMutationProposer`:
```python
# When component not in reflective_dataset, log and skip (don't error)
if name not in reflective_dataset or not reflective_dataset.get(name):
    self._logger.debug("propose_new_texts.component_skipped", component=name)
    # Use original candidate value for this component
```

### Architectural Difference

| GEPA Pattern | gepa-adk Pattern |
|--------------|------------------|
| `propose_new_texts` is optional attribute on adapter | `propose_new_texts()` is required async method |
| Proposer delegates TO adapter if adapter has it | Adapter delegates TO proposer |
| Sync-first | Async-first |

Both patterns are valid; gepa-adk inverts delegation for better async support and testability.