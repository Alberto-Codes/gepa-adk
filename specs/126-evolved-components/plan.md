# Implementation Plan: Evolved Components Dictionary

**Branch**: `126-evolved-components` | **Date**: 2026-01-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/126-evolved-components/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace `EvolutionResult.evolved_component_text: str` with `evolved_components: dict[str, str]` to enable multi-component evolution. This change exposes all evolved components (instruction, output_schema, etc.) via dictionary access while maintaining default instruction-only evolution behavior. Additionally, enhance `IterationRecord` to track which component was evolved per iteration.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, dataclasses (stdlib)
**Storage**: N/A (in-memory domain models)
**Testing**: pytest with three-layer testing (contracts, unit, integration)
**Target Platform**: Cross-platform Python library
**Project Type**: Single Python package (hexagonal architecture)
**Performance Goals**: N/A (API change, no performance-critical path)
**Constraints**: Breaking API change (no backward compatibility wrapper per spec)
**Scale/Scope**: Affects 30+ files referencing `evolved_component_text`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicable? | Status | Notes |
|-----------|-------------|--------|-------|
| I. Hexagonal Architecture | ✅ Yes | ✅ Pass | Changes isolated to `domain/models.py` (pure Python), `engine/async_engine.py` (orchestration) |
| II. Async-First Design | ❌ No | N/A | No I/O operations affected; domain model change only |
| III. Protocol-Based Interfaces | ❌ No | N/A | No new protocols required; internal data structure change |
| IV. Three-Layer Testing | ✅ Yes | ⚠️ Required | Must update tests in contracts/, unit/, integration/ for new field |
| V. Observability & Code Documentation | ✅ Yes | ⚠️ Required | Must update docstrings on EvolutionResult, IterationRecord; update examples |
| VI. Documentation Synchronization | ✅ Yes | ⚠️ Required | Breaking change requires docs/guides updates + example migrations |

**ADRs Referenced**:
- ADR-000: Hexagonal Architecture - domain/ layer purity maintained
- ADR-005: Three-Layer Testing - test updates across all layers

**Gate Result**: ✅ PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/126-evolved-components/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
├── architecture.md      # Phase 2 output (/speckit.plan command - conditional)
└── tasks.md             # Phase 3 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── models.py        # EvolutionResult, IterationRecord (MODIFY)
│   └── __init__.py      # Re-exports (CHECK)
├── engine/
│   └── async_engine.py  # _build_result(), _record_iteration() (MODIFY)
├── api.py               # evolve() result handling (MODIFY)
├── adapters/            # (NO CHANGES - layer boundary maintained)
├── ports/               # (NO CHANGES - no protocol changes)
└── utils/               # (NO CHANGES)

tests/
├── contracts/
│   ├── test_async_engine_contracts.py  # (MODIFY)
│   └── test_objective_scores_models.py # (CHECK)
├── unit/
│   ├── domain/test_models.py           # (MODIFY)
│   ├── engine/test_async_engine.py     # (MODIFY)
│   └── test_api.py                     # (MODIFY)
└── integration/
    └── engine/test_adk_reflection.py   # (MODIFY)

examples/
├── basic_evolution.py              # (MODIFY)
├── basic_evolution_adk_reflection.py  # (MODIFY)
├── critic_agent.py                 # (MODIFY)
└── schema_evolution_critic.py      # (MODIFY)

docs/
├── index.md                        # (MODIFY - breaking change note)
├── getting-started.md              # (MODIFY - API example)
├── guides/single-agent.md          # (MODIFY - result access)
├── guides/critic-agents.md         # (MODIFY - result access)
└── reference/glossary.md           # (MODIFY - term update)
```

**Structure Decision**: Hexagonal architecture with domain/, ports/, adapters/, engine/ layers. This feature modifies domain/ and engine/ only, maintaining layer boundaries per ADR-000.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations - section not applicable.*

## Phase 2 Decision: Architecture

**Decision**: Skip architecture.md

**Justification**:
- Feature touches only 2 layers (domain, engine), not 3+
- No external system integrations
- No complex data flow (simple field replacement in dataclass)
- Constitution Check references only 2 ADRs (ADR-000, ADR-005)

The data flow is straightforward:
1. `Candidate.components` → `_build_result()` → `EvolutionResult.evolved_components`
2. `_record_iteration()` → `IterationRecord.evolved_component`

No architectural diagrams are needed for this change.
