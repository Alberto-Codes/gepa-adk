# Implementation Plan: MergeProposer for Combining Pareto-Optimal Candidates

**Branch**: `028-merge-proposer` | **Date**: 2026-01-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/028-merge-proposer/spec.md`

## Summary

Implement a MergeProposer that performs genetic crossover by combining instruction components from two Pareto-optimal candidates that share a common ancestor. This requires extending the Candidate model with parent tracking (genealogy), implementing a common ancestor algorithm, and integrating merge proposals into the evolution loop alongside existing mutation-based proposals.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0, dataclasses (stdlib)
**Storage**: N/A (in-memory evolution state via ParetoState)
**Testing**: pytest with three-layer strategy (contract/unit/integration)
**Target Platform**: Linux server, cross-platform Python
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: Merge operations complete within single iteration budget
**Constraints**: No external state persistence; genealogy tracked in memory
**Scale/Scope**: Supports evolution runs with hundreds of candidates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | MergeProposer in engine/ layer, Candidate in domain/ |
| II. Async-First Design | ✅ PASS | MergeProposer.propose() will be async |
| III. Protocol-Based Interfaces | ✅ PASS | MergeProposer implements ProposerProtocol |
| IV. Three-Layer Testing | ✅ PASS | Contract, unit, integration tests planned |
| V. Observability & Documentation | ✅ PASS | structlog events, Google-style docstrings |

**ADR Applicability**:
- ADR-000: Hexagonal Architecture - applies to all code structure
- ADR-001: Async-First - applies to MergeProposer.propose()
- ADR-002: Protocol for Interfaces - ProposerProtocol definition
- ADR-005: Three-Layer Testing - all tests

## Project Structure

### Documentation (this feature)

```text
specs/028-merge-proposer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── models.py         # Extend Candidate with parent tracking
│   └── types.py          # Add ParentIds type alias
├── engine/
│   ├── merge_proposer.py # NEW: MergeProposer implementation
│   ├── genealogy.py      # NEW: Common ancestor algorithm
│   └── async_engine.py   # Integrate merge proposals
└── ports/
    └── proposer.py       # NEW: ProposerProtocol definition

tests/
├── contracts/
│   └── test_proposer_protocol.py # NEW: Protocol compliance
├── unit/
│   ├── test_merge_proposer.py    # NEW: MergeProposer unit tests
│   └── test_genealogy.py         # NEW: Genealogy algorithm tests
└── integration/
    └── test_merge_evolution.py   # NEW: Full evolution with merge
```

**Structure Decision**: Single project layout following existing hexagonal architecture. New files added to engine/ and ports/ layers with corresponding test coverage.

## Complexity Tracking

*No violations - design follows constitution principles.*
