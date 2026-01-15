# Research: Multi-Component Evolution with Component Selectors

**Feature**: 024-component-selector
**Date**: 2026-01-14

## Research Summary

This document captures research findings for implementing component selector strategies in gepa-adk, enabling multi-component evolution.

---

## 1. Upstream GEPA Reference Implementation

### Decision
Mirror upstream GEPA's `ReflectionComponentSelector` protocol and implementations (`RoundRobinReflectionComponentSelector`, `AllReflectionComponentSelector`).

### Rationale
- Upstream GEPA provides battle-tested implementations that align with the spec requirements
- Using similar patterns ensures behavioral parity and reduces conceptual overhead for users familiar with upstream GEPA
- The protocol-based approach aligns with gepa-adk's constitution (ADR-002: Protocol for Interfaces)

### Findings

**Upstream Protocol** (`.venv/lib/python3.12/site-packages/gepa/proposer/reflective_mutation/base.py:16-24`):
```python
class ReflectionComponentSelector(Protocol):
    def __call__(
        self,
        state: GEPAState,
        trajectories: list[Trajectory],
        subsample_scores: list[float],
        candidate_idx: int,
        candidate: dict[str, str],
    ) -> list[str]: ...
```

**RoundRobinReflectionComponentSelector** (`.venv/lib/python3.12/site-packages/gepa/strategies/component_selector.py:10-24`):
- Uses state to track `named_predictor_id_to_update_next_for_program_candidate[candidate_idx]`
- Cycles through `state.list_of_named_predictors` using modulo arithmetic
- Returns single component per iteration

**AllReflectionComponentSelector** (`.venv/lib/python3.12/site-packages/gepa/strategies/component_selector.py:27-36`):
- Returns `list(candidate.keys())` - all component keys from the candidate dict
- Stateless - no tracking needed

### Alternatives Considered
1. **Direct port of upstream classes**: Rejected because upstream uses `GEPAState` which is tightly coupled to sync GEPA internals
2. **Custom protocol with different signature**: Rejected to maintain conceptual alignment with upstream

---

## 2. gepa-adk Adapter Protocol Integration

### Decision
Extend the existing adapter flow to receive `components_to_update` from a component selector, rather than the current hardcoded `["instruction"]`.

### Rationale
- The `AsyncGEPAAdapter` protocol already supports `components_to_update` in `make_reflective_dataset` and `propose_new_texts` methods
- The hardcoded selection at `async_engine.py:313` is the only integration point that needs modification
- No adapter changes required - only engine orchestration changes

### Findings

**Current Hardcoded Selection** (`src/gepa_adk/engine/async_engine.py:313-324`):
```python
# Build reflective dataset
components_to_update = ["instruction"]  # v1: only instruction
reflective_dataset = await self.adapter.make_reflective_dataset(
    selected_candidate.components,
    eval_batch,
    components_to_update,
)

# Propose new texts
proposed_components = await self.adapter.propose_new_texts(
    selected_candidate.components,
    reflective_dataset,
    components_to_update,
)
```

**Adapter Protocol Already Supports Multi-Component** (`src/gepa_adk/ports/adapter.py:136-166`):
- `make_reflective_dataset` accepts `components_to_update: list[str]`
- `propose_new_texts` accepts `components_to_update: list[str]`
- Both return component-keyed mappings

### Alternatives Considered
1. **Modify adapter protocol**: Rejected - protocol already supports multi-component
2. **Create new adapter variant**: Rejected - unnecessary complexity

---

## 3. Component Selector Protocol Design

### Decision
Create `ComponentSelectorProtocol` in `ports/selector.py` with async `select_components` method that takes candidate components and iteration number.

### Rationale
- Follows async-first design principle (ADR-001)
- Mirrors existing `CandidateSelectorProtocol` pattern in the codebase
- Simplified signature vs upstream (no GEPAState dependency) for clean hexagonal architecture

### Findings

**Existing CandidateSelectorProtocol Pattern** (`src/gepa_adk/ports/selector.py:14-46`):
```python
@runtime_checkable
class CandidateSelectorProtocol(Protocol):
    async def select_candidate(self, state: ParetoState) -> int:
        ...
```

**Proposed ComponentSelectorProtocol**:
```python
@runtime_checkable
class ComponentSelectorProtocol(Protocol):
    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        ...
```

### Alternatives Considered
1. **Sync protocol**: Rejected per ADR-001 (Async-First Design)
2. **Include full candidate dict**: Rejected - only component names needed for selection

---

## 4. State Management for Round-Robin

### Decision
Track round-robin iteration state within the selector instance, keyed by candidate index for Pareto-aware scenarios.

### Rationale
- Upstream tracks state in `GEPAState.named_predictor_id_to_update_next_for_program_candidate`
- For gepa-adk, selector instance state is cleaner than polluting engine state
- Per-candidate tracking enables independent round-robin cycles for Pareto evolution

### Findings

**Upstream State Tracking**:
```python
pid = state.named_predictor_id_to_update_next_for_program_candidate[candidate_idx]
state.named_predictor_id_to_update_next_for_program_candidate[candidate_idx] = (pid + 1) % len(
    state.list_of_named_predictors
)
```

**Proposed gepa-adk Implementation**:
```python
class RoundRobinComponentSelector:
    def __init__(self) -> None:
        self._next_index: dict[int, int] = {}  # candidate_idx -> component index

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        idx = self._next_index.get(candidate_idx, 0)
        self._next_index[candidate_idx] = (idx + 1) % len(components)
        return [components[idx]]
```

### Alternatives Considered
1. **Global iteration-based cycling**: Rejected - doesn't work well with Pareto multi-candidate scenarios
2. **Store state in engine**: Rejected - violates separation of concerns

---

## 5. Multi-Agent Component Discovery

### Decision
Build component list from candidate keys, filtering by `_instruction` suffix for per-agent instructions, with special handling to exclude generic `instruction` alias when specific per-agent keys exist.

### Rationale
- Multi-agent candidates use naming convention `{agent_name}_instruction` (see `api.py:503-507`)
- The generic `instruction` key is added for engine compatibility but points to primary agent
- Excluding the alias prevents double-mutation of the same underlying instruction

### Findings

**Current Multi-Agent Candidate Structure** (`src/gepa_adk/api.py:503-508`):
```python
seed_candidate_components: dict[str, str] = {
    f"{agent.name}_instruction": str(agent.instruction) for agent in agents
}
# Add required "instruction" key for engine compatibility
seed_candidate_components["instruction"] = str(primary_agent.instruction)
```

**Proposed Component List Building**:
```python
def _build_component_list(candidate: Candidate) -> list[str]:
    components = list(candidate.components.keys())
    instruction_keys = [k for k in components if k.endswith("_instruction")]

    # If per-agent instructions exist, exclude the generic "instruction" alias
    if instruction_keys and "instruction" in components:
        components.remove("instruction")

    return sorted(components)  # Sorted for deterministic ordering
```

### Alternatives Considered
1. **Explicit component list in Candidate**: Rejected - adds state that duplicates keys()
2. **No filtering of instruction alias**: Rejected - would cause double-mutation of primary agent

---

## 6. API Integration Points

### Decision
Add `component_selector` parameter to `evolve()`, `evolve_group()`, and `evolve_workflow()` functions, accepting either a protocol instance or string identifier.

### Rationale
- Follows existing pattern for `candidate_selector` parameter
- String identifiers provide convenient defaults ("round_robin", "all")
- Protocol instances allow custom selector implementations

### Findings

**Existing Candidate Selector Pattern** (`src/gepa_adk/api.py:934-939`):
```python
resolved_selector: CandidateSelectorProtocol | None = None
if candidate_selector is not None:
    if isinstance(candidate_selector, str):
        resolved_selector = create_candidate_selector(candidate_selector)
    else:
        resolved_selector = candidate_selector
```

**Proposed Component Selector Pattern**:
```python
resolved_component_selector: ComponentSelectorProtocol | None = None
if component_selector is not None:
    if isinstance(component_selector, str):
        resolved_component_selector = create_component_selector(component_selector)
    else:
        resolved_component_selector = component_selector
else:
    # Default to round-robin
    resolved_component_selector = RoundRobinComponentSelector()
```

### Alternatives Considered
1. **Config-based selection**: Rejected - less flexible than parameter-based
2. **No default selector**: Rejected - spec requires default to round-robin (FR-003)

---

## 7. Testing Strategy

### Decision
Follow three-layer testing strategy per ADR-005: contract tests for protocol compliance, unit tests for selector logic, integration tests for end-to-end multi-component evolution.

### Rationale
- Contract tests ensure adapters implement ComponentSelectorProtocol correctly
- Unit tests verify round-robin cycling and all-components selection logic
- Integration tests validate the full flow with real ADK agents

### Findings

**Existing Test Structure**:
- `tests/contracts/` - Protocol compliance tests
- `tests/unit/` - Business logic with mocks
- `tests/integration/` - Real ADK/LLM calls (marked `@pytest.mark.slow`)

**Proposed Test Files**:
- `tests/contracts/test_component_selector_protocol.py` - Protocol compliance
- `tests/unit/adapters/test_component_selector.py` - Selector logic
- `tests/unit/engine/test_engine_component_selection.py` - Engine integration
- `tests/integration/test_multi_component_evolution.py` - End-to-end

---

## 8. Constitution Compliance Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | COMPLIANT | Protocol in ports/, implementations in adapters/ |
| II. Async-First Design | COMPLIANT | Protocol uses async method |
| III. Protocol-Based Interfaces | COMPLIANT | Uses `typing.Protocol` with `@runtime_checkable` |
| IV. Three-Layer Testing | COMPLIANT | Contract, unit, and integration tests planned |
| V. Observability & Documentation | COMPLIANT | Google-style docstrings, structlog events |

---

## Summary of Key Decisions

| Decision | Choice | Key Rationale |
|----------|--------|---------------|
| Protocol design | Simplified async protocol | Clean hexagonal architecture |
| State management | Per-selector instance state | Separation of concerns |
| Round-robin tracking | Per-candidate-idx dict | Pareto-aware multi-candidate support |
| Component discovery | Keys filtering with alias exclusion | Prevents double-mutation |
| API pattern | String or instance parameter | Follows existing candidate_selector pattern |
| Default selector | Round-robin | Per FR-003 specification |
