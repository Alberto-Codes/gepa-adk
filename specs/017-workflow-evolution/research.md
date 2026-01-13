# Research: Workflow Agent Evolution

**Feature**: 017-workflow-evolution  
**Date**: 2026-01-12  
**Status**: Complete

## Research Tasks

### 1. ADK Workflow Agent Types and `sub_agents` Attribute

**Decision**: Use isinstance() checks against SequentialAgent, LoopAgent, ParallelAgent from `google.adk.agents`.

**Rationale**: The ADK documentation confirms all three workflow agent types:
- `SequentialAgent`: Executes sub-agents in sequence via `sub_agents` list
- `LoopAgent`: Executes sub-agents in a loop with `sub_agents` list and `max_iterations` parameter
- `ParallelAgent`: Executes sub-agents concurrently via `sub_agents` list

All workflow agents have a consistent `sub_agents` attribute containing child agents.

**Alternatives Considered**:
- Duck typing (check for `sub_agents` attribute): Rejected because custom agents could have `sub_agents` but not be workflow agents
- Base class check: ADK doesn't expose a common workflow base class in its public API

**Source**: https://google.github.io/adk-docs/agents/workflow-agents/

### 2. LlmAgent Detection Strategy

**Decision**: Use `isinstance(agent, LlmAgent)` to identify agents that can be evolved.

**Rationale**: LlmAgent is the only agent type with `instruction` attribute that can be mutated during evolution. The ADK documentation distinguishes LlmAgent from workflow agents clearly:
- LlmAgent: Has `instruction`, `model`, `output_key` attributes
- Workflow agents: Orchestrate sub-agents, no `instruction` attribute

**Alternatives Considered**:
- Check for `instruction` attribute: Rejected because future agent types might have instructions but not be evolvable
- Check for callable `instruction`: Not needed since we only support string instructions (documented limitation)

**Source**: https://google.github.io/adk-docs/agents/llm-agents/

### 3. Recursive Traversal with Depth Limiting

**Decision**: Implement recursive `find_llm_agents()` with `max_depth` parameter (default: 5) and `current_depth` counter.

**Rationale**: 
- Prevents infinite recursion in deeply nested or malformed workflows
- Default depth of 5 matches typical workflow complexity (most workflows are 2-3 levels)
- Depth limiting is a common pattern for tree traversal safety

**Implementation Pattern**:
```python
def find_llm_agents(agent, max_depth: int = 5, current_depth: int = 0) -> list[LlmAgent]:
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
- Visited set to prevent cycles: Rejected because ADK agent hierarchies are tree-structured (no cycles expected)
- Iterative with explicit stack: More complex, recursive is clearer and Python recursion limit is sufficient

### 4. Integration with `evolve_group()`

**Decision**: `evolve_workflow()` finds all LlmAgents, then delegates to `evolve_group()` with `share_session=True`.

**Rationale**:
- `evolve_group()` already handles multi-agent evolution with session state sharing
- The last agent in a sequential workflow typically produces the final output, making it the natural `primary` agent
- Session sharing preserves workflow context during evaluation (agents can access earlier outputs)

**Key Integration Points**:
- `agents`: All discovered LlmAgents from the workflow
- `primary`: Last LlmAgent in discovered list (for sequential workflows) or configurable
- `share_session=True`: Maintains workflow execution context

**Alternatives Considered**:
- Custom evaluation loop: Rejected because `evolve_group()` already provides all needed functionality
- Evolve agents individually: Rejected because it loses workflow context and agent coordination

### 5. Error Handling for Empty Workflows

**Decision**: Raise `WorkflowEvolutionError` (new exception class) when no LlmAgents are found.

**Rationale**:
- Follows ADR-009 exception hierarchy (inherit from `EvolutionError`)
- Clear, actionable error message helps users understand what went wrong
- Consistent with other validation errors in the codebase

**Error Message Template**:
```
"No LlmAgents found in workflow '{workflow.name}'. Workflow must contain at least one LlmAgent to evolve."
```

### 6. Workflow Structure Preservation

**Decision**: Evolution only modifies LlmAgent `instruction` attributes. Workflow hierarchy remains unchanged.

**Rationale**:
- `evolve_group()` already follows this pattern—it mutates instructions in place
- Workflow structure (agent order, nesting) is configuration, not the target of optimization
- Preserving structure ensures evolved workflows are directly usable

**Verification**: After evolution, assert that `workflow.sub_agents` references are unchanged (same object IDs).

## Technology Decisions Summary

| Decision | Choice | Key Reason |
|----------|--------|------------|
| Type detection | isinstance() checks | ADK doesn't expose workflow base class |
| Traversal | Recursive with depth limit | Clean, safe, handles nested workflows |
| Evolution | Delegate to evolve_group() | Reuses proven multi-agent infrastructure |
| Error handling | WorkflowEvolutionError | Follows ADR-009 hierarchy |
| Primary agent | Last LlmAgent in sequence | Natural output producer in pipelines |

## Open Questions (Resolved)

1. ✅ **Q**: Should `evolve_workflow()` support custom primary agent selection?
   **A**: Yes, add optional `primary` parameter with default to last discovered LlmAgent.

2. ✅ **Q**: How to handle LoopAgent's iterative nature?
   **A**: Treat LoopAgent same as SequentialAgent—find LlmAgents in `sub_agents`. Loop configuration (`max_iterations`) is preserved.

3. ✅ **Q**: How to handle ParallelAgent's concurrent branches?
   **A**: Find LlmAgents in all branches via `sub_agents`. Evolution uses sequential evaluation (share_session=True), not parallel.
