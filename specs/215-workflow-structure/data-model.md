# Data Model: Execute Workflows As-Is (Preserve Structure)

**Feature**: 215-workflow-structure
**Date**: 2026-01-22

## Overview

This feature modifies workflow cloning behavior, not domain models. No new data structures are introduced. The key change is how existing ADK agent types are cloned and composed.

## Existing Entities (No Changes)

### ADK Agent Types (External)

These are ADK-provided types; we clone them, not modify them:

```
LlmAgent
├── name: str
├── instruction: str | InstructionProvider
├── output_key: str | None
├── parent_agent: BaseAgent | None
└── ... (other LLM-specific fields)

SequentialAgent
├── name: str
├── sub_agents: list[BaseAgent]
├── parent_agent: BaseAgent | None
└── ... (inherited from BaseAgent)

LoopAgent
├── name: str
├── sub_agents: list[BaseAgent]
├── max_iterations: int        # CRITICAL: Must be preserved
├── parent_agent: BaseAgent | None
└── ... (inherited from BaseAgent)

ParallelAgent
├── name: str
├── sub_agents: list[BaseAgent]
├── parent_agent: BaseAgent | None
└── ... (inherited from BaseAgent)
```

### Domain Types (No Changes)

Existing gepa-adk types remain unchanged:

```
ComponentSpec
├── agent: str
├── component: str
└── qualified: QualifiedComponentName (property)

Candidate (dict alias)
└── QualifiedComponentName -> str
    Example: {"generator.instruction": "...", "critic.instruction": "..."}
```

## Cloning Behavior

### Current Behavior (Problem)

```
_build_pipeline(candidate) -> SequentialAgent
    Input: {agent_name: LlmAgent}
    Output: SequentialAgent wrapping ALL agents sequentially

    Result: LoopAgent(max_iterations=3) becomes [inner_agent] (1 execution)
```

### New Behavior (Solution)

```
clone_workflow_with_overrides(workflow, candidate) -> WorkflowAgentType
    Input: Original workflow (any type)
    Output: Cloned workflow with same structure

    Result: LoopAgent(max_iterations=3) stays LoopAgent(max_iterations=3)
```

## Cloning Rules by Type

| Agent Type | Clone Method | Preserved Fields | Modified Fields |
|------------|--------------|------------------|-----------------|
| LlmAgent | `model_copy(update={...})` | All except instruction | `instruction` (from candidate), `parent_agent=None` |
| SequentialAgent | Constructor with cloned sub_agents | `name` | `sub_agents` (recursively cloned) |
| LoopAgent | Constructor with cloned sub_agents | `name`, `max_iterations` | `sub_agents` (recursively cloned) |
| ParallelAgent | Constructor with cloned sub_agents | `name` | `sub_agents` (recursively cloned) |

## Workflow Traversal Order

```
clone_workflow_with_overrides(workflow, candidate):
    1. Check workflow type
    2. If LlmAgent:
       - Look up instruction override in candidate
       - Return cloned agent with override applied
    3. If workflow agent (Sequential/Loop/Parallel):
       - Recursively clone each sub_agent
       - Construct new workflow with cloned sub_agents
       - Preserve type-specific properties (max_iterations)
    4. Return cloned workflow
```

## State Flow During Evaluation

```
evaluate(example, candidate):
    1. Store original workflow reference (first call only)
    2. _apply_candidate() - apply non-instruction components to originals
    3. clone_workflow_with_overrides() - create cloned workflow with instructions
    4. Execute cloned workflow via ADK Runner
       - LoopAgent: N iterations
       - ParallelAgent: concurrent execution
       - SequentialAgent: in-order execution
    5. _restore_agents() - restore originals
    6. Return trajectory
```

## Key Invariants

1. **Type preservation**: `type(clone_workflow_with_overrides(w, c)) == type(w)`
2. **Iteration preservation**: `cloned_loop.max_iterations == original_loop.max_iterations`
3. **Structure preservation**: Workflow tree shape is identical before/after cloning
4. **Candidate key format**: Always `{agent_name}.{component}` per ADR-012
