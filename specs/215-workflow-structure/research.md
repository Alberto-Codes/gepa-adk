# Research: Execute Workflows As-Is (Preserve Structure)

**Feature**: 215-workflow-structure
**Date**: 2026-01-22

## Research Questions

### Q1: How does LoopAgent store its inner agent(s)?

**Decision**: LoopAgent uses `sub_agents` (same as other workflow agents), not a separate `agent` property.

**Rationale**: Inspection of ADK's LoopAgent model fields shows:
```python
['name', 'description', 'parent_agent', 'sub_agents', 'before_agent_callback', 'after_agent_callback', 'max_iterations']
```

The `sub_agents` list contains the agent(s) to iterate over. The `max_iterations` field controls how many times the loop executes.

**Alternatives considered**:
- GitHub issue #215 proposed `LoopAgent.agent` (singular) - this is incorrect per ADK implementation
- ADK uses consistent `sub_agents` across all workflow agents for uniformity

**Source**: [Google ADK Loop Agents Documentation](https://google.github.io/adk-docs/agents/workflow-agents/loop-agents/)

---

### Q2: How does model_copy() work with ADK agents?

**Decision**: Use `model_copy(update={...})` for cloning agents with modified fields.

**Rationale**: ADK agents are Pydantic v2 models. The `model_copy()` method creates a shallow copy with optional field updates. This is the established pattern already used in `_build_pipeline()`:

```python
cloned = agent.model_copy(update=updates)
```

**Key consideration**: Must clear `parent_agent` before re-parenting to avoid ADK ValueError (an agent can only have one parent).

**Alternatives considered**:
- Deep copy with `copy.deepcopy()` - heavier, not needed
- Creating new instances - loses non-modified fields

---

### Q3: What properties must be preserved for each workflow agent type?

**Decision**: Preserve the following properties during cloning:

| Agent Type | Properties to Preserve |
|------------|----------------------|
| SequentialAgent | `name`, `sub_agents` (order matters) |
| LoopAgent | `name`, `sub_agents`, `max_iterations` |
| ParallelAgent | `name`, `sub_agents` |
| LlmAgent | All fields except `instruction` (override), `parent_agent` (clear) |

**Rationale**:
- `max_iterations` is critical for LoopAgent - this is the whole point of the feature
- `sub_agents` must be recursively cloned (not referenced) to apply instruction overrides
- `name` preserved for logging and debugging

---

### Q4: How should recursive cloning handle the `parent_agent` field?

**Decision**: Clear `parent_agent` on all cloned agents before constructing the new workflow hierarchy.

**Rationale**: ADK enforces single-parent constraint. When constructing a new workflow tree with cloned agents:
1. Clone each agent with `parent_agent=None`
2. Pass cloned agents to parent constructor
3. ADK automatically sets `parent_agent` during construction

This is already the pattern in `_build_pipeline()`:
```python
updates["parent_agent"] = None
cloned = agent.model_copy(update=updates)
```

---

### Q5: Where should the cloning function live?

**Decision**: Add `clone_workflow_with_overrides()` to `workflow.py` in the adapters layer.

**Rationale**:
- `workflow.py` already contains workflow traversal utilities (`find_llm_agents`, `is_workflow_agent`)
- Keeps ADK-specific code in adapters layer per ADR-000
- Function can be reused by both `MultiAgentAdapter` and future workflow-related features
- Maintains single responsibility: workflow.py handles workflow operations

**Alternatives considered**:
- Adding directly to `multi_agent.py` - grows an already large file (1500+ lines)
- Creating new `workflow_cloning.py` - over-engineering for one function

---

### Q6: How should the cloned workflow be executed?

**Decision**: Replace SequentialAgent wrapper with the cloned original workflow structure.

**Rationale**: Currently `_build_pipeline()` returns a `SequentialAgent` wrapping cloned agents. The new implementation should:
1. Clone the original workflow structure (preserving type)
2. Return the cloned workflow directly
3. Let ADK Runner execute with native semantics

**Key insight**: `MultiAgentAdapter` receives the original workflow at initialization. We need to store this root workflow reference for cloning.

---

### Q7: How to handle output extraction for LoopAgent?

**Decision**: Use final iteration output from the designated primary agent.

**Rationale**:
- LoopAgent executes sub_agents N times
- Each iteration produces output captured in session state
- For scoring, use the output from the last iteration (most refined)
- Trajectory captures all iterations for debugging/analysis

**Note**: This aligns with spec requirement FR-010.

---

## Implementation Decisions Summary

| Decision | Choice | Impact |
|----------|--------|--------|
| Inner agent storage | Use `sub_agents` consistently | Compatible with ADK |
| Cloning method | `model_copy(update={...})` | Reuse existing pattern |
| Properties preserved | Type-specific (max_iterations for Loop) | Correct semantics |
| Parent handling | Clear before clone, let ADK re-set | Avoid ValueError |
| Code location | `workflow.py` | Follows existing structure |
| Execution | Return cloned workflow directly | Native ADK execution |
| Output extraction | Final iteration output | Per spec FR-010 |
