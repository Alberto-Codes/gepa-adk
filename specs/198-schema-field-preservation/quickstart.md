# Quickstart: Schema Field Preservation

**Feature**: 198-schema-field-preservation

## Problem

When evolving `output_schema`, the reflection agent may propose schemas that remove critical fields like `score` or change their types. This breaks downstream consumers (scorers, integrations).

## Solution

Use `schema_constraints` to protect critical fields during evolution.

---

## Basic Usage

### Preserve Required Fields

```python
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from gepa_adk import evolve
from gepa_adk.domain.types import SchemaConstraints


class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str
    reasoning: str  # Can be evolved/removed


agent = LlmAgent(
    name="critic",
    model="gemini-2.0-flash",
    instruction="You are a code review critic...",
    output_schema=CriticOutput,
)

trainset = [{"input": "def foo(): pass", "expected": "Clean code"}]

# Protect score and feedback - they're required for the scorer
result = await evolve(
    agent,
    trainset,
    components=["output_schema"],
    schema_constraints=SchemaConstraints(
        required_fields=("score", "feedback"),
    ),
)

# The evolved schema will always have score and feedback fields
```

### Preserve Field Types

```python
from gepa_adk.domain.types import SchemaConstraints


class OrderOutput(BaseModel):
    order_id: str      # Must stay string (primary key)
    total: float       # Must stay numeric
    items: list[str]   # Can change


# Protect both existence and types
result = await evolve(
    agent,
    trainset,
    components=["output_schema"],
    schema_constraints=SchemaConstraints(
        required_fields=("order_id", "total"),
        preserve_types={
            "order_id": str,
            "total": (float, int),  # Allow int or float
        },
    ),
)
```

---

## What Happens When Constraints Are Violated

1. Reflection agent proposes a schema mutation
2. `OutputSchemaHandler` validates against constraints
3. **If valid**: Schema is applied normally
4. **If invalid**:
   - Original schema is preserved (no change)
   - Warning is logged with violation details
   - Evolution continues with next iteration

```python
# Example log output when mutation is rejected:
# WARNING  output_schema.constraint_violation
#          violations=["Required field 'score' not found in evolved schema"]
```

---

## Common Patterns

### Critic Agent (Score + Feedback)

```python
constraints = SchemaConstraints(
    required_fields=("score", "feedback"),
    preserve_types={"score": (float, int)},
)
```

### Domain Agent (Primary Keys)

```python
constraints = SchemaConstraints(
    required_fields=("id", "created_at"),
    preserve_types={"id": str, "created_at": str},
)
```

### Flexible Numeric (Allow int or float)

```python
constraints = SchemaConstraints(
    preserve_types={"value": (float, int)},
)
```

---

## Configuration Validation

Constraints are validated **before evolution starts**:

```python
# This will raise ConfigurationError immediately:
await evolve(
    agent,
    trainset,
    schema_constraints=SchemaConstraints(
        required_fields=("nonexistent_field",),  # Not in original schema!
    ),
)
# ConfigurationError: Field 'nonexistent_field' in required_fields
# not found in original schema
```

---

## Backward Compatibility

If you don't pass `schema_constraints`, evolution works exactly as before:

```python
# No constraints - all mutations allowed (current behavior)
result = await evolve(agent, trainset, components=["output_schema"])
```

---

## Next Steps

- See [Single-Agent Evolution Guide](/guides/single-agent) for full examples
- See [Critic Agents Guide](/guides/critic-agents) for scorer integration
