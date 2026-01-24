# Research: ADK-First Reflection Agent Support

**Feature**: 010-adk-reflection-agent
**Date**: 2026-01-10
**Status**: Complete

## Research Questions

### RQ-1: How to pass context (instruction + feedback) to ADK reflection agent?

**Decision**: Use session state initialization via `create_session(state={...})` to pass context to the reflection agent.

**Rationale**:
- ADK's `SessionService.create_session()` accepts a `state` parameter for initial state
- The reflection agent's instruction can use `{key}` template syntax to inject state values
- This is the documented ADK pattern for passing context to agents

**Implementation Pattern**:
```python
session = await session_service.create_session(
    app_name="reflection",
    user_id="reflection",
    session_id=f"reflect_{uuid4()}",
    state={
        "current_instruction": current_instruction,
        "execution_feedback": json.dumps(feedback),
    }
)
```

**Alternatives Considered**:
1. ~~Passing context in `new_message` content~~ - Rejected because it mixes context with the trigger prompt
2. ~~Using `temp:` prefix state~~ - Acceptable but unnecessary since we create fresh sessions each time

**Sources**:
- [State - Agent Development Kit](https://google.github.io/adk-docs/sessions/state/)
- [Overview - Agent Development Kit Sessions](https://google.github.io/adk-docs/sessions/session/)

---

### RQ-2: How to configure the reflection agent's instruction to use injected state?

**Decision**: Use ADK's built-in `{key}` template syntax in the `LlmAgent.instruction` parameter.

**Rationale**:
- ADK automatically replaces `{key}` placeholders with `session.state[key]` values before sending to LLM
- This is a native ADK feature that requires no additional code
- The reflection agent can be configured once with a template and reused

**Implementation Pattern**:
```python
reflection_agent = LlmAgent(
    name="ReflectionAgent",
    model="gemini-2.5-flash",
    instruction="""You are an expert at improving AI agent instructions based on feedback.

Current Instruction:
{current_instruction}

Execution Feedback:
{execution_feedback}

Based on this feedback, propose an improved instruction that addresses identified issues.
Return ONLY the improved instruction text."""
)
```

**Alternatives Considered**:
1. ~~Using `InstructionProvider` function~~ - Adds complexity, only needed if escaping `{{` is required
2. ~~Passing instruction in user message~~ - Loses the "system prompt" behavior of instructions

**Sources**:
- [State - Agent Development Kit](https://google.github.io/adk-docs/sessions/state/)
- [LLM agents - Agent Development Kit](https://google.github.io/adk-docs/agents/llm-agents/)

---

### RQ-3: Best practices for Runner lifecycle and session isolation?

**Decision**: Create a new Runner instance per reflection call with a unique session ID.

**Rationale**:
- Runners are stateless and safe to create per-operation
- Each reflection is independent and should not share conversation history
- Using unique session IDs (e.g., `reflect_{uuid}`) ensures complete isolation
- `InMemorySessionService` handles cleanup automatically (no explicit cleanup needed)

**Implementation Pattern**:
```python
async def reflect(current_instruction: str, feedback: list[dict]) -> str:
    session_id = f"reflect_{uuid4()}"

    # Create session with initial state
    session = await session_service.create_session(
        app_name="gepa_reflection",
        user_id="reflection",
        session_id=session_id,
        state={"current_instruction": current_instruction, ...}
    )

    runner = Runner(
        agent=reflection_agent,
        app_name="gepa_reflection",
        session_service=session_service,
    )

    # Execute and extract result
    async for event in runner.run_async(
        user_id="reflection",
        session_id=session_id,
        new_message=Content(role="user", parts=[Part(text="Propose improved instruction")])
    ):
        if event.is_final_response():
            return extract_text(event)
```

**Alternatives Considered**:
1. ~~Reusing Runner instance~~ - Acceptable but creates shared state risk; fresh instances are cleaner
2. ~~Using `InMemoryRunner`~~ - Doesn't support session persistence, not suitable

**Sources**:
- [Agent Runtime - Agent Development Kit](https://google.github.io/adk-docs/runtime/)
- [FastAPI + Google ADK Discussion](https://github.com/google/adk-python/discussions/3924)
- [Google ADK Masterclass Part 5](https://saptak.in/writing/2025/05/10/google-adk-masterclass-part5)

---

### RQ-4: How to extract final response text from Runner.run_async() events?

**Decision**: Iterate through events, check `event.is_final_response()`, extract text from `event.actions.response_content`.

**Rationale**:
- This is the standard ADK pattern already used in `ADKAdapter._run_single_example()`
- `is_final_response()` reliably identifies the terminal event
- Text is in `event.actions.response_content[0].text` for final responses

**Implementation Pattern**:
```python
async for event in runner.run_async(...):
    if event.is_final_response():
        if event.actions and event.actions.response_content:
            for part in event.actions.response_content:
                if hasattr(part, "text") and part.text:
                    return part.text.strip()
return ""  # Fallback for empty response
```

**Sources**:
- [Events - Agent Development Kit](https://google.github.io/adk-docs/events/)
- Existing implementation: `src/gepa_adk/adapters/adk_adapter.py:576-591`

---

### RQ-5: Error handling and empty response fallback strategy?

**Decision**: Follow existing proposer pattern - return original candidate text on empty/None response; propagate exceptions to caller.

**Rationale**:
- Maintains consistency with existing `AsyncReflectiveMutationProposer` behavior
- LiteLLM fallback path already handles empty responses this way
- Propagating exceptions allows caller (engine) to handle retries/logging

**Implementation Pattern**:
```python
try:
    new_text = await adk_reflection_fn(current_instruction, feedback)
    if new_text is None or not new_text.strip():
        proposals[component] = current_text  # Fallback
    else:
        proposals[component] = new_text.strip()
except Exception:
    raise  # Let engine handle
```

**Sources**:
- Existing implementation: `src/gepa_adk/engine/proposer.py:218-226`

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Context passing | Session state via `create_session(state={...})` |
| Instruction templating | ADK native `{key}` syntax in `LlmAgent.instruction` |
| Runner lifecycle | Fresh Runner + unique session ID per reflection |
| Response extraction | `event.is_final_response()` + `response_content` pattern |
| Error handling | Empty → fallback to original; exceptions propagate |

## Implementation Notes

1. **Factory function signature**: `create_adk_reflection_fn(agent: LlmAgent, session_service: BaseSessionService | None = None) -> Callable`

2. **Returned callable signature**: `async def reflect(current_instruction: str, feedback: list[dict]) -> str`

3. **Session state keys**: `current_instruction` (str), `execution_feedback` (JSON string)

4. **Input text to agent**: Simple trigger prompt like "Propose an improved instruction based on the feedback."

5. **No additional dependencies**: All required imports (`Runner`, `InMemorySessionService`, `Content`, `Part`) are already available from `google.adk` and `google.genai.types`
