# Data Model: Workflow Agent Evolution

**Feature**: 017-workflow-evolution  
**Date**: 2026-01-12  
**Status**: Complete

## Package Versions

- **google-adk**: 1.22.0
- **gepa**: 0.0.24 (dev dependency for reference patterns)

## Entities

### Existing Entities (from google-adk 1.22.0)

#### BaseAgent (from google.adk.agents.base_agent)
Base class for all agents. Defines common attributes.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Unique agent identifier |
| sub_agents | list[BaseAgent] | Child agents (default: empty list) |
| parent_agent | BaseAgent \| None | Parent agent reference |
| description | str \| None | Human-readable description |

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/base_agent.py:133`

#### LlmAgent (from google.adk.agents.llm_agent)
Agent type with `instruction` attribute that can be evolved.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Unique agent identifier |
| instruction | str \| InstructionProvider | Prompt instruction text (target of evolution) |
| model | str \| None | Model identifier (inherits from ancestor if not set) |
| output_key | str \| None | State key for storing output |
| static_instruction | ContentUnion \| None | Static content for caching optimization |
| global_instruction | str \| InstructionProvider | Instructions for entire agent tree (deprecated) |

**Note**: Only `str` instruction is supported for evolution. `InstructionProvider` callables are not evolvable.

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/llm_agent.py:203`

#### SequentialAgent (from google.adk.agents.sequential_agent)
Workflow agent executing sub-agents in sequence.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Workflow name |
| sub_agents | list[BaseAgent] | Ordered list of child agents |
| description | str \| None | Human-readable description |

**Behavior**: Iterates through `sub_agents` in order, calling each agent's `run_async`.

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/sequential_agent.py`

#### LoopAgent (from google.adk.agents.loop_agent)
Workflow agent executing sub-agents in a loop.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Workflow name |
| sub_agents | list[BaseAgent] | Agents to execute each iteration |
| max_iterations | int | Maximum loop iterations |

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/loop_agent.py`

#### ParallelAgent (from google.adk.agents.parallel_agent)
Workflow agent executing sub-agents concurrently.

| Attribute | Type | Description |
|-----------|------|-------------|
| name | str | Workflow name |
| sub_agents | list[BaseAgent] | Agents to execute in parallel |

**Source**: `.venv/lib/python3.12/site-packages/google/adk/agents/parallel_agent.py`

### Existing Entities (from gepa_adk)

#### EvolutionConfig (from gepa_adk.domain.models)
Configuration for evolution runs.

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| max_iterations | int | 50 | Maximum evolution iterations |
| max_concurrent_evals | int | 5 | Concurrent batch evaluations |
| min_improvement_threshold | float | 0.01 | Minimum score improvement |
| patience | int | 5 | Iterations without improvement before stopping |
| reflection_model | str | "gemini-2.5-flash" | Model for mutation |

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
