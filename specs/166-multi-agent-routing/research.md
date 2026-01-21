# Research: Multi-Agent Component Routing

**Feature**: 166-multi-agent-routing
**Date**: 2026-01-20

## Research Tasks

### 1. Component Addressing Format

**Question**: What format should be used for qualified component names?

**Decision**: Use dot-separated format per ADR-012 (`generator.instruction`)

**Rationale**:
- ADR-012 (Multi-Agent Component Addressing) is already finalized in issue #165
- Dot separator chosen because:
  - Agent names are Python identifiers (no dots allowed)
  - Matches ADK branch addressing pattern
  - Avoids collision with underscore-containing component names
- Type safety via `QualifiedComponentName = NewType("QualifiedComponentName", str)`
- Structured parsing via `ComponentSpec.parse(qualified_name)`

**Alternatives Considered**:
- Underscore separator (`generator_instruction`) - REJECTED: collides with `generate_content_config`
- Slash separator (`generator/instruction`) - REJECTED: not URI-safe without encoding
- Tuple key (`("generator", "instruction")`) - REJECTED: dict serialization complexity

### 2. Existing Type Definitions

**Question**: Are the required types already implemented?

**Decision**: Yes, types exist in `src/gepa_adk/domain/types.py`

**Findings**:
```python
# Line 74
QualifiedComponentName = NewType("QualifiedComponentName", str)

# Lines 180-287
@dataclass(frozen=True, slots=True)
class ComponentSpec:
    agent: str
    component: str

    @property
    def qualified(self) -> QualifiedComponentName:
        return QualifiedComponentName(f"{self.agent}.{self.component}")

    @classmethod
    def parse(cls, qualified: str) -> ComponentSpec:
        parts = qualified.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid qualified name: {qualified}")
        return cls(agent=parts[0], component=parts[1])
```

**No changes needed** to domain types.

### 3. Component Handler System

**Question**: How should handlers be retrieved for routing?

**Decision**: Use existing `get_handler(component_name)` function

**Rationale**:
- `ComponentHandlerRegistry` already exists in `src/gepa_adk/adapters/component_handlers.py`
- Three handlers registered: `instruction`, `output_schema`, `generate_content_config`
- Handler interface provides: `apply(agent, value) -> original`, `restore(agent, original)`
- O(1) lookup via `component_handlers.get(name)`

**Implementation Pattern**:
```python
from gepa_adk.domain.types import ComponentSpec
from gepa_adk.adapters.component_handlers import get_handler

def _apply_candidate(self, candidate: dict[str, str]) -> dict[str, Any]:
    originals = {}
    for qualified_name, value in candidate.items():
        spec = ComponentSpec.parse(qualified_name)
        agent = self.agents[spec.agent]
        handler = get_handler(spec.component)
        originals[qualified_name] = handler.apply(agent, value)
    return originals
```

### 4. API Design (No Backward Compatibility)

**Question**: What should the new API signature look like?

**Decision**: Clean break with explicit required parameters

**Rationale**:
- Project is at 0.2.x - active development, breaking changes acceptable
- Simpler implementation without legacy support code
- Cleaner API surface for users
- Fail-fast validation prevents runtime surprises

**New API**:
```python
async def evolve_group(
    agents: dict[str, LlmAgent],        # REQUIRED: named agents
    primary: str,                        # Primary agent name
    trainset: list[dict[str, Any]],
    components: dict[str, list[str]],   # REQUIRED: per-agent components
    ...
) -> MultiAgentEvolutionResult
```

**Example Usage**:
```python
result = await evolve_group(
    agents={"generator": gen, "refiner": ref, "critic": critic},
    primary="generator",
    trainset=trainset,
    components={
        "generator": ["instruction", "output_schema"],
        "refiner": ["instruction"],
        "critic": ["generate_content_config"],
    },
)
```

**Migration for Existing Users**:
```python
# Old (0.2.x)
evolve_group(agents=[gen, critic], primary="generator", ...)

# New (0.3.x)
evolve_group(
    agents={"generator": gen, "critic": critic},
    primary="generator",
    components={"generator": ["instruction"], "critic": ["instruction"]},
    ...
)
```

### 5. Restoration Error Handling

**Question**: How to handle partial restore failures?

**Decision**: Best-effort restoration with error aggregation

**Rationale**:
- If one handler.restore() fails, continue restoring other agents
- Collect all errors and raise aggregated exception after all attempts
- Prevents cascading state corruption
- Follows Python try/finally pattern

**Implementation Pattern**:
```python
def _restore_agents(self, originals: dict[str, Any]) -> None:
    errors = []
    for qualified_name, original in originals.items():
        try:
            spec = ComponentSpec.parse(qualified_name)
            agent = self.agents[spec.agent]
            handler = get_handler(spec.component)
            handler.restore(agent, original)
        except Exception as e:
            errors.append((qualified_name, e))
    if errors:
        raise RestoreError(f"Failed to restore {len(errors)} components", errors=errors)
```

### 6. Validation Requirements

**Question**: What validation is needed before evolution runs?

**Decision**: Validate at initialization time (fail-fast)

**Validations**:
1. All agent names in `components` mapping exist in `agents` dict
2. All component names have registered handlers
3. No duplicate qualified names in candidate keys
4. Agent names are valid Python identifiers (for dot parsing)

**Error Messages**:
```python
# Agent not found
f"Agent '{spec.agent}' not found in agents dict. Available: {list(self.agents.keys())}"

# Component not found
f"No handler registered for component '{spec.component}'. Available: {list(component_handlers.names())}"
```

### 7. Current Implementation Gap Analysis

**Question**: What changes are needed in MultiAgentAdapter?

**Findings**:

| Current | Target | Gap |
|---------|--------|-----|
| Seed candidate uses `{agent.name}_instruction` | Qualified names `generator.instruction` | Modify `_build_seed_candidate` |
| `_build_pipeline` reads `{agent.name}_instruction` | Read via ComponentSpec parsing | Modify component access |
| No `_apply_candidate` in MultiAgentAdapter | Add routing method | New method |
| No `_restore_agents` in MultiAgentAdapter | Add restoration method | New method |
| `agents` is `list[LlmAgent]` | Change to `dict[str, LlmAgent]` | Modify `__init__` (breaking change) |
| No `components` parameter | Add required per-agent component config | New required parameter |

**Key Methods to Modify**:
- `__init__`: Accept dict agents, components parameter
- `_build_seed_candidate`: Generate qualified names
- `_build_pipeline`: Use ComponentSpec for component access
- Add `_apply_candidate`: Route updates to correct agents
- Add `_restore_agents`: Restore all agents

### 8. Test Strategy

**Question**: What tests are needed for three-layer coverage?

**Decision**: Tests across contract, unit, and integration layers

| Layer | Test | Purpose |
|-------|------|---------|
| Contract | `test_component_handler_apply_restore` | Handler protocol compliance |
| Unit | `test_apply_candidate_routes_to_correct_agent` | Routing logic |
| Unit | `test_restore_agents_restores_all` | Restoration logic |
| Unit | `test_validation_unknown_agent_raises` | Error handling |
| Unit | `test_validation_unknown_component_raises` | Error handling |
| Unit | `test_validation_missing_agent_in_components` | Fail-fast validation |
| Integration | `test_multi_agent_evolution_with_per_agent_components` | End-to-end |

## Summary

All research tasks complete. No NEEDS CLARIFICATION markers remain.

**Key Decisions**:
1. Use ADR-012 dot-separated qualified names (`generator.instruction`)
2. Leverage existing ComponentSpec/QualifiedComponentName types
3. Use existing ComponentHandlerRegistry for handler lookup
4. No backward compatibility - clean API break at 0.3.x (agents as dict, components required)
5. Best-effort restoration with error aggregation
6. Fail-fast validation at initialization (all agents must have components mapping)

**Dependencies Confirmed**:
- Issue #165 (ADR-012): Complete - types available
- Issue #164 (generate_content_config): Assumed complete - handler registered
