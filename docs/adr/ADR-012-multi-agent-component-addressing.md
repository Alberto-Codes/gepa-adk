# ADR-012: Multi-Agent Component Addressing Scheme

> **Status**: Accepted
> **Date**: 2026-01-20
> **Deciders**: gepa-adk maintainers
> **Issue**: [#165](https://github.com/Alberto-Codes/gepa-adk/issues/165)

## Context

GEPA-ADK supports multi-agent evolution where different agents can have different components evolved simultaneously. We need a clear addressing scheme for specifying which components to evolve on which agents.

**Current single-agent pattern:**
```python
evolve(agent, trainset, components=["instruction", "output_schema"])
```

**Multi-agent requirement:**
```python
evolve_group(
    agents=[generator, refiner, critic],
    trainset=trainset,
    components=???  # How to specify generator.instruction + critic.output_schema?
)
```

### Problem: Underscore Separator Ambiguity

The current implementation uses underscore-separated names (`generator_instruction`), but this is ambiguous because component names themselves contain underscores:

```python
COMPONENT_OUTPUT_SCHEMA = "output_schema"           # has underscore
COMPONENT_GENERATE_CONFIG = "generate_content_config"  # has underscores
```

This creates parsing ambiguity:
- `generator_output_schema` → Is this `generator` + `output_schema` or `generator_output` + `schema`?

## Decision

Use **dot-separated qualified names** for multi-agent component addressing.

### Format

```
{agent_name}.{component_name}
```

**Examples:**
- `generator.instruction`
- `critic.output_schema`
- `refiner.generate_content_config`

### Why Dot Separator?

| Separator | Pros | Cons |
|-----------|------|------|
| **Dot (.)** | Unambiguous, matches ADK branch pattern, URI-like | Looks like attribute access |
| Underscore (_) | Python-friendly | Ambiguous with component names |
| Slash (/) | REST-like | Not Python identifier |
| Colon (:) | Namespace-like | Not Python identifier |

**ADK agent names are Python identifiers** (validated at agent creation), which cannot contain dots. Therefore, dots are always unambiguous separators.

### Type Safety

To maximize type safety with `ty`/`mypy`/`pyright`, we introduce:

1. **`QualifiedComponentName`**: A `NewType` that distinguishes qualified names from plain strings
2. **`ComponentSpec`**: A dataclass for structured construction and parsing

```python
from typing import NewType
from dataclasses import dataclass

QualifiedComponentName = NewType("QualifiedComponentName", str)

@dataclass(frozen=True, slots=True)
class ComponentSpec:
    """Structured representation of an agent.component pair."""
    agent: str
    component: str

    @property
    def qualified(self) -> QualifiedComponentName:
        """Return dot-separated qualified name."""
        return QualifiedComponentName(f"{self.agent}.{self.component}")

    @classmethod
    def parse(cls, qualified: QualifiedComponentName | str) -> "ComponentSpec":
        """Parse qualified name into ComponentSpec."""
        name = str(qualified)
        agent, component = name.split(".", 1)
        return cls(agent=agent, component=component)
```

### Usage

```python
# Construction
spec = ComponentSpec(agent="generator", component="instruction")
name: QualifiedComponentName = spec.qualified  # "generator.instruction"

# Parsing
spec = ComponentSpec.parse("critic.output_schema")
print(spec.agent)      # "critic"
print(spec.component)  # "output_schema"

# In candidates
candidate.components = {
    spec.qualified: "evolved instruction text...",
}
```

### Type Checker Benefits

| Error Type | Caught by ty? |
|------------|---------------|
| Field typo: `ComponentSpec(agnet="x")` | YES |
| Attribute typo: `spec.componet` | YES |
| Wrong type: `get_handler("plain string")` vs `QualifiedComponentName` | YES |
| Invalid format in parse | Runtime (ValueError) |

## Consequences

### Positive

1. **Unambiguous parsing**: No confusion with component names containing underscores
2. **ADK alignment**: Matches ADK's branch addressing pattern (`parent.child.grandchild`)
3. **Type safety**: `NewType` + dataclass enables IDE autocomplete and type checker validation
4. **Minimal change**: Same `dict[str, str]` structure, just different key format
5. **URI convention**: Follows established hierarchical naming patterns

### Negative

1. **Breaking change**: Existing multi-agent code using underscore separator needs migration
2. **Verbosity**: `QualifiedComponentName("...")` more verbose than plain string
3. **Learning curve**: New types to understand

### Neutral

1. **Single-agent unchanged**: Continues using unqualified names (`instruction`, `output_schema`)
2. **Dict keys remain strings**: Type is `NewType` of `str`, so JSON serialization unchanged

## Migration

### Internal Migration (api.py, multi_agent.py)

```python
# Before
component_name = f"{agent.name}_instruction"

# After
spec = ComponentSpec(agent=agent.name, component="instruction")
component_name = spec.qualified
```

### Backward Compatibility

- **Single-agent evolution**: No change required
- **Multi-agent evolution**: Internal refactor, API signature unchanged

## Alternatives Considered

### Option B: Nested Dict Structure

```python
components = {
    "generator": ["instruction", "output_schema"],
    "critic": ["generate_content_config"],
}
candidate = {
    "generator": {"instruction": "...", "output_schema": "..."},
    "critic": {"generate_content_config": "..."},
}
```

**Rejected because:**
- Breaking change to `Candidate.components` type (`dict[str, str]` → nested)
- More complex iteration patterns
- No clear benefit over flat structure

### Option C: ComponentSpec Without Qualified Names

```python
components = [
    ComponentSpec(agent="generator", component="instruction"),
    ComponentSpec(agent="critic", component="output_schema"),
]
```

**Partially adopted:**
- ComponentSpec used for construction/parsing
- Qualified string names used for dict keys (serialization compatibility)

## References

### Codebase
- `src/gepa_adk/api.py` - evolve_group implementation
- `src/gepa_adk/adapters/multi_agent.py` - MultiAgentAdapter
- `src/gepa_adk/domain/types.py` - Type definitions
- `src/gepa_adk/ports/component_handler.py` - ComponentHandler protocol

### ADK Patterns
- Agent naming validation: Python identifiers only (no dots)
- Branch addressing: `parent.child.grandchild` format
- State storage: Flat namespace keyed by agent name

### External
- [REST API Naming Conventions](https://restfulapi.net/resource-naming/)
- [Python NewType](https://docs.python.org/3/library/typing.html#newtype)
- [Google Multi-Agent Design Patterns](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
