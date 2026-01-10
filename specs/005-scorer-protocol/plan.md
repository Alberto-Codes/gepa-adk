# Implementation Plan: Scorer Protocol

**Branch**: `005-scorer-protocol` | **Date**: 2026-01-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-scorer-protocol/spec.md`

## Summary

Define a `Scorer` protocol that enables custom scoring logic for evaluating agent outputs in the evolution engine. The protocol provides both synchronous (`score()`) and asynchronous (`async_score()`) methods, returning `tuple[float, dict]` with score and metadata. This follows GEPA's `Evaluator` pattern while adapting for gepa-adk's async-first architecture per ADR-001.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: None (stdlib only for ports layer per ADR-000)
**Storage**: N/A (protocol definition only)
**Testing**: pytest with pytest-asyncio
**Target Platform**: Linux/macOS/Windows (cross-platform Python package)
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: N/A (protocol has no runtime overhead)
**Constraints**: No external imports in ports layer (constitution requirement)
**Scale/Scope**: Single protocol file (~100 lines)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | Protocol in `ports/` layer, no external imports |
| **II. Async-First Design** | ✅ PASS | `async_score()` method required by protocol |
| **III. Protocol-Based Interfaces** | ✅ PASS | Using `typing.Protocol` with `@runtime_checkable` |
| **IV. Three-Layer Testing** | ✅ PASS | Contract tests planned for protocol compliance |
| **V. Observability & Documentation** | ✅ PASS | Google-style docstrings, examples in docstrings |

**ADR Alignment**:
- ADR-000: Scorer in ports/ with no adapters/ or external imports
- ADR-001: Both sync and async methods defined
- ADR-002: Protocol-based, @runtime_checkable, no ABC inheritance

## Project Structure

### Documentation (this feature)

```text
specs/005-scorer-protocol/
├── plan.md              # This file
├── research.md          # GEPA patterns, design decisions
├── data-model.md        # Entity definitions
├── quickstart.md        # Usage examples
├── contracts/           # Protocol contract specification
│   └── scorer-protocol.md
└── tasks.md             # Implementation tasks (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── ports/
│   ├── __init__.py      # Add Scorer export
│   ├── adapter.py       # Existing AsyncGEPAAdapter
│   └── scorer.py        # NEW: Scorer protocol
└── domain/
    └── types.py         # Existing Score type alias

tests/
└── contracts/
    └── test_scorer_protocol.py  # NEW: Contract tests
```

**Structure Decision**: Follows existing hexagonal architecture. Scorer protocol added to `ports/` layer alongside `AsyncGEPAAdapter`. Contract tests in `tests/contracts/` per ADR-005.

## Design Decisions

### From Research (research.md)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Method signatures | `score()` + `async_score()` | Spec requires both; flexibility for sync/async callers |
| Return type | `tuple[float, dict]` | Simple, extensible, matches GEPA pattern |
| Runtime checkable | Yes | Spec FR-006 requires isinstance() support |
| Score range | 0.0-1.0 convention | GEPA pattern, documented but not enforced |
| Expected parameter | Optional (None default) | Support open-ended scoring scenarios |

### Protocol Design

Based on analysis of:
- GEPA's `Evaluator` protocol in `.venv/lib/.../gepa/adapters/default_adapter/`
- Existing `AsyncGEPAAdapter` in `src/gepa_adk/ports/adapter.py`
- Proposal's `Scorer` interface in `docs/proposals/001-initial-package-proposal.md`

```python
@runtime_checkable
class Scorer(Protocol):
    def score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]: ...

    async def async_score(
        self,
        input_text: str,
        output: str,
        expected: str | None = None,
    ) -> tuple[float, dict[str, Any]]: ...
```

## Implementation Files

### New Files

| File | Purpose | Lines Est. |
|------|---------|------------|
| `src/gepa_adk/ports/scorer.py` | Scorer protocol definition | ~80 |
| `tests/contracts/test_scorer_protocol.py` | Contract tests | ~60 |

### Modified Files

| File | Changes |
|------|---------|
| `src/gepa_adk/ports/__init__.py` | Export Scorer |

## Test Strategy

Per constitution ADR-005 (Three-Layer Testing):

### Contract Tests (tests/contracts/test_scorer_protocol.py)
- Verify protocol is runtime-checkable
- Verify mock implementation satisfies isinstance()
- Verify method signatures match specification
- Verify return types are correct

### Unit Tests (future, with implementations)
- Test specific scorer implementations (ExactMatchScorer, etc.)
- Mock-based, fast execution

### Integration Tests (future, with ADK)
- Test CriticScorer with real ADK agents
- Marked @pytest.mark.slow

## Dependencies

### Runtime
- None (stdlib only for protocol)

### Dev
- pytest >= 8.0.0
- pytest-asyncio >= 0.24.0

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Protocol too minimal | Documented conventions in metadata dict |
| Score range violations | Convention documented, not enforced (user responsibility) |
| Async-only callers | Both methods required, simple delegation pattern documented |

## Success Metrics

From spec SC-001 through SC-004:
- [ ] Protocol can be implemented by custom scorers
- [ ] isinstance() checks work at runtime
- [ ] Both sync and async methods are functional
- [ ] Integration with evolution engine (future)

## Phase 2 Readiness

Ready for `/speckit.tasks` to generate implementation tasks:
- Research complete (research.md)
- Data model defined (data-model.md)
- Contract specified (contracts/scorer-protocol.md)
- Quickstart documented (quickstart.md)
