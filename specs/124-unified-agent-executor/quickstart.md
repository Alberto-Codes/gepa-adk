# Quickstart: Unified Agent Executor

**Feature**: 124-unified-agent-executor
**Date**: 2026-01-19

## Overview

The Unified Agent Executor provides a single execution path for all ADK agents (generator, critic, reflection) with consistent behavior, session management, and result handling.

---

## Basic Usage

### Execute an Agent

```python
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.ports.agent_executor import ExecutionStatus

# Create executor
executor = AgentExecutor()

# Execute agent
result = await executor.execute_agent(
    agent=my_agent,
    input_text="Hello, world!",
)

# Check result
if result.status == ExecutionStatus.SUCCESS:
    print(f"Output: {result.extracted_value}")
else:
    print(f"Error: {result.error_message}")
```

### With Instruction Override (Evolution)

```python
# Test a mutated instruction without modifying the agent
result = await executor.execute_agent(
    agent=my_agent,
    input_text="Hello!",
    instruction_override="You are an extremely formal assistant.",
)
# Original agent.instruction unchanged
```

### With Session State (Reflection)

```python
# Inject template variables for reflection agent
result = await executor.execute_agent(
    agent=reflection_agent,
    input_text="Improve the instruction",
    session_state={
        "component_text": "Be helpful and concise.",
        "trials": '[{"input": "Hi", "output": "Hey", "feedback": {"score": 0.5}}]',
    },
)
# Agent instruction can use {component_text} and {trials}
```

### Session Sharing (Critic Access)

```python
# Generator creates session
gen_result = await executor.execute_agent(
    agent=generator,
    input_text="Write a haiku about coding.",
)

# Critic reuses session to access generator's state
critic_result = await executor.execute_agent(
    agent=critic,
    input_text=f"Evaluate this haiku: {gen_result.extracted_value}",
    existing_session_id=gen_result.session_id,
)
```

### With Timeout

```python
result = await executor.execute_agent(
    agent=my_agent,
    input_text="Complex task...",
    timeout_seconds=60,  # Default is 300
)

if result.status == ExecutionStatus.TIMEOUT:
    print(f"Execution timed out after {result.execution_time_seconds}s")
    # Partial events may still be available
    print(f"Events captured: {len(result.captured_events or [])}")
```

---

## Integration with Evolution

### In ADKAdapter (Internal)

```python
# ADKAdapter now uses AgentExecutor internally
class ADKEvolutionAdapter:
    def __init__(self, agent, executor: AgentExecutorProtocol | None = None):
        self._executor = executor or AgentExecutor()

    async def _run_single_example(self, input_text: str) -> tuple[str, list]:
        result = await self._executor.execute_agent(
            agent=self._agent,
            input_text=input_text,
            instruction_override=self._current_instruction,
        )
        return result.extracted_value, result.captured_events
```

### In CriticScorer (Internal)

```python
# CriticScorer now uses AgentExecutor internally
class CriticScorer:
    async def async_score(self, input_text, output, session_id=None):
        result = await self._executor.execute_agent(
            agent=self._critic,
            input_text=self._format_input(input_text, output),
            existing_session_id=session_id,
        )
        return self._parse_score(result.extracted_value)
```

### In Reflection (Internal)

```python
# Reflection function now uses AgentExecutor internally
def create_adk_reflection_fn(reflection_agent, executor=None):
    executor = executor or AgentExecutor()

    async def reflect(component_text: str, trials: list) -> str:
        result = await executor.execute_agent(
            agent=reflection_agent,
            input_text="Improve the instruction",
            session_state={
                "component_text": component_text,
                "trials": json.dumps(trials),
            },
        )
        return result.extracted_value or ""

    return reflect
```

---

## ExecutionResult Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | `ExecutionStatus` | SUCCESS, FAILED, or TIMEOUT |
| `session_id` | `str` | ADK session identifier |
| `extracted_value` | `str \| None` | Agent output text |
| `error_message` | `str \| None` | Error details (if failed/timeout) |
| `execution_time_seconds` | `float` | Execution duration |
| `captured_events` | `list \| None` | ADK events for debugging |

---

## Error Handling

```python
from gepa_adk.ports.agent_executor import ExecutionStatus

result = await executor.execute_agent(...)

match result.status:
    case ExecutionStatus.SUCCESS:
        # Use result.extracted_value
        pass
    case ExecutionStatus.FAILED:
        # Handle error, check result.error_message
        logger.error("Execution failed", error=result.error_message)
    case ExecutionStatus.TIMEOUT:
        # Handle timeout gracefully
        logger.warning("Execution timed out",
                      duration=result.execution_time_seconds)
```

---

## Testing

### Mock Executor for Unit Tests

```python
from unittest.mock import AsyncMock
from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

# Create mock executor
mock_executor = AsyncMock()
mock_executor.execute_agent.return_value = ExecutionResult(
    status=ExecutionStatus.SUCCESS,
    session_id="test_session",
    extracted_value="Mocked output",
    execution_time_seconds=0.1,
)

# Inject into component under test
adapter = ADKEvolutionAdapter(agent, executor=mock_executor)
```

---

## Backward Compatibility

The public API is unchanged:

```python
# These still work exactly the same
from gepa_adk import evolve, evolve_sync, EvolutionConfig

result = evolve_sync(agent, trainset, config=config)
# Internal implementation now uses AgentExecutor
```
