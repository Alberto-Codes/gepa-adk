# Implementation Plan: Generate Content Config Evolution

**Branch**: `164-config-evolution` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/164-config-evolution/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add `generate_content_config` as an evolvable component in GEPA's evolution system. This enables automatic optimization of LLM generation parameters (temperature, top_p, top_k, max_output_tokens) alongside other agent components. Implementation follows the existing ComponentHandler pattern established in #162/#163, providing serialize/apply/restore operations with YAML serialization for LLM-friendly reflection.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0 (GenerateContentConfig from google.genai.types), PyYAML (stdlib yaml), structlog >= 25.5.0
**Storage**: N/A (in-memory component handling)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux/Windows/macOS (Python library)
**Project Type**: Single project (Python library)
**Performance Goals**: Synchronous operations (no I/O), <1ms serialize/apply/restore
**Constraints**: Must follow existing ComponentHandler protocol, stateless handlers
**Scale/Scope**: Single handler implementation, ~200-300 LOC

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | Status | Notes |
|-----------|---------|--------|-------|
| I. Hexagonal Architecture | ✅ | PASS | Handler in adapters/ (accesses google.genai.types), constant in domain/, protocol in ports/ |
| II. Async-First Design | ⚠️ | N/A | ComponentHandler methods are sync (no I/O) - this is correct per existing pattern |
| III. Protocol-Based Interfaces | ✅ | PASS | ComponentHandler is a @runtime_checkable Protocol |
| IV. Three-Layer Testing | ✅ | REQUIRED | Contract tests for protocol compliance, unit tests for handler logic, integration tests for evolution loop |
| V. Observability & Code Documentation | ✅ | REQUIRED | Google-style docstrings, structlog logging in handler |
| VI. Documentation Synchronization | ✅ | REQUIRED | Update guides (single-agent, workflows), add config_evolution_demo.py example |

**ADR Alignment**:
- ADR-000: Handler in adapters/ (imports google.genai.types) ✅
- ADR-002: Follows ComponentHandler protocol ✅
- ADR-005: Three-layer tests required ✅
- ADR-006: ADK integration isolated in adapters/ ✅
- ADR-008: Use structlog for handler operations ✅

**Gate Status**: ✅ PASS - All applicable principles satisfied or required for implementation

## Project Structure

### Documentation (this feature)

```text
specs/164-config-evolution/
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
│   └── types.py                    # Add COMPONENT_GENERATE_CONFIG constant
├── ports/
│   └── component_handler.py        # Existing ComponentHandler protocol (no changes)
├── adapters/
│   ├── __init__.py                 # Export GenerateContentConfigHandler
│   └── component_handlers.py       # Add GenerateContentConfigHandler class + registration
├── utils/
│   └── config_utils.py             # NEW: serialize/deserialize/validate config utilities
└── engine/
    └── reflection_agents.py        # Add config reflection agent factory (optional)

tests/
├── contracts/
│   └── test_component_handler_contract.py  # Add config handler protocol compliance
├── unit/
│   ├── adapters/
│   │   └── test_component_handlers.py      # Add GenerateContentConfigHandler tests
│   └── utils/
│       └── test_config_utils.py            # NEW: Config utility tests
└── integration/
    └── test_config_evolution.py            # NEW: End-to-end config evolution

examples/
└── config_evolution_demo.py        # NEW: Demo script for config evolution

docs/guides/
├── single-agent.md                 # Update: mention config evolution
└── workflows.md                    # Update: mention config evolution
```

**Structure Decision**: Single project (Python library) following existing hexagonal architecture. Handler in adapters/ layer (imports ADK types), utilities in utils/, constant in domain/types.py.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations - implementation follows established patterns.*
