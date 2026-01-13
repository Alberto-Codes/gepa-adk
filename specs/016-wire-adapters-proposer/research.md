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

---

## Reference Analysis: Original GEPA Library (gepa>=0.0.24)

### Key Architectural Insight

Examined the original GEPA library installed as a dev dependency to understand the canonical pattern for proposer integration.

**Source**: `.venv/lib/python3.12/site-packages/gepa/`

### GEPA's Adapter Pattern

In the original GEPA, `propose_new_texts` is an **optional attribute** on the adapter, not a required method:

```python
# From gepa/core/adapter.py
class GEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    # ... evaluate() and make_reflective_dataset() are required methods ...
    
    propose_new_texts: ProposalFn | None = None  # Optional attribute!
```

Where `ProposalFn` is:
```python
class ProposalFn(Protocol):
    def __call__(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]: ...
```

### GEPA's ReflectiveMutationProposer Flow

The `ReflectiveMutationProposer` in GEPA (sync, not async) delegates to the adapter's `propose_new_texts` if provided:

```python
# From gepa/proposer/reflective_mutation/reflective_mutation.py
def propose_new_texts(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str]:
    # Check adapter first!
    if self.adapter.propose_new_texts is not None:
        return self.adapter.propose_new_texts(candidate, reflective_dataset, components_to_update)
    
    # Otherwise use reflection_lm
    if self.reflection_lm is None:
        raise ValueError("reflection_lm must be provided when adapter.propose_new_texts is None.")
    
    new_texts: dict[str, str] = {}
    for name in components_to_update:
        if name not in reflective_dataset or not reflective_dataset.get(name):
            self.logger.log(f"Component '{name}' is not in reflective dataset. Skipping.")
            continue
        # ... LLM-based proposal logic ...
    return new_texts
```

### Architectural Comparison

| Aspect | Original GEPA | gepa-adk |
|--------|---------------|----------|
| `propose_new_texts` | Optional attribute on adapter | Required async method on adapter |
| Proposer location | Engine owns proposal logic | Engine owns proposal logic |
| Delegation direction | Proposer → Adapter (if adapter has it) | Adapter → Proposer |
| Async support | Sync only | Async-first |

### Design Decision: gepa-adk Approach

Our gepa-adk approach **inverts** the delegation direction:
- **GEPA**: Proposer checks if adapter has `propose_new_texts`, delegates to it
- **gepa-adk**: Adapter always has `propose_new_texts()` method, delegates to proposer

**Why this difference makes sense for gepa-adk**:

1. **Async-first**: ADK is async-native. Having async methods as the primary interface (not optional attributes) is cleaner.

2. **Protocol compliance**: Our `AsyncGEPAAdapter` protocol requires `propose_new_texts()` as a method. This ensures type safety and consistent interface.

3. **Dependency injection**: Injecting proposer into adapter is cleaner than adapter checking if proposer exists.

4. **Testability**: Easier to mock the proposer in adapter tests than to mock an optional attribute.

### Key Patterns to Adopt from GEPA

1. **Graceful handling of missing components**:
   ```python
   if name not in reflective_dataset or not reflective_dataset.get(name):
       self.logger.log(f"Component '{name}' is not in reflective dataset. Skipping.")
       continue
   ```
   Our adapters should log and skip missing components similarly.

2. **Return type consistency**: GEPA's `propose_new_texts` returns `dict[str, str]` (never None). Our proposer can return `None`, but adapters should convert to dict with fallback values.

3. **Reflective dataset format**: GEPA uses `{"Inputs": ..., "Generated Outputs": ..., "Feedback": ...}` format. Our adapters already follow this convention in `build_reflection_example()`.

### Impact on Implementation

No changes needed to our planned approach. The research confirms:
- ✅ Our signature is compatible with GEPA's `ProposalFn` protocol
- ✅ Delegating adapter → proposer is valid (inverse of GEPA's pattern but architecturally sound)
- ✅ Eager instantiation aligns with GEPA's "fail if reflection_lm is None" pattern
- ✅ Graceful component skipping should be adopted from GEPA

---

## Unresolved Items

None. All clarifications resolved.
