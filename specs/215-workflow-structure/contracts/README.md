# Contracts: Execute Workflows As-Is

**Feature**: 215-workflow-structure

## No New Protocols Required

This feature extends existing adapter behavior without introducing new protocols or ports.

### Existing Contracts Used

| Protocol | Location | Usage |
|----------|----------|-------|
| `AsyncGEPAAdapter` | `ports/adapter.py` | `MultiAgentAdapter` already implements this |

### New Function Signature

```python
# adapters/workflow.py

def clone_workflow_with_overrides(
    workflow: SequentialAgent | LoopAgent | ParallelAgent | LlmAgent,
    candidate: dict[str, str],
) -> SequentialAgent | LoopAgent | ParallelAgent | LlmAgent:
    """Clone workflow with instruction overrides applied to LlmAgents.

    Args:
        workflow: Original workflow to clone.
        candidate: Qualified component names to instruction text mapping.

    Returns:
        Cloned workflow with same structure, instruction overrides applied.

    Invariants:
        - type(result) == type(workflow)
        - For LoopAgent: result.max_iterations == workflow.max_iterations
        - For all workflows: len(result.sub_agents) == len(workflow.sub_agents)
    """
```

### Type Hints

```python
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

WorkflowAgentType = SequentialAgent | LoopAgent | ParallelAgent
AnyAgentType = WorkflowAgentType | LlmAgent
```
