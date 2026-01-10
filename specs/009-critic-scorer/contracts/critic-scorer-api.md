# CriticScorer API Contract

**Feature**: 009-critic-scorer  
**Date**: 2026-01-10  
**Protocol**: Implements `gepa_adk.ports.scorer.Scorer`

## Class: CriticScorer

### Constructor

```python
def __init__(
    self,
    critic_agent: BaseAgent,
    session_service: BaseSessionService | None = None,
    app_name: str = "critic_scorer",
) -> None:
```

**Parameters**:
- `critic_agent`: ADK agent configured for evaluation (LlmAgent, SequentialAgent, etc.)
- `session_service`: Optional session service (default: InMemorySessionService)
- `app_name`: Application name for session identification

**Raises**:
- `TypeError`: If `critic_agent` is not a BaseAgent instance
- `ValueError`: If `app_name` is empty string

> **Note**: When using LlmAgent with `output_schema`, the agent cannot use tools (ADK constraint). For evaluations requiring tool usage, use a SequentialAgent with tool-enabled agents before the output-constrained scorer.

---

### Method: score

```python
def score(
    self,
    input_text: str,
    output: str,
    expected: str | None = None,
) -> tuple[float, dict[str, Any]]:
```

**Description**: Synchronously score an agent output using the critic agent.

**Parameters**:
- `input_text`: The original input provided to the agent being evaluated
- `output`: The agent's generated output to score
- `expected`: Optional expected/reference output for comparison

**Returns**: `tuple[float, dict[str, Any]]`
- `[0]`: Score value (float, conventionally 0.0-1.0)
- `[1]`: Metadata dictionary containing:
  - `feedback` (str): Feedback text if present
  - `dimension_scores` (dict): Per-dimension scores if present
  - `actionable_guidance` (str): Guidance text if present

**Raises**:
- `CriticOutputParseError`: If critic output is not valid JSON
- `MissingScoreFieldError`: If `score` field missing from output

**Example**:
```python
scorer = CriticScorer(critic_agent=my_critic)
score, metadata = scorer.score(
    input_text="What is 2+2?",
    output="4",
    expected="4"
)
print(f"Score: {score}, Feedback: {metadata.get('feedback')}")
```

---

### Method: async_score

```python
async def async_score(
    self,
    input_text: str,
    output: str,
    expected: str | None = None,
    session_id: str | None = None,
) -> tuple[float, dict[str, Any]]:
```

**Description**: Asynchronously score an agent output using the critic agent.

**Parameters**:
- `input_text`: The original input provided to the agent being evaluated
- `output`: The agent's generated output to score
- `expected`: Optional expected/reference output for comparison
- `session_id`: Optional session ID to share state with main agent workflow

**Returns**: `tuple[float, dict[str, Any]]`
- Same structure as `score()` method

**Raises**:
- `CriticOutputParseError`: If critic output is not valid JSON
- `MissingScoreFieldError`: If `score` field missing from output

**Example**:
```python
scorer = CriticScorer(critic_agent=my_critic)
score, metadata = await scorer.async_score(
    input_text="Explain gravity",
    output="Gravity is the force that attracts objects...",
    expected=None  # Open-ended evaluation
)
```

---

## Pydantic Schema: CriticOutput

```python
from pydantic import BaseModel, Field

class CriticOutput(BaseModel):
    """Expected structured output format from critic agents.
    
    Attributes:
        score: Score value between 0.0 and 1.0.
        feedback: Human-readable feedback text.
        dimension_scores: Per-dimension evaluation scores.
        actionable_guidance: Specific improvement suggestions.
    """
    
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score from 0.0 to 1.0"
    )
    feedback: str = Field(
        default="",
        description="Human-readable feedback"
    )
    dimension_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension scores"
    )
    actionable_guidance: str = Field(
        default="",
        description="Improvement suggestions"
    )
```

---

## Exception Classes

### ScoringError

```python
class ScoringError(EvolutionError):
    """Base exception for scoring-related errors."""
    pass
```

### CriticOutputParseError

```python
class CriticOutputParseError(ScoringError):
    """Raised when critic output cannot be parsed as JSON.
    
    Attributes:
        raw_output: The unparseable output string.
        parse_error: Description of the parsing failure.
    """
    
    def __init__(
        self,
        raw_output: str,
        parse_error: str,
        cause: Exception | None = None,
    ) -> None:
        ...
```

### MissingScoreFieldError

```python
class MissingScoreFieldError(ScoringError):
    """Raised when parsed output lacks required score field.
    
    Attributes:
        parsed_output: The parsed dict without score.
        available_fields: List of fields present in output.
    """
    
    def __init__(
        self,
        parsed_output: dict[str, Any],
        cause: Exception | None = None,
    ) -> None:
        ...
```

---

## Protocol Compliance

CriticScorer MUST satisfy the `Scorer` protocol:

```python
from gepa_adk.ports.scorer import Scorer

scorer = CriticScorer(critic_agent=my_agent)
assert isinstance(scorer, Scorer)  # Must pass at runtime
```

### Required Method Signatures

| Method | Parameters | Return Type |
|--------|------------|-------------|
| `score` | `(input_text: str, output: str, expected: str \| None)` | `tuple[float, dict[str, Any]]` |
| `async_score` | `(input_text: str, output: str, expected: str \| None)` | `tuple[float, dict[str, Any]]` |

---

## Usage Examples

### Basic Scoring

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from gepa_adk.adapters.critic_scorer import CriticScorer

class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str = ""

critic = LlmAgent(
    name="quality_critic",
    model="gemini-2.0-flash",
    instruction="Evaluate the response quality...",
    output_schema=CriticOutput,
)

scorer = CriticScorer(critic_agent=critic)
score, metadata = await scorer.async_score(
    input_text="What is Python?",
    output="Python is a programming language.",
    expected="Python is a high-level programming language.",
)
```

### Workflow Critic (SequentialAgent)

```python
from google.adk.agents import LlmAgent, SequentialAgent

validator = LlmAgent(name="validator", ...)
evaluator = LlmAgent(name="evaluator", output_schema=CriticOutput, ...)

workflow_critic = SequentialAgent(
    name="validation_workflow",
    sub_agents=[validator, evaluator],
)

scorer = CriticScorer(critic_agent=workflow_critic)
score, metadata = await scorer.async_score(...)
```

### With Session Sharing

```python
# Share session with main agent for context access
scorer = CriticScorer(
    critic_agent=critic,
    session_service=shared_session_service,
)
score, metadata = await scorer.async_score(
    input_text="...",
    output="...",
    session_id="existing_session_123",
)
```
