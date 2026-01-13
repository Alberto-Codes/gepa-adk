# API Contract: Workflow Evolution

**Feature**: 017-workflow-evolution  
**Date**: 2026-01-12  
**Version**: 1.0.0

## Public Functions

### `evolve_workflow()`

Evolves all LlmAgents within a workflow agent structure.

**Signature**:
```python
async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
) -> MultiAgentEvolutionResult:
    ...
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| workflow | SequentialAgent \| LoopAgent \| ParallelAgent | Yes | - | Workflow agent containing LlmAgents to evolve |
| trainset | list[dict[str, Any]] | Yes | - | Training examples with "input" and optional "expected" keys |
| critic | LlmAgent \| None | No | None | Critic agent for scoring. If None, uses primary's output_schema |
| primary | str \| None | No | None | Name of agent to score. Defaults to last LlmAgent found |
| max_depth | int | No | 5 | Maximum recursion depth for nested workflows |
| config | EvolutionConfig \| None | No | None | Evolution configuration. Uses defaults if None |

**Returns**: `MultiAgentEvolutionResult`

**Raises**:
- `WorkflowEvolutionError`: If workflow contains no LlmAgents
- `MultiAgentValidationError`: If primary agent not found or no scorer available
- `EvolutionError`: If evolution fails during execution

**Example**:
```python
from google.adk.agents import LlmAgent, SequentialAgent
from gepa_adk import evolve_workflow

pipeline = SequentialAgent(
    name="Pipeline",
    sub_agents=[agent1, agent2, agent3],
)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=[{"input": "test", "expected": "result"}],
)
```

---

### `is_workflow_agent()`

Check if an agent is a workflow type.

**Signature**:
```python
def is_workflow_agent(agent: Any) -> bool:
    ...
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| agent | Any | Yes | Agent to check |

**Returns**: `bool` - True if agent is SequentialAgent, LoopAgent, or ParallelAgent

**Example**:
```python
from gepa_adk.adapters.workflow import is_workflow_agent

assert is_workflow_agent(SequentialAgent(...)) == True
assert is_workflow_agent(LlmAgent(...)) == False
```

---

### `find_llm_agents()`

Recursively find all LlmAgents in a workflow.

**Signature**:
```python
def find_llm_agents(
    agent: Any,
    max_depth: int = 5,
    current_depth: int = 0,
) -> list[LlmAgent]:
    ...
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| agent | Any | Yes | - | Agent or workflow to search |
| max_depth | int | No | 5 | Maximum recursion depth |
| current_depth | int | No | 0 | Current recursion level (internal use) |

**Returns**: `list[LlmAgent]` - All LlmAgents found up to max_depth

**Example**:
```python
from gepa_adk.adapters.workflow import find_llm_agents

agents = find_llm_agents(nested_workflow, max_depth=3)
print(f"Found {len(agents)} LlmAgents")
```

---

## Exception Classes

### `WorkflowEvolutionError`

Exception raised when workflow evolution fails.

**Signature**:
```python
class WorkflowEvolutionError(EvolutionError):
    def __init__(
        self,
        message: str,
        *,
        workflow_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        ...
```

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| message | str | Human-readable error description |
| workflow_name | str \| None | Name of the workflow that failed |
| cause | Exception \| None | Underlying exception if any |

**Example**:
```python
from gepa_adk.domain.exceptions import WorkflowEvolutionError

try:
    result = await evolve_workflow(...)
except WorkflowEvolutionError as e:
    print(f"Workflow '{e.workflow_name}' failed: {e}")
```

---

## Type Aliases

```python
# Type alias for workflow agent types (internal use)
WorkflowAgentType = SequentialAgent | LoopAgent | ParallelAgent
```

---

## Module Locations

| Function/Class | Module |
|----------------|--------|
| `evolve_workflow` | `gepa_adk.api` |
| `is_workflow_agent` | `gepa_adk.adapters.workflow` |
| `find_llm_agents` | `gepa_adk.adapters.workflow` |
| `WorkflowEvolutionError` | `gepa_adk.domain.exceptions` |

---

## Re-exports

The `gepa_adk` package `__init__.py` should export:

```python
from gepa_adk.api import evolve_workflow

__all__ = [
    # ... existing exports ...
    "evolve_workflow",
]
```
