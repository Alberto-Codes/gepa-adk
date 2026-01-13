# Research: Public API (evolve, evolve_sync)

**Feature**: 018-public-api  
**Date**: 2026-01-12  
**Phase**: 0 - Research

## Research Questions

### RQ-1: How to handle sync wrapper with nested event loops?

**Context**: The `evolve_sync()` function must work in Jupyter notebooks and scripts that may already have a running event loop.

**Research**:
- Standard `asyncio.run()` raises `RuntimeError` if called from within a running event loop
- Jupyter notebooks run their own event loop
- Options:
  1. Use `asyncio.run()` with try/except and fallback to `loop.run_until_complete()`
  2. Use `nest_asyncio` library to patch asyncio for nested loops
  3. Detect existing loop and use appropriate strategy

**Decision**: Use a try/except pattern that detects running event loops and uses `nest_asyncio` as a fallback. This is the standard pattern used by many libraries (e.g., `httpx`, `requests-async`).

**Rationale**: 
- Keeps the API simple for users
- Works in all contexts (scripts, notebooks, existing async code)
- `nest_asyncio` is a lightweight, well-maintained dependency

**Alternatives Considered**:
- Requiring users to manage async context themselves (rejected: poor UX)
- Only supporting `asyncio.run()` (rejected: breaks notebook use case)

---

### RQ-2: What is the minimal adapter setup for single-agent evolution?

**Context**: Need to understand how to wire up a single LlmAgent with the engine.

**Research**:
- Existing `ADKAdapter` in `adapters/adk_adapter.py` handles single-agent evaluation
- Requires: agent, scorer, optional trajectory_config
- Default scorer: Schema-based scorer (uses agent.output_schema) or `CriticScorer` (LLM-based)
- Engine expects: adapter, config, initial_candidate, batch

**Decision**: 
```python
# Build chain for single agent evolution:
1. Create scorer (CriticScorer if critic provided, else infer from agent.output_schema)
2. Create ADKAdapter(agent, scorer, trajectory_config)
3. Create initial Candidate with agent.instruction
4. Create AsyncGEPAEngine(adapter, config, initial_candidate, batch)
5. Run engine and extract result
```

**Rationale**: Follows existing patterns from `evolve_group()` but simplified for single agent.

---

### RQ-3: What parameters should have defaults vs be required?

**Context**: API should be simple for basic use but allow progressive disclosure.

**Research from spec**:
- **Required**: agent, trainset (minimum viable call)
- **Optional with defaults**:
  - `valset`: None (no validation set)
  - `critic`: None (use schema-based scorer via agent's output_schema)
  - `reflection_agent`: None (use LiteLLM-based proposer from config)
  - `config`: None → EvolutionConfig() defaults
  - `trajectory_config`: None → TrajectoryConfig() defaults
  - `state_guard`: None (no state preservation)

**Decision**: Match the signature from GitHub Issue #16:
```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict],
    valset: list[dict] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
) -> EvolutionResult:
```

**Rationale**: 
- 2 required params = minimal cognitive load
- All optional params have sensible defaults
- Matches user expectations from the issue spec

---

### RQ-4: Does StateGuard exist? What is it?

**Context**: Spec mentions `state_guard` parameter for preserving tokens.

**Research**:
- Checked `src/gepa_adk/utils/` - no `state_guard.py` found
- Checked specs/ - `015-state-guard-tokens` exists but implementation status unknown
- StateGuard would validate evolved instructions to preserve certain tokens/patterns

**Decision**: Mark as optional dependency. If StateGuard doesn't exist:
1. Accept the parameter but make it truly optional
2. Skip state guard validation if None
3. If provided, validate evolved instruction before returning

**Rationale**: API should be forward-compatible with StateGuard when it's implemented.

---

### RQ-5: What about the `reflection_agent` parameter?

**Context**: Spec mentions using a custom ADK agent for generating proposals.

**Research**:
- Checked `engine/proposer.py` - AsyncReflectiveMutationProposer exists
- Uses LiteLLM for proposals by default
- Would need `create_adk_reflection_fn()` adapter to use ADK agent

**Decision**: For MVP, don't support custom reflection_agent:
1. Accept the parameter for API compatibility
2. Log warning if provided (not yet implemented)
3. Use default LiteLLM proposer from config.reflection_model

**Rationale**: Keeps initial implementation simpler while maintaining API surface for future enhancement.

---

## Dependencies Identified

| Dependency | Purpose | Status |
|------------|---------|--------|
| `nest_asyncio` | Handle nested event loops in Jupyter | NEW - needs uv add |
| `ADKAdapter` | Single-agent evaluation | EXISTING |
| `CriticScorer` | LLM-based scoring | EXISTING |
| `AsyncGEPAEngine` | Core evolution loop | EXISTING |
| `EvolutionConfig` | Config defaults | EXISTING |
| `TrajectoryConfig` | Trace settings | EXISTING |
| `StateGuard` | Token preservation | NOT IMPLEMENTED (optional) |

## Implementation Notes

1. **File changes**:
   - `api.py`: Add `evolve()` and `evolve_sync()` functions
   - `__init__.py`: Export new functions

2. **Test strategy**:
   - Contract: Verify function signatures and return types
   - Unit: Mock adapter/engine, test parameter handling
   - Integration: Real ADK calls (marked slow)

3. **Error handling**:
   - Empty trainset → raise appropriate error
   - Invalid agent → raise validation error
   - Network failures → let underlying exceptions propagate with context
