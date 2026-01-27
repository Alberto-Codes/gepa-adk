# Implementation Plan: Model Evolution Support

**Branch**: `238-model-evolution` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/238-model-evolution/spec.md`

## Summary

Add support for evolving the model used by ADK agents through the existing evolutionary optimization process. Users provide a list of allowed model choices via the `model_choices` parameter to `evolve()`. The system evolves models alongside other components (instruction, schema, config) while preserving wrapper configurations (LiteLLM custom headers, auth, etc.) by mutating only the `.model` attribute.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new dependencies)
**Storage**: N/A (in-memory evolution state)
**Testing**: pytest with asyncio_mode="auto", markers: unit, contract, integration
**Target Platform**: Cross-platform Python library
**Project Type**: Single Python package (src layout)
**Performance Goals**: No degradation from existing evolution performance
**Constraints**: Must preserve wrapper object configuration during model mutation
**Scale/Scope**: Extends existing component evolution system

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | ModelConstraints in domain/types.py (no external deps), ModelHandler in adapters/ (ADK imports allowed), reflection agent factory in engine/ |
| **II. Async-First Design** | ✅ PASS | No new async operations - integrates with existing async evolution flow |
| **III. Protocol-Based Interfaces** | ✅ PASS | ModelHandler implements existing ComponentHandler protocol |
| **IV. Three-Layer Testing** | ✅ REQUIRED | Must add: contract tests (protocol compliance), unit tests (handler logic), integration tests (end-to-end) |
| **V. Observability & Documentation** | ✅ REQUIRED | Must add: Google-style docstrings, structlog events for model evolution |
| **VI. Documentation Synchronization** | ✅ REQUIRED | New public API parameter - must update docs/guides/single-agent.md, examples/ |

**Applicable ADRs**:
- ADR-000: Hexagonal Architecture - layer placement of ModelConstraints, ModelHandler
- ADR-002: Protocol for Interfaces - ModelHandler implements ComponentHandler protocol
- ADR-005: Three-Layer Testing - test structure required
- ADR-008: Structured Logging - log model evolution events

## Project Structure

### Documentation (this feature)

```text
specs/238-model-evolution/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 3 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   └── types.py         # ADD: ModelConstraints dataclass
├── ports/
│   └── component_handler.py  # UNCHANGED (protocol already exists)
├── adapters/
│   └── component_handlers.py # ADD: ModelHandler class
├── engine/
│   └── reflection_agents.py  # ADD: create_model_reflection_agent()
├── api.py               # MODIFY: add model_choices parameter to evolve()
└── utils/               # UNCHANGED

tests/
├── contracts/
│   └── test_component_handler_contract.py  # ADD: ModelHandler protocol compliance
├── unit/
│   ├── adapters/
│   │   └── test_model_handler.py           # ADD: handler unit tests
│   └── domain/
│       └── test_model_constraints.py       # ADD: constraints unit tests
└── integration/
    └── test_model_evolution.py             # ADD: end-to-end tests
```

**Structure Decision**: Follows existing hexagonal architecture pattern. ModelConstraints goes in domain/ (pure Python, no external deps). ModelHandler goes in adapters/ (implements protocol, accesses ADK types). Reflection agent factory goes in engine/ (orchestration).

## Complexity Tracking

No violations - feature fits cleanly within existing architecture patterns.

## Affected Layers

| Layer | Files | Changes |
|-------|-------|---------|
| domain/ | types.py | Add ModelConstraints dataclass |
| adapters/ | component_handlers.py | Add ModelHandler class + registration |
| engine/ | reflection_agents.py | Add create_model_reflection_agent factory |
| api/ | api.py | Add model_choices parameter, integrate with evolution flow |

## Key Design Decisions

1. **Opt-in via model_choices parameter**: Model evolution only occurs when explicitly requested
2. **Duck-typing for wrapper preservation**: Check for `.model` attribute rather than specific types
3. **Auto-include current model**: User's model always in allowed list as baseline
4. **Partial application for factory**: Use `functools.partial` to bake allowed_models into agent factory
5. **No model validation at config time**: Trust user-provided model names (validation happens at execution)
