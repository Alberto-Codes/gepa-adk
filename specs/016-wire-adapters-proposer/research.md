# Research: Wire Adapters to AsyncReflectiveMutationProposer

**Feature**: 016-wire-adapters-proposer  
**Phase**: 0 - Research  
**Date**: 2026-01-12

## Research Tasks

Based on the Technical Context section in plan.md, the following items needed clarification:

### 1. Proposer Interface Compatibility

**Question**: Does `AsyncReflectiveMutationProposer.propose()` have the exact signature that adapters need?

**Research**: Examined `src/gepa_adk/engine/proposer.py` lines 352-406.

**Finding**: The proposer's `propose()` method signature:
```python
async def propose(
    self,
    candidate: dict[str, str],
    reflective_dataset: ReflectiveDataset,  # Mapping[str, Sequence[Mapping[str, Any]]]
    components_to_update: list[str],
) -> ProposalResult:  # dict[str, str] | None
```

**Decision**: ✅ Compatible. Both adapters already have `propose_new_texts()` with matching parameter types:
- `candidate: dict[str, str]`
- `reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]]`
- `components_to_update: list[str]`

The return type `dict[str, str] | None` is also compatible with the expected adapter behavior.

---

### 2. Default Proposer Instantiation

**Question**: What default parameters should be used when instantiating `AsyncReflectiveMutationProposer()`?

**Research**: Examined proposer constructor defaults in `src/gepa_adk/engine/proposer.py` lines 295-345.

**Finding**: Default constructor values:
- `model="ollama/gpt-oss:20b"` (local development model)
- `prompt_template=DEFAULT_PROMPT_TEMPLATE` (built-in template)
- `temperature=0.7` (balanced creativity/consistency)
- `max_tokens=2048` (sufficient for instruction text)
- `adk_reflection_fn=None` (uses LiteLLM fallback)

**Decision**: Use `AsyncReflectiveMutationProposer()` with no arguments for default. Users can inject custom proposers with different configurations. This keeps the adapter API simple while allowing full customization.

---

### 3. Import Strategy

**Question**: How should adapters import the proposer class without violating hexagonal architecture?

**Research**: Constitution Principle I states adapters CAN import from engine layer.

**Finding**: Current import rules allow:
- adapters/ → can import from ports/, domain/, external libs
- engine/ → depends on ports/, domain/ only

**Decision**: ✅ Safe to import. Adapters can import `AsyncReflectiveMutationProposer` from `gepa_adk.engine.proposer`. However, this creates a dependency from adapters → engine. 

**Alternative Considered**: Define a `MutationProposer` protocol in `ports/`. 
- **Rejected**: Over-engineering for a single concrete implementation. The proposer is internal to gepa-adk, not an external boundary. If multiple proposer implementations emerge, we can extract a protocol later (YAGNI).

**Final Decision**: Direct import `from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer` in adapter modules.

---

### 4. Null Handling Pattern

**Question**: How should adapters handle `None` return from proposer?

**Research**: Examined proposer behavior in `src/gepa_adk/engine/proposer.py` lines 398-410.

**Finding**: Proposer returns `None` when:
1. `reflective_dataset` is empty (`{}`)
2. No components in `components_to_update` have entries in dataset
3. No valid proposals were generated

**Decision**: Adapters should:
1. Call `await self._proposer.propose(...)`
2. If result is `None`, construct fallback dict: `{c: candidate.get(c, "") for c in components_to_update}`
3. If result is partial (some components missing), merge with candidate values
4. Log when falling back (FR-008)

Pattern:
```python
result = await self._proposer.propose(candidate, reflective_dataset, components_to_update)
if result is None:
    self._logger.info("propose_new_texts.fallback", reason="proposer_returned_none")
    return {c: candidate.get(c, "") for c in components_to_update}
# Merge with candidate for any missing components
return {c: result.get(c, candidate.get(c, "")) for c in components_to_update}
```

---

### 5. Backward Compatibility

**Question**: Will adding `proposer` parameter break existing code?

**Research**: Examined adapter constructors.

**Finding**: Both adapters use keyword-only parameters after `agent`/`agents`. Adding `proposer: AsyncReflectiveMutationProposer | None = None` as optional won't break existing callers.

**Decision**: ✅ Safe. Add as last optional parameter with `None` default. Existing code continues to work; new code can inject custom proposers.

---

### 6. Lazy vs Eager Default Instantiation

**Question**: Should the default proposer be instantiated at adapter init time or lazily on first use?

**Research**: Considered tradeoffs.

**Options**:
1. **Eager (at init)**: Simpler, fails fast if proposer has config issues
2. **Lazy (on first propose_new_texts call)**: Avoids instantiation if propose_new_texts never called

**Decision**: **Eager instantiation** at `__init__`. Reasons:
- Fail-fast on configuration issues
- Consistent behavior (proposer always exists)
- Simpler implementation
- Minor performance impact (proposer is lightweight to construct)

Pattern:
```python
def __init__(self, ..., proposer: AsyncReflectiveMutationProposer | None = None):
    ...
    self._proposer = proposer or AsyncReflectiveMutationProposer()
```

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Proposer interface | Compatible as-is | Signatures match exactly |
| Default instantiation | `AsyncReflectiveMutationProposer()` | Use library defaults |
| Import strategy | Direct import from engine | Within hexagonal rules, YAGNI for protocol |
| Null handling | Fallback to candidate values | Graceful degradation |
| Parameter position | Last optional kwarg | Backward compatible |
| Instantiation timing | Eager at init | Fail-fast, simpler |

## Unresolved Items

None. All clarifications resolved.
