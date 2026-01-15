# API Contract Extensions: Component Selector

**Feature**: 024-component-selector
**Date**: 2026-01-14

## Public API Changes

### 1. `evolve()` Function Extension

**File**: `src/gepa_adk/api.py`

**Current Signature**:
```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
    candidate_selector: CandidateSelectorProtocol | str | None = None,
) -> EvolutionResult:
```

**Extended Signature**:
```python
async def evolve(
    agent: LlmAgent,
    trainset: list[dict[str, Any]],
    valset: list[dict[str, Any]] | None = None,
    critic: LlmAgent | None = None,
    reflection_agent: LlmAgent | None = None,
    config: EvolutionConfig | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    state_guard: StateGuard | None = None,
    candidate_selector: CandidateSelectorProtocol | str | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,  # NEW
) -> EvolutionResult:
```

**New Parameter**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `component_selector` | `ComponentSelectorProtocol \| str \| None` | `None` | Strategy for selecting which components to mutate each iteration. String values: `"round_robin"`, `"all"`. When `None`, defaults to round-robin. |

**Behavior**:
- `None` → Uses `RoundRobinComponentSelector()` (FR-003 default)
- `"round_robin"` → Uses `RoundRobinComponentSelector()`
- `"all"` → Uses `AllComponentSelector()`
- Protocol instance → Uses provided selector

---

### 2. `evolve_group()` Function Extension

**File**: `src/gepa_adk/api.py`

**Current Signature**:
```python
async def evolve_group(
    agents: list[LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
) -> MultiAgentEvolutionResult:
```

**Extended Signature**:
```python
async def evolve_group(
    agents: list[LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,  # NEW
) -> MultiAgentEvolutionResult:
```

---

### 3. `evolve_workflow()` Function Extension

**File**: `src/gepa_adk/api.py`

**Current Signature**:
```python
async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
) -> MultiAgentEvolutionResult:
```

**Extended Signature**:
```python
async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,  # NEW
) -> MultiAgentEvolutionResult:
```

---

## Factory Function

### `create_component_selector()`

**File**: `src/gepa_adk/adapters/component_selector.py`

**Signature**:
```python
def create_component_selector(
    selector_type: str,
) -> ComponentSelectorProtocol:
    """Create a component selector by name.

    Args:
        selector_type: Selector identifier. Valid values:
            - "round_robin": Cycles through components sequentially
            - "all": Selects all components each iteration

    Returns:
        ComponentSelectorProtocol implementation.

    Raises:
        ConfigurationError: If selector_type is unsupported.

    Examples:
        ```python
        selector = create_component_selector("round_robin")
        components = await selector.select_components(
            ["instruction", "output_schema"], 1, 0
        )
        ```
    """
```

**Supported Values**:
| Value | Aliases | Implementation |
|-------|---------|----------------|
| `"round_robin"` | `"round-robin"`, `"roundrobin"` | `RoundRobinComponentSelector` |
| `"all"` | — | `AllComponentSelector` |

---

## Selector Classes

### `RoundRobinComponentSelector`

**File**: `src/gepa_adk/adapters/component_selector.py`

```python
class RoundRobinComponentSelector:
    """Cycle through components sequentially, one per iteration.

    Maintains per-candidate-idx state to ensure independent cycling
    when used with Pareto-aware candidate selection.

    Attributes:
        _next_index: Dict mapping candidate_idx to next component index.

    Examples:
        ```python
        selector = RoundRobinComponentSelector()

        # Iteration 1: selects "instruction"
        result1 = await selector.select_components(
            ["instruction", "output_schema"], iteration=1, candidate_idx=0
        )
        assert result1 == ["instruction"]

        # Iteration 2: selects "output_schema"
        result2 = await selector.select_components(
            ["instruction", "output_schema"], iteration=2, candidate_idx=0
        )
        assert result2 == ["output_schema"]

        # Iteration 3: cycles back to "instruction"
        result3 = await selector.select_components(
            ["instruction", "output_schema"], iteration=3, candidate_idx=0
        )
        assert result3 == ["instruction"]
        ```
    """

    def __init__(self) -> None:
        """Initialize the selector with empty state."""

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        """Select the next component in round-robin order."""
```

### `AllComponentSelector`

**File**: `src/gepa_adk/adapters/component_selector.py`

```python
class AllComponentSelector:
    """Select all components for mutation each iteration.

    Stateless selector that returns all available components,
    enabling aggressive evolution of the entire candidate.

    Examples:
        ```python
        selector = AllComponentSelector()

        result = await selector.select_components(
            ["instruction", "output_schema"], iteration=1, candidate_idx=0
        )
        assert result == ["instruction", "output_schema"]
        ```
    """

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        """Return all components."""
```

---

## Usage Examples

### Basic Round-Robin Evolution

```python
from gepa_adk import evolve

result = await evolve(
    agent=my_agent,
    trainset=training_data,
    component_selector="round_robin",  # Or omit for default
)
```

### All-Components Evolution

```python
from gepa_adk import evolve

result = await evolve(
    agent=my_agent,
    trainset=training_data,
    component_selector="all",
)
```

### Multi-Agent with Component Selection

```python
from gepa_adk import evolve_group

result = await evolve_group(
    agents=[generator, critic, validator],
    primary="validator",
    trainset=training_data,
    component_selector="round_robin",  # Cycles through all agents' instructions
)
```

### Custom Selector Implementation

```python
from gepa_adk import evolve
from gepa_adk.ports.selector import ComponentSelectorProtocol

class PriorityComponentSelector:
    """Always evolve 'instruction' first, then others."""

    async def select_components(
        self,
        components: list[str],
        iteration: int,
        candidate_idx: int,
    ) -> list[str]:
        if "instruction" in components:
            return ["instruction"]
        return components[:1]

result = await evolve(
    agent=my_agent,
    trainset=training_data,
    component_selector=PriorityComponentSelector(),
)
```
