# Implementation Plan: Frontier Types and Valset Evaluation Policies

**Branch**: `027-frontier-eval-policy` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/027-frontier-eval-policy/spec.md`

## Summary

Enable multi-objective Pareto frontier tracking with configurable frontier types (instance, objective, hybrid, cartesian) and valset evaluation policies (full_eval, subset). Port upstream GEPA's frontier tracking and evaluation policy patterns while maintaining backward compatibility with existing instance-level tracking.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0, dataclasses (stdlib)
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Library (Python package)
**Project Type**: Single project (src/ layout)
**Performance Goals**: Sub-millisecond frontier updates; O(n*m) for cartesian where n=examples, m=objectives
**Constraints**: Backward compatible with FrontierType.INSTANCE default; no new external dependencies
**Scale/Scope**: Support 1000+ validation examples with 10+ objectives

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Hexagonal Architecture (Ports & Adapters)

| Requirement | Status | Notes |
|-------------|--------|-------|
| domain/ has no external imports | PASS | FrontierType enum, ParetoState, ParetoFrontier are stdlib-only |
| ports/ has no external imports | PASS | EvaluationPolicyProtocol will be Protocol-based |
| adapters/ contains external integrations | PASS | FullEvaluationPolicy, SubsetEvaluationPolicy in adapters/ |
| engine/ receives adapters via injection | PASS | AsyncGEPAEngine receives evaluation_policy via constructor |

### II. Async-First Design

| Requirement | Status | Notes |
|-------------|--------|-------|
| I/O operations are async | PASS | Evaluation calls are already async |
| No internal sync/async bridging | PASS | Follows existing async patterns |
| Protocol methods are coroutines | PASS | EvaluationPolicyProtocol.get_eval_batch() returns list, no I/O needed |

### III. Protocol-Based Interfaces

| Requirement | Status | Notes |
|-------------|--------|-------|
| Ports use typing.Protocol | PASS | EvaluationPolicyProtocol using Protocol |
| @runtime_checkable when isinstance() needed | PASS | Will use @runtime_checkable |
| No ABC inheritance | PASS | Pure Protocol-based |

### IV. Three-Layer Testing

| Requirement | Status | Notes |
|-------------|--------|-------|
| Contract tests in tests/contracts/ | PASS | Protocol compliance for EvaluationPolicyProtocol |
| Unit tests in tests/unit/ | PASS | Frontier update logic, dominance calculations |
| Integration tests in tests/integration/ | PASS | End-to-end evolution with different frontier types |

### V. Observability & Documentation Standards

| Requirement | Status | Notes |
|-------------|--------|-------|
| structlog with context binding | PASS | Existing logging patterns |
| Google-style docstrings | PASS | Will follow existing style |
| Exceptions inherit EvolutionError | PASS | ValidationError for missing objective_scores |

**Gate Status**: PASS - Ready to proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/027-frontier-eval-policy/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── types.py          # FrontierType enum (already exists - extend validation)
│   ├── state.py          # ParetoState, ParetoFrontier (extend for new frontier types)
│   └── exceptions.py     # ConfigurationError (exists)
├── ports/
│   └── selector.py       # EvaluationPolicyProtocol (new protocol)
├── adapters/
│   ├── evaluation_policy.py  # FullEvaluationPolicy, SubsetEvaluationPolicy (new)
│   └── candidate_selector.py # Existing selectors (minor updates if needed)
└── engine/
    └── async_engine.py   # Wire evaluation_policy parameter

tests/
├── contracts/
│   └── test_evaluation_policy_protocol.py  # Protocol compliance
├── unit/
│   ├── domain/
│   │   └── test_frontier_types.py  # Dominance logic for each frontier type
│   └── adapters/
│       └── test_evaluation_policy.py  # Policy implementations
└── integration/
    └── test_frontier_evolution.py  # End-to-end with different configs
```

**Structure Decision**: Follows existing single-project layout with hexagonal architecture. Extends domain/state.py for frontier tracking and adds new port (EvaluationPolicyProtocol) with adapter implementations.

## Complexity Tracking

> No violations. Implementation follows existing patterns from 022-pareto-frontier and 026-objective-scores features.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |
