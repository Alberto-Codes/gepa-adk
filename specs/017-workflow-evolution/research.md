# Research: Workflow Agent Evolution

**Feature**: 017-workflow-evolution  
**Date**: 2026-01-12  
**Status**: Complete

## Package Versions (from .venv)

- **google-adk**: 1.22.0 (installed in src dependencies)
- **gepa**: 0.0.24 (installed as dev dependency for inspiration)

## Research Tasks

### 1. ADK Workflow Agent Types and `sub_agents` Attribute

**Decision**: Use isinstance() checks against SequentialAgent, LoopAgent, ParallelAgent from `google.adk.agents`.

**Rationale**: Verified from installed google-adk 1.22.0:
- All agents inherit from `BaseAgent` which defines `sub_agents: list[BaseAgent] = Field(default_factory=list)` (base_agent.py:133)
- `SequentialAgent`: Runs sub-agents in sequence via `_run_async_impl` loop
- `LoopAgent`: Runs sub-agents iteratively with `max_iterations` parameter  
- `ParallelAgent`: Runs sub-agents concurrently

**Key Code Reference** (base_agent.py:133):
```python
sub_agents: list[BaseAgent] = Field(default_factory=list)
"""The sub-agents of this agent."""
```

**Alternatives Considered**:
- Duck typing (check for `sub_agents` attribute): Rejected because ALL agents have `sub_agents` (it's on BaseAgent)
- Check `sub_agents` is non-empty: Not sufficient—need to identify workflow agent *types*

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/`

### 2. LlmAgent Detection Strategy

**Decision**: Use `isinstance(agent, LlmAgent)` to identify agents that can be evolved.

**Rationale**: Verified from installed google-adk 1.22.0 (llm_agent.py:203):
```python
instruction: Union[str, InstructionProvider] = ''
"""Dynamic instructions for the LLM model, guiding the agent's behavior."""
```

Key attributes unique to LlmAgent:
- `instruction`: str or InstructionProvider (the target of evolution)
- `model`: str (LLM model identifier)
- `output_key`: Optional[str] (state key for storing output)
- `static_instruction`: Optional content for caching optimization

**Important**: `instruction` can be a string OR an `InstructionProvider` callable. For evolution, we only support string instructions (documented limitation matches existing codebase pattern).

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/llm_agent.py`

### 3. Recursive Traversal with Depth Limiting

**Decision**: Implement recursive `find_llm_agents()` with `max_depth` parameter (default: 5) and `current_depth` counter.

**Rationale**: 
- Prevents infinite recursion in deeply nested or malformed workflows
- Default depth of 5 matches typical workflow complexity (most workflows are 2-3 levels)
- Depth limiting is a common pattern for tree traversal safety

**Implementation Pattern**:
```python
def find_llm_agents(agent: Any, max_depth: int = 5, current_depth: int = 0) -> list[LlmAgent]:
    if current_depth >= max_depth:
        return []
    if isinstance(agent, LlmAgent):
        return [agent]
    if is_workflow_agent(agent):
        agents = []
        for sub_agent in agent.sub_agents:
            agents.extend(find_llm_agents(sub_agent, max_depth, current_depth + 1))
        return agents
    return []
```

**Alternatives Considered**:
- Visited set to prevent cycles: Rejected because ADK enforces unique sub-agent assignment (base_agent.py validator)
- Iterative with explicit stack: More complex, recursive is clearer

### 4. GEPA Package Patterns (Dev Dependency Reference)

**Reference**: gepa 0.0.24 provides patterns we follow:
- `gepa.api.optimize()` is the main entry point (like our `evolve_workflow()`)
- `GEPAAdapter` protocol for adapter abstraction (we have `AsyncGEPAAdapter`)
- `ReflectiveMutationProposer` for LLM-based mutation (we have `AsyncReflectiveMutationProposer`)
- `GEPAResult` for evolution results (we have `MultiAgentEvolutionResult`)

**Key Pattern from gepa**: The adapter handles evaluation, the engine handles evolution loop, the proposer handles mutation. Our architecture mirrors this separation.

**Source**: `.venv/lib/python3.12/site-packages/gepa/`

### 5. Integration with `evolve_group()`

**Decision**: `evolve_workflow()` finds all LlmAgents, then delegates to `evolve_group()` with `share_session=True`.

**Rationale**:
- `evolve_group()` already handles multi-agent evolution with session state sharing
- The last agent in a sequential workflow typically produces the final output, making it the natural `primary` agent
- Session sharing preserves workflow context during evaluation (agents can access earlier outputs via `output_key`)

**Key Integration Points**:
- `agents`: All discovered LlmAgents from the workflow
- `primary`: Last LlmAgent in discovered list (for sequential workflows) or configurable
- `share_session=True`: Maintains workflow execution context

**Alternatives Considered**:
- Custom evaluation loop: Rejected because `evolve_group()` already provides all needed functionality
- Evolve agents individually: Rejected because it loses workflow context and agent coordination

### 6. Error Handling for Empty Workflows

**Decision**: Raise `WorkflowEvolutionError` (new exception class) when no LlmAgents are found.

**Rationale**:
- Follows ADR-009 exception hierarchy (inherit from `EvolutionError`)
- Clear, actionable error message helps users understand what went wrong
- Consistent with other validation errors in the codebase

**Error Message Template**:
```
"No LlmAgents found in workflow '{workflow.name}'. Workflow must contain at least one LlmAgent to evolve."
```

### 7. Workflow Structure Preservation

**Decision**: Evolution only modifies LlmAgent `instruction` attributes. Workflow hierarchy remains unchanged.

**Rationale**:
- `evolve_group()` already follows this pattern—it mutates instructions in place
- Workflow structure (agent order, nesting) is configuration, not the target of optimization
- Preserving structure ensures evolved workflows are directly usable

**Verification**: After evolution, assert that `workflow.sub_agents` references are unchanged (same object IDs).

## Technology Decisions Summary

| Decision | Choice | Key Reason |
|----------|--------|------------|
| Type detection | isinstance() checks | All agents have sub_agents; need type-specific check |
| Traversal | Recursive with depth limit | Clean, safe, handles nested workflows |
| Evolution | Delegate to evolve_group() | Reuses proven multi-agent infrastructure |
| Error handling | WorkflowEvolutionError | Follows ADR-009 hierarchy |
| Primary agent | Last LlmAgent in sequence | Natural output producer in pipelines |
| Instruction type | String only | InstructionProvider callables not supported for evolution |

## Open Questions (Resolved)

1. ✅ **Q**: Should `evolve_workflow()` support custom primary agent selection?
   **A**: Yes, add optional `primary` parameter with default to last discovered LlmAgent.

2. ✅ **Q**: How to handle LoopAgent's iterative nature?
   **A**: Treat LoopAgent same as SequentialAgent—find LlmAgents in `sub_agents`. Loop configuration (`max_iterations`) is preserved.

3. ✅ **Q**: How to handle ParallelAgent's concurrent branches?
   **A**: Find LlmAgents in all branches via `sub_agents`. Evolution uses sequential evaluation (share_session=True), not parallel.

4. ✅ **Q**: What if instruction is an InstructionProvider callable?
   **A**: Skip or error—only string instructions are evolvable. Document as limitation.
