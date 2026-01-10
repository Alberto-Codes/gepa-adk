# Research: Scorer Protocol

**Feature**: 005-scorer-protocol
**Date**: 2026-01-10

## Research Questions

### 1. How does GEPA handle scoring internally?

**Decision**: Follow GEPA's `Evaluator` pattern but adapt for our async-first architecture.

**Rationale**: GEPA's default adapter uses an `Evaluator` protocol that returns `EvaluationResult(score, feedback, objective_scores)`. Our Scorer protocol aligns with this but simplifies to `(float, dict)` to stay focused on the core scoring contract.

**Key Findings from GEPA**:
- GEPA's `GEPAAdapter.evaluate()` returns `EvaluationBatch` with `scores: list[float]`
- The `DefaultAdapter` uses an `Evaluator` protocol: `(data, response) -> EvaluationResult`
- `EvaluationResult` is a NamedTuple with `score: float`, `feedback: str`, `objective_scores: dict | None`
- Scores are per-example floats where higher is better
- GEPA uses sum(scores) for minibatch acceptance, mean(scores) for tracking

**Source**: `.venv/lib/python3.12/site-packages/gepa/adapters/default_adapter/default_adapter.py:54-60`

### 2. What scoring patterns exist in the proposal?

**Decision**: Support both simple scorers and critic-based scorers through the same protocol.

**Rationale**: The proposal defines two scoring approaches:
1. **Mechanical scorers** - Simple logic like exact match (`score = 1.0 if output == expected else 0.0`)
2. **Critic scorers** - ADK agents with `output_schema` returning structured `{score, feedback}`

Both can implement the same `Scorer` protocol; the difference is in the implementation.

**Key Findings from Proposal**:
- Critic agents are the "key innovation" differentiating gepa-adk from GEPA default
- Critics return structured JSON: `{score: float, feedback: str, dimension_scores?: dict, actionable_guidance?: str}`
- The feedback flows into the reflective dataset for targeted improvements
- Use Case 3 in proposal shows custom scorer: `class MyScorer(Scorer): def score(self, input, output, expected) -> tuple[float, dict]`

**Source**: `docs/proposals/001-initial-package-proposal.md:302-347, 582-593`

### 3. Should scoring be async-only or support both sync and async?

**Decision**: Define both `score()` (sync) and `async_score()` (async) in the protocol, following the spec requirements.

**Rationale**:
- Constitution mandates async-first design (ADR-001)
- However, many simple scorers (exact match, keyword detection) don't need async
- Having both methods provides flexibility while maintaining async-first principles
- The evolution engine can choose which method to call based on context

**Alternatives Considered**:
1. **Async-only**: Would force simple scorers to wrap sync code in `async def`
2. **Sync-only with wrapper**: Would require `run_async()` bridges, explicitly rejected in proposal
3. **Both methods (chosen)**: Maximum flexibility, aligns with spec FR-001/FR-002

### 4. What return type should the scorer use?

**Decision**: Return `tuple[float, dict]` where float is the score and dict contains metadata.

**Rationale**:
- GEPA's `EvaluationResult` uses a NamedTuple but we want simpler contracts
- The proposal's use case shows `-> tuple[float, dict]`
- Metadata dict allows extensibility (feedback, dimension_scores, etc.)
- Aligns with existing `EvaluationBatch` pattern which separates scores from outputs

**Key Considerations**:
- Float should be normalized 0.0-1.0 by convention (not enforced)
- Dict can contain arbitrary metadata: feedback, component-level scores, debug info
- Using a simple tuple avoids adding domain models for protocol returns

### 5. Should we create a ScoreResult dataclass or use plain tuple?

**Decision**: Use plain `tuple[float, dict]` for the protocol, not a dataclass.

**Rationale**:
- Protocols should have minimal dependencies
- A dataclass would add coupling between ports and domain
- Tuple is sufficient and matches GEPA's lightweight approach
- Users can wrap in their own types if needed

**Alternatives Considered**:
1. **Dataclass ScoreResult**: More structured but adds import dependency
2. **NamedTuple**: Better than plain tuple but still adds a type
3. **Plain tuple (chosen)**: Simplest, no additional types needed

### 6. How should the protocol interact with existing AsyncGEPAAdapter?

**Decision**: Scorer is a separate protocol that can be used within adapters or independently.

**Rationale**:
- `AsyncGEPAAdapter.evaluate()` already returns `EvaluationBatch` with scores
- Scorer protocol is for custom scoring logic that feeds into the adapter
- The adapter may internally use a Scorer, but this is an implementation detail
- Keeping them separate follows single responsibility principle

**Integration Pattern**:
```python
# Adapter uses Scorer internally
class ADKAdapter(AsyncGEPAAdapter):
    def __init__(self, scorer: Scorer): ...

    async def evaluate(self, batch, candidate, capture_traces):
        results = []
        for example in batch:
            output = await self._execute(example, candidate)
            score, metadata = await self.scorer.async_score(
                example["input"], output, example.get("expected")
            )
            results.append((output, score, metadata))
        return EvaluationBatch(...)
```

### 7. Should @runtime_checkable be applied?

**Decision**: Yes, apply `@runtime_checkable` to enable isinstance() checks.

**Rationale**:
- Spec FR-006 explicitly requires runtime-checkable support
- Constitution ADR-002 allows `@runtime_checkable` when isinstance() checks are needed
- Useful for validation and debugging: `assert isinstance(scorer, Scorer)`

## Technical Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Method signatures | `score()` + `async_score()` | Spec requires both; flexibility |
| Return type | `tuple[float, dict]` | Simple, extensible, matches GEPA |
| Runtime checkable | Yes | Spec FR-006 requires it |
| Score range | 0.0-1.0 convention | GEPA pattern, not enforced |
| Expected parameter | Optional (None default) | Support open-ended scoring |
| Protocol location | `ports/scorer.py` | Follows hexagonal architecture |

## Implementation Guidance

### File Structure
```
src/gepa_adk/
└── ports/
    ├── __init__.py       # Export Scorer
    └── scorer.py         # Scorer protocol definition
```

### Protocol Definition Pattern
Follow the existing `AsyncGEPAAdapter` pattern in `ports/adapter.py`:
- Use `typing.Protocol` with `@runtime_checkable`
- Include comprehensive docstrings (Google style per ADR-010)
- Type hints for all parameters and return values
- No external imports (stdlib only per constitution)

### Test Strategy
Per constitution ADR-005, three-layer testing:
1. **Contract tests**: Verify protocol is correctly defined, check isinstance() works
2. **Unit tests**: Mock implementations satisfy protocol
3. **Integration tests**: Real scorer implementations (future)

## References

- GEPA core adapter: `.venv/lib/python3.12/site-packages/gepa/core/adapter.py`
- GEPA default evaluator: `.venv/lib/python3.12/site-packages/gepa/adapters/default_adapter/default_adapter.py`
- Proposal scoring section: `docs/proposals/001-initial-package-proposal.md:302-347`
- Existing AsyncGEPAAdapter: `src/gepa_adk/ports/adapter.py`
- Constitution: `.specify/memory/constitution.md`
