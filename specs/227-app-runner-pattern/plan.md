# Implementation Plan: Support ADK App/Runner Pattern for Evolution

**Branch**: `227-app-runner-pattern` | **Date**: 2026-01-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/227-app-runner-pattern/spec.md`

## Summary

Add optional `app` and `runner` parameters to `evolve_workflow()` and `evolve_group()` APIs, enabling users to pass pre-configured ADK `App` or `Runner` instances. This allows evolution to leverage existing infrastructure (session services, artifact services, plugins, memory services) instead of creating its own defaults. The implementation extracts services from provided instances and passes them to the existing AgentExecutor, maintaining full backward compatibility.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, structlog >= 25.5.0
**Storage**: N/A (uses user-provided services or InMemorySessionService default)
**Testing**: pytest with three-layer testing (contract, unit, integration)
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: Single Python library (src/ layout)
**Performance Goals**: No degradation from baseline; service extraction adds negligible overhead
**Constraints**: Must maintain 100% backward compatibility with existing API
**Scale/Scope**: Library API change affecting 2-3 files plus tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | Changes in `api.py` (public API layer) and `adapters/agent_executor.py` (adapter layer). No new external imports in domain/ports. |
| II. Async-First Design | ✅ PASS | All affected functions are async. No sync/async bridging added. |
| III. Protocol-Based Interfaces | ✅ PASS | Uses existing `AgentExecutorProtocol`. No new protocols required. |
| IV. Three-Layer Testing | ✅ REQUIRED | Must add unit tests for parameter combinations, integration tests for App/Runner usage. |
| V. Observability & Documentation | ✅ REQUIRED | Must update docstrings for new parameters, add examples in guides. |
| VI. Documentation Synchronization | ✅ REQUIRED | Update `docs/guides/workflows.md` with App/Runner integration examples. |

**ADR References**:
- ADR-000: Hexagonal Architecture (api.py is public entry, adapters handle ADK integration)
- ADR-006: External Library Integration (App/Runner types come from google.adk)

## Project Structure

### Documentation (this feature)

```text
specs/227-app-runner-pattern/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 3 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── api.py               # MODIFY: Add app/runner parameters to evolve_workflow, evolve_group
├── adapters/
│   └── agent_executor.py # MODIFY: Accept runner parameter, extract services from App
├── ports/
│   └── agent_executor.py # NO CHANGE: Protocol already supports session_service injection
└── domain/              # NO CHANGE: Pure domain models unaffected

tests/
├── unit/
│   └── test_api_app_runner.py    # CREATE: Unit tests for parameter precedence
└── integration/
    └── test_app_runner_integration.py  # CREATE: Integration tests with real App/Runner

docs/
└── guides/
    └── workflows.md     # MODIFY: Add App/Runner integration examples
```

**Structure Decision**: Single project (default). Changes are localized to API layer and one adapter. No new modules needed.

## Complexity Tracking

No violations. Feature adds optional parameters with clear precedence rules. No new abstractions required.
