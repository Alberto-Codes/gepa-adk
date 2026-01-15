# Implementation Plan: Pareto Frontier Tracking and Candidate Selection

**Branch**: `022-pareto-frontier` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/022-pareto-frontier/spec.md`

## Summary

Implement Pareto frontier tracking and candidate selection strategies for gepa-adk, enabling evolution to explore diverse candidates that excel on different validation examples rather than always selecting the single best average performer. This is GEPA's core differentiator from simple greedy optimization.

**Technical Approach**: Adapt GEPA's proven Pareto algorithms into gepa-adk's hexagonal architecture:
- New `ParetoState` domain model for per-example score tracking
- `CandidateSelectorProtocol` port with three implementations (Pareto, greedy, epsilon-greedy)
- Engine integration via optional `candidate_selector` parameter

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0 (existing); no new dependencies
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux server, macOS (development)
**Project Type**: Single project (Python library)
**Performance Goals**: Frontier update < 10ms for 100 candidates × 50 examples
**Constraints**: No external imports in domain layer; async-first design
**Scale/Scope**: < 100 candidates, < 50 validation examples per evolution run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Hexagonal Architecture** | ✅ Pass | Domain models in `domain/`, protocol in `ports/`, selectors in `adapters/` |
| **II. Async-First Design** | ✅ Pass | Selector protocol is async; engine awaits selection; selection logic remains pure computation |
| **III. Protocol-Based Interfaces** | ✅ Pass | `CandidateSelectorProtocol` uses `typing.Protocol` |
| **IV. Three-Layer Testing** | ✅ Pass | Contract, unit, and integration tests planned |
| **V. Observability & Documentation** | ✅ Pass | Google-style docstrings, structlog events for selection |

**Post-Design Re-check**: All principles satisfied. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/022-pareto-frontier/
├── plan.md              # This file
├── research.md          # GEPA analysis and design decisions
├── data-model.md        # ParetoState, ParetoFrontier, selector models
├── quickstart.md        # Usage guide for Pareto selection
├── contracts/           # Protocol and model contracts
│   ├── selector-protocol.md
│   └── pareto-state.md
└── tasks.md             # (Created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── adapters/
│   └── candidate_selector.py  # NEW: Pareto, Greedy, EpsilonGreedy selectors
├── domain/
│   ├── models.py        # Existing: Candidate, EvolutionConfig, etc.
│   ├── state.py         # NEW: ParetoState, ParetoFrontier
│   └── types.py         # MODIFIED: Add FrontierType
├── ports/
│   └── selector.py      # NEW: CandidateSelectorProtocol
├── engine/
│   └── async_engine.py  # MODIFIED: Integrate selector
└── api.py               # MODIFIED: Add candidate_selector parameter

tests/
├── contracts/
│   └── test_candidate_selector_protocol.py  # NEW: Protocol compliance
├── unit/
│   ├── test_pareto_state.py         # NEW: State and frontier logic
│   └── test_candidate_selectors.py  # NEW: Selector behavior
└── integration/
    └── test_pareto_evolution.py     # NEW: End-to-end with Pareto
```

**Structure Decision**: Follows existing hexagonal layout. New files are:
- 1 domain model file (`state.py`)
- 1 port protocol file (`selector.py`)
- 1 adapter implementation file (`candidate_selector.py`)
- 4 test files across three layers

## Complexity Tracking

> No violations. Design follows all constitution principles.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Selector location | `adapters/` | Port implementations; no external deps |
| State vs Engine | Separate `ParetoState` class | Cleaner than extending `_EngineState` |
| Frontier types | Only `instance` initially | Reduces scope; others can be added later |

## Implementation Phases

### Phase 0: Research ✅
- Analyzed GEPA reference implementation
- Identified key algorithms (`remove_dominated_programs`, `select_program_candidate_from_pareto_front`)
- Mapped GEPA concepts to gepa-adk architecture

### Phase 1: Design ✅
- Created data model specification
- Defined protocol contract
- Wrote quickstart guide

### Phase 2: Implementation (via /speckit.tasks)
1. Add `FrontierType` to `domain/types.py`
2. Create `ParetoState` and `ParetoFrontier` in `domain/state.py`
3. Create `CandidateSelectorProtocol` in `ports/selector.py`
4. Implement selectors in `adapters/candidate_selector.py`
5. Integrate selector into `AsyncGEPAEngine`
6. Add `candidate_selector` parameter to public API
7. Write tests (contract → unit → integration)

## References

- [GEPA candidate_selector.py](.venv/lib/python3.12/site-packages/gepa/strategies/candidate_selector.py)
- [GEPA state.py](.venv/lib/python3.12/site-packages/gepa/core/state.py)
- [GEPA gepa_utils.py](.venv/lib/python3.12/site-packages/gepa/gepa_utils.py)
- [ADR-000: Hexagonal Architecture](docs/adr/ADR-000-hexagonal-architecture.md)
- [ADR-002: Protocol for Interfaces](docs/adr/ADR-002-protocol-for-interfaces.md)
- [ADR-005: Three-Layer Testing](docs/adr/ADR-005-three-layer-testing.md)
