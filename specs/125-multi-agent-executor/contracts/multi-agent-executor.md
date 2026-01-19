# Contract: Multi-Agent Executor Integration

**Feature**: 125-multi-agent-executor
**Date**: 2026-01-19
**Type**: Internal API Extension

## Overview

This contract defines the integration of `AgentExecutorProtocol` into `MultiAgentAdapter` and the `evolve_group()` API function.

## Contract: MultiAgentAdapter Executor Parameter

### FR-001: Constructor Accepts Executor

```python
from gepa_adk.adapters.multi_agent import MultiAgentAdapter
from gepa_adk.adapters.agent_executor import AgentExecutor
from gepa_adk.ports.agent_executor import AgentExecutorProtocol

def test_multi_agent_adapter_accepts_executor():
    """MultiAgentAdapter MUST accept optional executor parameter."""
    executor = AgentExecutor()

    # Verify parameter is accepted (FR-001)
    adapter = MultiAgentAdapter(
        agents=[mock_agent],
        primary="mock_agent",
        scorer=mock_scorer,
        executor=executor,  # Type: AgentExecutorProtocol | None
    )

    assert adapter._executor is executor
```

### FR-002: Executor Used for All Agent Executions

```python
async def test_executor_used_for_all_executions():
    """When executor provided, all agent executions MUST use it (FR-002)."""
    executor = MockExecutor()  # Tracks execute_agent calls

    adapter = MultiAgentAdapter(
        agents=[agent1, agent2],
        primary="agent1",
        scorer=mock_scorer,
        executor=executor,
    )

    await adapter.evaluate(batch, candidate)

    # All agents should have used the executor
    assert executor.execute_count >= len(batch)
```

### FR-009: Backward Compatibility Without Executor

```python
def test_backward_compatibility_without_executor():
    """System MUST work when no executor provided (FR-009)."""
    # No executor parameter - should use legacy execution
    adapter = MultiAgentAdapter(
        agents=[mock_agent],
        primary="mock_agent",
        scorer=mock_scorer,
        # executor not provided
    )

    # Should not raise
    assert adapter._executor is None
```

## Contract: evolve_group() Executor Management

### FR-003: Creates Executor When Not Provided

```python
async def test_evolve_group_creates_executor():
    """evolve_group() MUST create AgentExecutor when not provided (FR-003)."""
    # Call evolve_group - it should create executor internally
    result = await evolve_group(
        agents=[agent],
        primary="agent",
        trainset=trainset,
        critic=critic,
    )

    # Verify execution completed (executor was created and used)
    assert result.best_score >= 0
```

### FR-004: Executor Passed to All Components

```python
async def test_evolve_group_passes_executor():
    """evolve_group() MUST pass executor to MultiAgentAdapter (FR-004)."""
    # This is verified by checking logs for uses_executor=True

    with capture_logs() as logs:
        await evolve_group(
            agents=[agent],
            primary="agent",
            trainset=trainset,
            critic=critic,
        )

    # All adapter logs should show uses_executor=True
    adapter_logs = [l for l in logs if "adapter.evaluate" in l["event"]]
    assert all(l.get("uses_executor") for l in adapter_logs)
```

### FR-005: CriticScorer Receives Executor

```python
async def test_critic_scorer_receives_executor():
    """CriticScorer created in evolve_group() MUST receive executor (FR-005)."""
    with capture_logs() as logs:
        await evolve_group(
            agents=[agent],
            primary="agent",
            trainset=trainset,
            critic=critic,
        )

    # Scorer logs should show uses_executor=True
    scorer_logs = [l for l in logs if "scorer" in l["event"]]
    assert all(l.get("uses_executor") for l in scorer_logs)
```

### FR-006: Reflection Function Receives Executor

```python
async def test_reflection_fn_receives_executor():
    """Reflection functions MUST receive executor (FR-006)."""
    with capture_logs() as logs:
        await evolve_group(
            agents=[agent],
            primary="agent",
            trainset=trainset,
            critic=critic,
            reflection_agent=reflector,
        )

    # Reflection logs should show uses_executor=True
    reflection_logs = [l for l in logs if "reflection" in l["event"]]
    assert all(l.get("uses_executor") for l in reflection_logs)
```

## Contract: Workflow Evolution Support

### FR-007: evolve_workflow() Inherits Support

```python
async def test_evolve_workflow_inherits_executor():
    """evolve_workflow() MUST inherit executor support (FR-007)."""
    # evolve_workflow delegates to evolve_group
    result = await evolve_workflow(
        workflow=sequential_workflow,
        trainset=trainset,
        critic=critic,
    )

    # Should complete without error, using executor internally
    assert result.best_score >= 0
```

## Contract: Observability

### FR-008: Logs Show uses_executor=True

```python
async def test_all_logs_show_uses_executor():
    """All agent executions MUST log uses_executor=True (FR-008)."""
    with capture_logs() as logs:
        await evolve_group(
            agents=[agent],
            primary="agent",
            trainset=trainset,
            critic=critic,
        )

    # Filter for execution-related logs
    execution_logs = [
        l for l in logs
        if any(k in l["event"] for k in ["evaluate", "score", "reflection", "execution"])
    ]

    # All should have uses_executor field set to True
    for log in execution_logs:
        if "uses_executor" in log:
            assert log["uses_executor"] is True, f"Log {log['event']} has uses_executor=False"
```

## Test Utilities

### MockExecutor

```python
from gepa_adk.ports.agent_executor import AgentExecutorProtocol, ExecutionResult, ExecutionStatus

class MockExecutor:
    """Mock executor for contract testing."""

    def __init__(self):
        self.execute_count = 0
        self.calls: list[dict] = []

    async def execute_agent(
        self,
        agent,
        input_text: str,
        **kwargs,
    ) -> ExecutionResult:
        self.execute_count += 1
        self.calls.append({
            "agent": agent,
            "input_text": input_text,
            **kwargs,
        })
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="mock_session",
            extracted_value="mock output",
        )

# Verify it implements protocol
assert isinstance(MockExecutor(), AgentExecutorProtocol)
```

## Edge Cases

### EC-1: Executor Cleanup on Agent Failure

```python
async def test_executor_cleanup_on_failure():
    """Session state MUST be cleaned up when agent fails mid-execution."""
    failing_executor = MockExecutorThatFails()

    adapter = MultiAgentAdapter(
        agents=[agent],
        primary="agent",
        scorer=mock_scorer,
        executor=failing_executor,
    )

    result = await adapter.evaluate(batch, candidate)

    # Should handle failure gracefully
    assert result.scores[0] == 0.0  # Failed examples get 0 score
```

### EC-2: Isolated Sessions for Conflicting Agents

```python
async def test_isolated_sessions_per_agent():
    """Each agent SHOULD get isolated sessions unless explicitly shared."""
    executor = AgentExecutor()

    adapter = MultiAgentAdapter(
        agents=[agent1, agent2],
        primary="agent1",
        scorer=mock_scorer,
        share_session=False,  # Isolated sessions
        executor=executor,
    )

    await adapter.evaluate(batch, candidate)

    # Verify agents used different session IDs
    # (Implementation detail - verified via executor tracking)
```

### EC-3: Timeout Handling Per Agent

```python
async def test_per_agent_timeout():
    """Each agent execution SHOULD respect its own timeout."""
    slow_executor = MockSlowExecutor(delay_seconds=10)

    adapter = MultiAgentAdapter(
        agents=[agent],
        primary="agent",
        scorer=mock_scorer,
        executor=slow_executor,
    )

    # Should timeout and handle gracefully
    result = await adapter.evaluate(batch, candidate)
    assert result.scores[0] == 0.0  # Timeout = failed
```
