# Data Model: Workflow Agent Evolution

**Feature**: 017-workflow-evolution  
**Date**: 2026-01-12  
**Status**: Complete

## Entities

### Existing Entities (Reused)

#### LlmAgent (from google.adk.agents)
Agent type with `instruction` attribute that can be evolved.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Unique agent identifier |
| instruction | str | Prompt instruction text (target of evolution) |
| model | str | Model identifier |
| output_key | str \| None | State key for storing output |

#### SequentialAgent (from google.adk.agents)
Workflow agent executing sub-agents in sequence.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Workflow name |
| sub_agents | list[BaseAgent] | Ordered list of child agents |
| description | str \| None | Human-readable description |

#### LoopAgent (from google.adk.agents)
Workflow agent executing sub-agents in a loop.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Workflow name |
| sub_agents | list[BaseAgent] | Agents to execute each iteration |
| max_iterations | int | Maximum loop iterations |

#### ParallelAgent (from google.adk.agents)
Workflow agent executing sub-agents concurrently.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Workflow name |
| sub_agents | list[BaseAgent] | Agents to execute in parallel |

#### EvolutionConfig (from gepa_adk.domain.models)
Configuration for evolution runs.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| max_iterations | int | 50 | Maximum evolution iterations |
| max_concurrent_evals | int | 5 | Concurrent batch evaluations |
| min_improvement_threshold | float | 0.01 | Minimum score improvement |
| patience | int | 5 | Iterations without improvement before stopping |
| reflection_model | str | "gemini-2.0-flash" | Model for mutation |

#### MultiAgentEvolutionResult (from gepa_adk.domain.models)
Result from evolving multiple agents together.

| Attribute | Type | Description |
|-----------|------|-------------|
| evolved_instructions | dict[str, str] | Agent name → evolved instruction |
| original_score | float | Score before evolution |
| final_score | float | Best score achieved |
| primary_agent | str | Name of primary agent |
| iteration_history | list[IterationRecord] | Evolution trace |
| total_iterations | int | Total iterations executed |

### New Entities

#### WorkflowEvolutionError (new exception)
Exception raised when workflow evolution fails.

| Attribute | Type | Description |
|-----------|------|-------------|
| message | str | Human-readable error description |
| workflow_name | str \| None | Name of workflow that failed |
| cause | Exception \| None | Underlying exception if any |

**Inherits from**: `EvolutionError`

**Usage**:
```python
raise WorkflowEvolutionError(
    "No LlmAgents found in workflow",
    workflow_name="MyPipeline",
)
```

## Type Aliases

```python
# Union type for all workflow agent types
WorkflowAgentType = SequentialAgent | LoopAgent | ParallelAgent

# Type alias for workflow or LLM agent
AgentType = LlmAgent | WorkflowAgentType
```

## Relationships

```
┌──────────────────────────────────────────────────────────────┐
│                    Workflow Structure                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────┐                                        │
│   │ SequentialAgent │──sub_agents──►┌───────────┐            │
│   │  / LoopAgent /  │               │ LlmAgent  │ ◄─evolves  │
│   │ ParallelAgent   │               ├───────────┤            │
│   └────────┬────────┘               │ LlmAgent  │ ◄─evolves  │
│            │                        ├───────────┤            │
│            │                        │ParallelAg.│──►...      │
│            ▼                        └───────────┘            │
│   ┌─────────────────┐                                        │
│   │   sub_agents    │ (can contain workflow agents           │
│   │   (recursive)   │  or LlmAgents at any level)            │
│   └─────────────────┘                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## State Transitions

### Evolution Process

```
┌─────────────┐     ┌────────────────────┐     ┌────────────────┐
│  Workflow   │────►│ find_llm_agents()  │────►│ list[LlmAgent] │
│   Input     │     │  (recursive scan)  │     │   discovered   │
└─────────────┘     └────────────────────┘     └───────┬────────┘
                                                       │
                                                       ▼
┌─────────────┐     ┌────────────────────┐     ┌────────────────┐
│ Workflow    │◄────│ evolve_group()     │◄────│ Validate       │
│ (evolved)   │     │ (existing engine)  │     │ (≥1 LlmAgent)  │
└─────────────┘     └────────────────────┘     └────────────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │ MultiAgentEvolution│
                    │ Result             │
                    └────────────────────┘
```

## Validation Rules

| Rule | Entity | Constraint |
|------|--------|------------|
| V-001 | Workflow | Must contain at least one LlmAgent (raises WorkflowEvolutionError) |
| V-002 | max_depth | Must be positive integer (≥1) |
| V-003 | trainset | Must be non-empty list (existing validation) |
| V-004 | primary | If specified, must match an LlmAgent name in workflow |
