# Data Model: Multi-Component Evolution with Component Selectors

**Feature**: 024-component-selector
**Date**: 2026-01-14

## Entity Definitions

### 1. ComponentSelectorProtocol (Port Interface)

**Location**: `src/gepa_adk/ports/selector.py`

| Attribute | Type | Description |
|-----------|------|-------------|
| (method) `select_components` | `async (components: list[str], iteration: int, candidate_idx: int) -> list[str]` | Selects component(s) to mutate |

**Relationships**:
- Used by `AsyncGEPAEngine` for component selection during mutation
- Implemented by `RoundRobinComponentSelector` and `AllComponentSelector`

**Validation Rules**:
- Input `components` must be non-empty list
- Input `iteration` must be non-negative integer
- Input `candidate_idx` must be non-negative integer
- Output must be non-empty subset of input `components`

---

### 2. RoundRobinComponentSelector (Adapter Implementation)

**Location**: `src/gepa_adk/adapters/component_selector.py`

| Attribute | Type | Description |
|-----------|------|-------------|
| `_next_index` | `dict[int, int]` | Per-candidate-idx tracking of next component index |

**State Transitions**:
```
Initial: _next_index = {}

On select_components(components, iteration, candidate_idx=0):
  If candidate_idx not in _next_index:
    _next_index[0] = 0

  selected_idx = _next_index[0]  # e.g., 0
  _next_index[0] = (selected_idx + 1) % len(components)  # e.g., 1
  Return components[selected_idx]
```

**Validation Rules**:
- Returns exactly one component per call
- Cycles through all components before repeating
- Independent cycle per candidate_idx

---

### 3. AllComponentSelector (Adapter Implementation)

**Location**: `src/gepa_adk/adapters/component_selector.py`

| Attribute | Type | Description |
|-----------|------|-------------|
| (none) | — | Stateless selector |

**Validation Rules**:
- Returns all components from input list
- Stateless - no tracking required

---

### 4. Candidate (Existing - Extended Usage)

**Location**: `src/gepa_adk/domain/models.py`

| Attribute | Type | Description |
|-----------|------|-------------|
| `components` | `dict[str, str]` | Component name to text value mapping |
| `generation` | `int` | Generation number in evolution lineage |
| `parent_id` | `str \| None` | Parent candidate ID for lineage tracking |
| `metadata` | `dict[str, Any]` | Extensible metadata dict |

**Extended Component Keys**:
- `instruction` - Primary/generic instruction (required by engine)
- `output_schema` - JSON schema definition for structured output
- `{agent_name}_instruction` - Per-agent instructions in multi-agent scenarios

**Validation Rules**:
- Must have at least `instruction` key (engine requirement)
- Component keys should be snake_case
- Per-agent keys follow pattern `{agent_name}_instruction`

---

### 5. EvolutionConfig (Existing - Potential Extension)

**Location**: `src/gepa_adk/domain/models.py`

**Potential New Attribute** (if config-based selection desired):

| Attribute | Type | Description |
|-----------|------|-------------|
| `component_selector` | `str` | Default: `"round_robin"`. Selector strategy name. |

**Note**: Research recommends parameter-based selection over config-based for flexibility.

---

## Data Flow Diagrams

### Component Selection Flow

```
┌─────────────────────┐
│  AsyncGEPAEngine    │
│  _propose_mutation  │
└──────────┬──────────┘
           │ 1. Get candidate components
           ▼
┌─────────────────────┐
│  Candidate          │
│  .components.keys() │
└──────────┬──────────┘
           │ 2. Pass to selector
           ▼
┌─────────────────────┐
│ ComponentSelector   │
│ .select_components()│
└──────────┬──────────┘
           │ 3. Return selected components
           ▼
┌─────────────────────┐
│  adapter            │
│ .make_reflective_   │
│  dataset()          │
│ .propose_new_texts()│
└─────────────────────┘
```

### Round-Robin State Tracking

```
Iteration 1 (candidate_idx=0, components=["a", "b", "c"]):
  _next_index = {}
  → _next_index[0] = 0
  → select components[0] = "a"
  → _next_index[0] = 1

Iteration 2 (candidate_idx=0):
  _next_index = {0: 1}
  → select components[1] = "b"
  → _next_index[0] = 2

Iteration 3 (candidate_idx=0):
  _next_index = {0: 2}
  → select components[2] = "c"
  → _next_index[0] = 0  # wraps

Iteration 4 (candidate_idx=1, different candidate):
  _next_index = {0: 0, 1: 0}  # new entry for candidate 1
  → select components[0] = "a"
  → _next_index[1] = 1
```

---

## Type Definitions

### New Types (in `domain/types.py` if needed)

```python
# Component name type alias
ComponentName = str  # Already exists

# Selector type literal for factory
ComponentSelectorType = Literal["round_robin", "all"]
```

---

## Relationship Matrix

| Entity | Depends On | Used By |
|--------|------------|---------|
| `ComponentSelectorProtocol` | `domain/types` | `AsyncGEPAEngine`, `api.py` |
| `RoundRobinComponentSelector` | `ComponentSelectorProtocol` | `create_component_selector`, `evolve()` |
| `AllComponentSelector` | `ComponentSelectorProtocol` | `create_component_selector`, `evolve()` |
| `Candidate` | — | `AsyncGEPAEngine`, `ComponentSelector` |
| `AsyncGEPAEngine` | `ComponentSelectorProtocol`, `Candidate` | `api.py` functions |

---

## Migration Notes

### Backward Compatibility

1. **Default Behavior**: Without explicit `component_selector` parameter, default to `RoundRobinComponentSelector`
2. **Single-Component Candidates**: For candidates with only `instruction`, both selectors return `["instruction"]` - identical to current behavior
3. **No Breaking Changes**: Existing API calls without `component_selector` continue to work
