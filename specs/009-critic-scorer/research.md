# Research: CriticScorer Implementation

**Feature**: 009-critic-scorer  
**Date**: 2026-01-10  
**Status**: Complete

## Research Tasks

### 1. ADK Runner and Agent Execution Patterns

**Question**: How does the ADK Runner execute agents and retrieve structured output?

**Findings**:
- **Runner** is the main orchestrator for agent execution via `runner.run_async()`
- Runner returns events via async generator pattern
- Final response is identified via `event.is_final_response()` 
- Content accessed via `event.content.parts[0].text`

**Decision**: Use `Runner.run_async()` with event iteration to capture final agent output.

**Source**: https://google.github.io/adk-docs/runtime/

### 2. Structured Output with `output_schema`

**Question**: How do ADK agents enforce structured JSON output?

**Findings**:
- `LlmAgent` supports `output_schema` parameter (Pydantic BaseModel)
- When set, agent's final response MUST be JSON conforming to schema
- `output_key` can save output to session state automatically
- Schema enforces type safety at LLM generation level

**Decision**: Critic agents should use Pydantic `output_schema` with required `score` field.

**Example**:
```python
from pydantic import BaseModel, Field

class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="Score from 0.0 to 1.0")
    feedback: str = Field(default="", description="Feedback text")
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    actionable_guidance: str = Field(default="")
```

**Source**: https://google.github.io/adk-docs/agents/llm-agents/#structuring-data-input_schema-output_schema-output_key

### 3. Workflow Agents (SequentialAgent)

**Question**: How do workflow agents work and how to extract output from them?

**Findings**:
- `SequentialAgent` executes sub-agents in order
- Each sub-agent can pass state to the next via `output_key` → session state
- Final output comes from the last sub-agent in the sequence
- No LLM used for flow control (deterministic)

**Decision**: Support SequentialAgent as critic - final output extraction works identically to LlmAgent.

**Source**: https://google.github.io/adk-docs/agents/workflow-agents/

### 4. Session Management

**Question**: How to manage sessions for critic evaluation?

**Findings**:
- `InMemorySessionService` for local/testing (data lost on restart)
- `SessionService.create_session()` creates new isolated session
- Sessions can be shared via `session_id` parameter
- Session state accessible via `session.state` dict

**Decision**: 
- Default to `InMemorySessionService` for isolation
- Support optional `session_id` parameter for context sharing
- Create fresh session per scoring call by default

**Source**: https://google.github.io/adk-docs/sessions/

### 5. Async Execution Pattern

**Question**: What's the correct async pattern for running agents?

**Findings**:
- ADK is async-first: `run_async()` is primary method
- Returns `AsyncGenerator[Event]` - must iterate to completion
- Final response marked with `is_final_response()`
- Sync `run()` exists but wraps async internally

**Decision**: Implement `async_score()` as primary, `score()` uses `asyncio.run()` wrapper.

**Source**: https://google.github.io/adk-docs/runtime/#async-is-primary-run_async

### 6. Error Handling Patterns

**Question**: How should scoring errors be handled?

**Findings**:
- JSON parsing errors can occur if LLM doesn't follow schema
- Timeouts possible for long-running evaluations
- Missing required fields in output
- Agent execution failures

**Decision**: Create `ScoringError` exception hierarchy:
- `ScoringError` (base) - extends `EvolutionError`
- `CriticOutputParseError` - JSON/schema parsing failures
- `MissingScoreFieldError` - score field not present

**Rationale**: Follows ADR-009 exception hierarchy pattern.

## Alternatives Considered

### Alternative 1: Direct LLM Call Instead of Agent

**Rejected because**: Agents provide consistent execution patterns, tool support, and session management. Direct LLM calls would bypass ADK's orchestration benefits.

### Alternative 2: Batch Scoring Interface

**Rejected because**: Spec explicitly marks batch scoring as out of scope. Single-call interface aligns with existing `Scorer` protocol. Batch can be composed by callers.

### Alternative 3: Custom BaseAgent Instead of Using Runner

**Rejected because**: Runner provides proper event handling, session management, and state commitment. Custom implementation would duplicate this infrastructure.

## Implementation Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent Type Support | LlmAgent + SequentialAgent | Cover simple and workflow critics |
| Output Parsing | Pydantic + JSON parsing | Type-safe structured output |
| Session Management | InMemorySessionService default | Isolated evaluations |
| Error Strategy | Custom exception hierarchy | ADR-009 compliance |
| Async Pattern | async_score() primary | ADR-001 compliance |
| Protocol Compliance | Implement Scorer | Spec dependency #5 |

## Open Questions (Resolved)

1. ✅ **How to handle workflow agent output?** → Final output from last sub-agent via Runner events
2. ✅ **Score normalization?** → Convention 0.0-1.0, not enforced by protocol (per #5 spec)
3. ✅ **Session lifetime?** → Create per-call unless shared session_id provided
