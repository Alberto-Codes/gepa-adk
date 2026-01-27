# Contract: AgentExecutor Multimodal Input

**Feature**: 235-multimodal-input
**Date**: 2026-01-27
**Type**: API Contract

## Overview

Extends AgentExecutor.execute_agent() to accept multimodal content (text + video parts) while maintaining backward compatibility with text-only inputs.

## Current Contract (Preserved)

```python
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
) -> ExecutionResult:
```

## Extended Contract

### New Parameter

```python
async def execute_agent(
    self,
    agent: Any,
    input_text: str,
    *,
    input_content: Content | None = None,  # NEW: Multimodal content
    instruction_override: str | None = None,
    output_schema_override: Any | None = None,
    session_state: dict[str, Any] | None = None,
    existing_session_id: str | None = None,
    timeout_seconds: int = 300,
) -> ExecutionResult:
```

### Behavior Contract

| input_text | input_content | Behavior |
|------------|---------------|----------|
| Non-empty | None | Use input_text (backward compatible) |
| Empty/None | Content | Use input_content (new) |
| Non-empty | Content | Use input_content (explicit takes precedence) |
| Empty/None | None | Use empty text part (edge case) |

### Content Assembly Logic

```python
def _build_content(
    self,
    input_text: str,
    input_content: Content | None = None,
) -> Content:
    """Build Content for agent execution."""
    if input_content is not None:
        return input_content

    # Backward compatible: wrap text in Content
    return Content(
        role="user",
        parts=[Part(text=input_text)]
    )
```

## Test Cases

### Contract Test: Text Only (Backward Compatible)

```python
@pytest.mark.asyncio
async def test_execute_agent_text_only(executor, mock_agent):
    """Text-only execution must work unchanged."""
    result = await executor.execute_agent(
        agent=mock_agent,
        input_text="Hello, world!",
    )

    assert result.status == ExecutionStatus.SUCCESS
    # Verify text was passed to agent
```

### Contract Test: Multimodal Content

```python
@pytest.mark.asyncio
async def test_execute_agent_multimodal(executor, mock_agent, video_part):
    """Multimodal content must be passed to agent."""
    content = Content(
        role="user",
        parts=[Part(text="describe this"), video_part]
    )

    result = await executor.execute_agent(
        agent=mock_agent,
        input_text="",  # Can be empty when content provided
        input_content=content,
    )

    assert result.status == ExecutionStatus.SUCCESS
    # Verify content was passed to agent
```

### Contract Test: Content Takes Precedence

```python
@pytest.mark.asyncio
async def test_execute_agent_content_precedence(executor, mock_agent, video_part):
    """input_content takes precedence over input_text."""
    content = Content(
        role="user",
        parts=[Part(text="from content"), video_part]
    )

    result = await executor.execute_agent(
        agent=mock_agent,
        input_text="from text param",  # Should be ignored
        input_content=content,
    )

    assert result.status == ExecutionStatus.SUCCESS
    # Verify "from content" was used, not "from text param"
```

### Contract Test: Empty Text Without Content

```python
@pytest.mark.asyncio
async def test_execute_agent_empty_text_no_content(executor, mock_agent):
    """Empty text without content should use empty text part."""
    result = await executor.execute_agent(
        agent=mock_agent,
        input_text="",
    )

    assert result.status == ExecutionStatus.SUCCESS
    # Agent receives empty text part
```

### Contract Test: All Overrides Work with Multimodal

```python
@pytest.mark.asyncio
async def test_execute_agent_overrides_with_multimodal(
    executor, mock_agent, video_part
):
    """Instruction and schema overrides must work with multimodal."""
    content = Content(
        role="user",
        parts=[Part(text="describe this"), video_part]
    )

    result = await executor.execute_agent(
        agent=mock_agent,
        input_text="",
        input_content=content,
        instruction_override="Custom instruction",
        session_state={"key": "value"},
    )

    assert result.status == ExecutionStatus.SUCCESS
    # Verify overrides were applied
```

### Contract Test: Result Structure Unchanged

```python
@pytest.mark.asyncio
async def test_execute_agent_result_structure(executor, mock_agent, video_part):
    """ExecutionResult structure must remain unchanged."""
    content = Content(
        role="user",
        parts=[Part(text="describe this"), video_part]
    )

    result = await executor.execute_agent(
        agent=mock_agent,
        input_text="",
        input_content=content,
    )

    # All existing fields must be present
    assert hasattr(result, "status")
    assert hasattr(result, "session_id")
    assert hasattr(result, "extracted_value")
    assert hasattr(result, "error_message")
    assert hasattr(result, "execution_time_seconds")
    assert hasattr(result, "captured_events")
```

## Implementation Notes

- `input_content` parameter is keyword-only to maintain signature compatibility
- Type hint uses `Content | None` (imports from google.genai.types in adapters only)
- Internally, all execution paths converge to Content-based runner call
- Logging should indicate whether multimodal content was used
