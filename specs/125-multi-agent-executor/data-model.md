# Data Model: Multi-Agent Unified Executor

**Feature**: 125-multi-agent-executor
**Date**: 2026-01-19

## Entity Overview

This feature extends existing entities rather than creating new ones. The primary change is adding an optional `executor` dependency to `MultiAgentAdapter`.

## Modified Entities

### MultiAgentAdapter (Extended)

**Location**: `src/gepa_adk/adapters/multi_agent.py`

```python
class MultiAgentAdapter:
    """Adapter for multi-agent pipeline evaluation.

    Extended with executor parameter for unified agent execution.
    """

    def __init__(
        self,
        agents: list[LlmAgent],
        primary: str,
        scorer: Scorer | None = None,
        share_session: bool = True,
        session_service: BaseSessionService | None = None,
        app_name: str = "multi_agent_eval",
        trajectory_config: TrajectoryConfig | None = None,
        proposer: AsyncReflectiveMutationProposer | None = None,
        reflection_model: str = "ollama_chat/gpt-oss:20b",
        reflection_prompt: str | None = None,
        executor: AgentExecutorProtocol | None = None,  # NEW
    ) -> None:
        ...
        self._executor = executor  # Store for execution methods
```

**New Attribute**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `_executor` | `AgentExecutorProtocol \| None` | Optional unified executor for consistent agent execution |

## Existing Entities (Used, Not Modified)

### AgentExecutorProtocol

**Location**: `src/gepa_adk/ports/agent_executor.py`

Protocol interface defining unified execution contract. Already exists from PR #138.

```python
@runtime_checkable
class AgentExecutorProtocol(Protocol):
    async def execute_agent(
        self,
        agent: Any,
        input_text: str,
        *,
        instruction_override: str | None = None,
        output_schema_override: Any | None = None,
        session_state: dict[str, Any] | None = None,
        existing_session_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> ExecutionResult: ...
```

### AgentExecutor

**Location**: `src/gepa_adk/adapters/agent_executor.py`

Implementation of AgentExecutorProtocol. Already exists from PR #138.

### ExecutionResult

**Location**: `src/gepa_adk/ports/agent_executor.py`

Dataclass for agent execution results. Already exists from PR #138.

```python
@dataclass
class ExecutionResult:
    status: ExecutionStatus
    session_id: str
    extracted_value: str | None = None
    error_message: str | None = None
    execution_time_seconds: float = 0.0
    captured_events: list[Any] | None = field(default=None)
```

### CriticScorer (Already Has Executor)

**Location**: `src/gepa_adk/adapters/critic_scorer.py`

Already supports executor parameter from PR #138. No modifications needed.

## Data Flow

```
evolve_group()
    │
    ├── Creates AgentExecutor(session_service)
    │
    ├── Creates CriticScorer(critic, executor=executor)
    │       └── Uses executor for critic scoring
    │
    ├── Creates MultiAgentAdapter(agents, executor=executor)
    │       ├── _run_shared_session() uses executor
    │       └── _run_isolated_sessions() uses executor
    │
    └── Creates adk_reflection_fn(agent, executor=executor)
            └── Uses executor for reflection calls
```

## Session State Sharing

When executor is provided:
- All components share the same `InMemorySessionService` via the executor
- Session IDs can be passed between agents for state sharing
- Logs include `uses_executor=True` for observability

## Backward Compatibility

| API | Change | Compatibility |
|-----|--------|---------------|
| `MultiAgentAdapter.__init__()` | New optional `executor` param | ✅ Backward compatible |
| `evolve_group()` | Internal executor creation | ✅ No signature change |
| `evolve_workflow()` | Inherits from `evolve_group()` | ✅ No changes needed |
