# Contract: evolve() API Extension

**Function**: `evolve()` (in `gepa_adk.api`)
**New Parameter**: `model_choices: Sequence[str] | None = None`

## API Signature (Extended)

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
    component_selector: ComponentSelectorProtocol | str | None = None,
    executor: AgentExecutorProtocol | None = None,
    components: list[str] | None = None,
    schema_constraints: SchemaConstraints | None = None,
    model_choices: Sequence[str] | None = None,  # NEW
    app: App | None = None,
    runner: Runner | None = None,
) -> EvolutionResult:
```

## Contract Tests

### API-001: Model Evolution Opt-in

**Precondition**: Agent with model, `model_choices=["model-a", "model-b"]`
**Action**: `await evolve(agent, trainset, model_choices=["model-a", "model-b"])`
**Expected**:
- Model component included in evolution
- Result may contain evolved model in `evolved_components`

### API-002: Model Evolution Opt-out (Default)

**Precondition**: Agent with model, no `model_choices` parameter
**Action**: `await evolve(agent, trainset)`
**Expected**:
- Model NOT evolved
- `evolved_components` does not contain "model" key

### API-003: Empty Model Choices Treated as Opt-out

**Precondition**: Agent with model, `model_choices=[]`
**Action**: `await evolve(agent, trainset, model_choices=[])`
**Expected**:
- Model NOT evolved (empty list = opt-out)
- No error raised

### API-004: Single Model Choice Skipped

**Precondition**: Agent with model "model-a", `model_choices=["model-a"]`
**Action**: `await evolve(agent, trainset, model_choices=["model-a"])`
**Expected**:
- Model NOT evolved (no alternatives)
- No error raised

### API-005: Current Model Auto-included

**Precondition**: Agent with model "model-a", `model_choices=["model-b", "model-c"]`
**Action**: `await evolve(agent, trainset, model_choices=["model-b", "model-c"])`
**Expected**:
- "model-a" automatically added to allowed models
- Model evolution can select any of the three

### API-006: Model Evolution with Other Components

**Precondition**:
- Agent with model and instruction
- `components=["instruction", "model"]`
- `model_choices=["model-a", "model-b"]`
**Action**: `await evolve(agent, trainset, components=["instruction", "model"], model_choices=...)`
**Expected**:
- Both instruction and model evolved
- `evolved_components` may contain both keys

### API-007: Model Choices Without Model Component

**Precondition**:
- `components=["instruction"]` (model not in list)
- `model_choices=["model-a", "model-b"]`
**Action**: `await evolve(agent, trainset, components=["instruction"], model_choices=...)`
**Expected**:
- Warning logged (model_choices ignored when "model" not in components)
- Only instruction evolved

## Invariants

1. **Opt-in Required**: `model_choices=None` or `[]` means no model evolution
2. **Auto-include**: Current model always in effective allowed list
3. **Component Alignment**: `model_choices` only effective when "model" in components
4. **No Side Effects**: Original agent model unchanged after evolution completes
