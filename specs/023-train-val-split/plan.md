# Implementation Plan: Train/Val Split for Evolution Scoring

**Branch**: `023-train-val-split` | **Date**: 2026-01-14 | **Spec**: [/var/home/Alberto-Codes/Projects/gepa-adk/specs/023-train-val-split/spec.md](/var/home/Alberto-Codes/Projects/gepa-adk/specs/023-train-val-split/spec.md)
**Input**: Feature specification from `/var/home/Alberto-Codes/Projects/gepa-adk/specs/023-train-val-split/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add support for separate trainset (reflection) and valset (scoring) datasets during evolution, defaulting valset to trainset when not provided. This ensures acceptance decisions and candidate selection reflect generalization performance while preserving backward compatibility.

**Technical Approach**: Align gepa-adk behavior with upstream GEPA patterns:
- Use trainset exclusively for reflection (trace capture and reflective dataset building)
- Use valset exclusively for baseline/proposal scoring, acceptance decisions, and Pareto/candidate scoring
- Default valset to trainset when omitted
- Keep evaluation batches separated and clearly reported in results

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0 (existing); no new dependencies
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux server, macOS (development)
**Project Type**: Single project (Python library)
**Performance Goals**: No measurable regression vs current evolution runtime for same dataset size
**Constraints**: Async-first design; hexagonal architecture boundaries; backwards compatible API
**Scale/Scope**: < 100 candidates per run; trainset/valset sizes typically <= 1,000 examples

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Hexagonal Architecture** | ✅ Pass | Engine changes remain in `engine/`, domain models in `domain/`, no adapter imports in engine |
| **II. Async-First Design** | ✅ Pass | All evaluation and proposal flows remain async |
| **III. Protocol-Based Interfaces** | ✅ Pass | No new ports required for this change |
| **IV. Three-Layer Testing** | ✅ Pass | Contract, unit, and integration tests planned |
| **V. Observability & Documentation** | ✅ Pass | Structured logging for train/val scoring events; docstrings follow standards |

**Post-Design Re-check**: All principles satisfied. No violations.

## Project Structure

### Documentation (this feature)

```text
/var/home/Alberto-Codes/Projects/gepa-adk/specs/023-train-val-split/
├── plan.md              # This file
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── train-val-contract.md
└── tasks.md             # (Created by /speckit.tasks)
```

### Source Code (repository root)

```text
/var/home/Alberto-Codes/Projects/gepa-adk/src/gepa_adk/
├── api.py                       # MODIFIED: pass valset into engine; valset default
├── engine/
│   └── async_engine.py          # MODIFIED: separate reflection vs scoring datasets
├── domain/
│   └── models.py                # MODIFIED: expose valset-based scoring in results
└── adapters/
    └── adk_adapter.py           # VERIFY: supports evaluate on any dataset

/var/home/Alberto-Codes/Projects/gepa-adk/tests/
├── contracts/
│   └── test_train_val_contract.py      # NEW: dataset split contract
├── unit/
│   └── test_valset_scoring.py          # NEW: valset-based acceptance
└── integration/
    └── test_train_val_split.py         # NEW: end-to-end evolution split
```

**Structure Decision**: Keep all changes within existing hexagonal layout. No new top-level modules required.

## Complexity Tracking

> No violations. Design follows all constitution principles.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Dataset split | Separate reflection and scoring batches | Aligns with upstream GEPA and reduces overfitting risk |
| Defaults | Valset defaults to trainset | Backward compatibility for existing users |
| Reporting | Expose valset-based scores | Improves clarity of acceptance decisions |

## Implementation Phases

### Phase 0: Research ✅
- Review upstream GEPA trainset/valset behavior in `.venv` reference implementation
- Confirm reflection uses trainset while scoring uses valset
- Identify best spots in gepa-adk to separate evaluation batches

### Phase 1: Design ✅
- Data model specification for train/val datasets and scoring results
- Contract for dataset split behavior and invariants
- Quickstart guide for valset usage and defaults
- Update agent context via script

### Phase 2: Implementation (via /speckit.tasks)
1. Update `AsyncGEPAEngine` to evaluate reflection on trainset and scoring on valset
2. Default valset to trainset in public API and engine creation
3. Ensure acceptance decisions and candidate selection use valset scores
4. Update `EvolutionResult` to surface valset-based score data
5. Add contract, unit, and integration tests for split behavior

## References

- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/api.py
- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/core/engine.py
- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/proposer/reflective_mutation/reflective_mutation.py
- /var/home/Alberto-Codes/Projects/gepa-adk/docs/adr/ADR-000-hexagonal-architecture.md
- /var/home/Alberto-Codes/Projects/gepa-adk/docs/adr/ADR-001-async-first-architecture.md
- /var/home/Alberto-Codes/Projects/gepa-adk/docs/adr/ADR-005-three-layer-testing.md
