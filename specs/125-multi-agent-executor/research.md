# Research: Multi-Agent Unified Executor

**Feature**: 125-multi-agent-executor
**Date**: 2026-01-19
**Status**: Complete

## Research Questions

### RQ-1: What changes are needed to integrate executor into MultiAgentAdapter?

**Finding**: `MultiAgentAdapter` needs to accept an optional `executor: AgentExecutorProtocol | None` parameter and use it for all agent executions instead of direct `Runner` calls.

**Current State**:
- `MultiAgentAdapter.__init__()` does not have an `executor` parameter
- `_run_shared_session()` and `_run_isolated_sessions()` use direct `Runner` calls
- Session management is handled inline within each execution method

**Required Changes**:
1. Add `executor: AgentExecutorProtocol | None = None` parameter to `__init__`
2. Store executor as `self._executor`
3. Modify `_run_shared_session()` to use executor when available
4. Modify `_run_isolated_sessions()` to use executor when available
5. Log `uses_executor=True` in all execution logs

**Pattern Reference**: `CriticScorer` (already implements this pattern at lines 166-241 in `critic_scorer.py`)

---

### RQ-2: How should evolve_group() create and pass the executor?

**Finding**: `evolve_group()` should create an `AgentExecutor` instance at the start and pass it to all components.

**Current State** (`api.py` lines 504-538):
```python
# Build scorer
scorer = None
if critic:
    scorer = CriticScorer(critic_agent=critic)  # No executor

# Create adapter without proposer
adapter = MultiAgentAdapter(
    agents=agents,
    primary=primary,
    scorer=scorer,  # Scorer has no executor
    ...
)

# Create reflection proposer
if reflection_agent is not None:
    adk_reflection_fn = create_adk_reflection_fn(
        reflection_agent, session_service=session_service
    )  # No executor
```

**Required Changes**:
```python
# Create unified executor (FR-003)
executor = AgentExecutor(session_service=session_service)

# Build scorer with executor (FR-005)
scorer = None
if critic:
    scorer = CriticScorer(critic_agent=critic, executor=executor)

# Create adapter with executor (FR-004)
adapter = MultiAgentAdapter(
    agents=agents,
    primary=primary,
    scorer=scorer,
    executor=executor,  # NEW
    ...
)

# Create reflection proposer with executor (FR-006)
if reflection_agent is not None:
    adk_reflection_fn = create_adk_reflection_fn(
        reflection_agent,
        session_service=session_service,
        executor=executor,  # NEW
    )
```

---

### RQ-3: What existing patterns should be followed?

**Finding**: The codebase already has three implementations that use the executor pattern.

**1. CriticScorer** (`adapters/critic_scorer.py`):
```python
def __init__(
    self,
    critic_agent: BaseAgent,
    session_service: BaseSessionService | None = None,
    app_name: str = "critic_scorer",
    executor: AgentExecutorProtocol | None = None,  # Pattern to follow
) -> None:
    ...
    self._executor = executor  # T051: Store executor
    self._logger = logger.bind(
        ...
        uses_executor=executor is not None,  # Log executor usage
    )

async def async_score(self, ...):
    if self._executor is not None:
        result = await self._executor.execute_agent(...)  # Use executor
        ...
    # Legacy execution path as fallback
```

**2. ADKAdapter** (`adapters/adk_adapter.py`):
- Similar pattern in `_run_single_example()` method
- Checks `self._executor is not None` before execution
- Falls back to legacy execution path

**3. create_adk_reflection_fn** (`engine/adk_reflection.py`):
- Already has `executor` parameter
- Uses executor when provided, falls back to legacy path

---

### RQ-4: What about backward compatibility?

**Finding**: All changes can be backward compatible by using `None` defaults.

**Strategy**:
1. `MultiAgentAdapter(executor=None)` - works without executor (existing behavior)
2. `evolve_group()` - creates executor internally, callers don't need changes
3. All execution methods check `if self._executor is not None` before using

**Affected APIs**:
- `MultiAgentAdapter.__init__()` - new optional parameter
- `evolve_group()` - no signature change (creates executor internally)

---

### RQ-5: How does evolve_workflow() inherit support?

**Finding**: `evolve_workflow()` delegates to `evolve_group()`, so it inherits executor support automatically (FR-007).

**Code Reference** (`api.py`):
```python
async def evolve_workflow(...):
    ...
    # Delegates to evolve_group()
    return await evolve_group(
        agents=discovered_agents,
        primary=primary,
        trainset=trainset,
        critic=critic,
        ...
    )
```

No changes needed in `evolve_workflow()` - it will use the executor when `evolve_group()` creates one.

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Executor location | Create in `evolve_group()` | Central creation point, single shared instance |
| Parameter passing | Constructor injection | Follows existing CriticScorer pattern |
| Backward compatibility | Optional parameter with None | Existing callers continue working |
| Session service | Share between executor and adapter | Consistent session state |
| Logging | `uses_executor=True` in all logs | Matches FR-008 requirement |

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing callers | All new parameters are optional with None defaults |
| Session state conflicts | Use shared session service across all components |
| Performance regression | Executor adds minimal overhead (one wrapper layer) |

## References

- PR #138: Unified AgentExecutor implementation (merged)
- Issue #137: GitHub issue tracking this feature
- `adapters/critic_scorer.py`: Reference implementation
- `adapters/agent_executor.py`: AgentExecutor implementation
- `ports/agent_executor.py`: AgentExecutorProtocol definition
