# Implementation Plan: Multi-Agent Component Routing

**Branch**: `166-multi-agent-routing` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/166-multi-agent-routing/spec.md`

## Summary

Enable per-agent component routing in MultiAgentAdapter to support evolving different components (instruction, output_schema, generate_content_config) on different agents simultaneously. This replaces the current `{agent.name}_instruction` key format with ADR-012 compliant dot-separated qualified names (`generator.instruction`, `critic.output_schema`) and adds proper routing logic to apply/restore candidates to the correct agents.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0
**Storage**: N/A (in-memory candidate/component state)
**Testing**: pytest with three-layer strategy (contracts, unit, integration)
**Target Platform**: Linux/macOS development environments
**Project Type**: Single project (Python library with CLI)
**Performance Goals**: N/A - internal component routing logic
**Constraints**: Breaking API change - version bump to 0.3.x
**Scale/Scope**: Supports 3+ agents with 3+ components each per evolution run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Hexagonal Architecture | PASS | Changes affect adapters/ layer only (MultiAgentAdapter); uses existing domain types (ComponentSpec, QualifiedComponentName) and ports (ComponentHandler protocol) |
| II. Async-First Design | PASS | evaluate() remains async; _apply_candidate/_restore_agents are sync helper methods (no I/O) |
| III. Protocol-Based Interfaces | PASS | Uses existing ComponentHandler protocol for handler lookup; no new protocols required |
| IV. Three-Layer Testing | REQUIRED | Must add: contract tests for handler interface, unit tests for routing logic, integration tests for multi-agent evolution |
| V. Observability & Documentation | REQUIRED | Must update: Multi-Agent Guide (docs/guides/multi-agent.md), example files, structlog context binding |
| VI. Documentation Synchronization | REQUIRED | Must update: multi-agent guide, create/update example for per-agent components |

**ADR Compliance**:
- ADR-012: REQUIRED - Must use ComponentSpec.parse() for qualified name parsing
- ADR-000: PASS - adapters/ layer isolation maintained
- ADR-002: PASS - Uses ComponentHandler protocol
- ADR-005: REQUIRED - Three-layer tests must be added

## Project Structure

### Documentation (this feature)

```text
specs/166-multi-agent-routing/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 3 output
```

**Architecture Skipped**: Feature is localized to adapters/ layer with simple apply/restore pattern. No external integrations or complex data flows requiring architectural documentation.

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   └── types.py                    # ComponentSpec, QualifiedComponentName (existing)
├── ports/
│   └── component_handler.py        # ComponentHandler protocol (existing)
├── adapters/
│   ├── multi_agent.py              # MODIFY: Add per-agent routing
│   └── component_handlers.py       # ComponentHandlerRegistry (existing)
├── engine/
│   └── [unchanged]
└── api.py                          # MODIFY: Add components parameter to evolve_group

tests/
├── contracts/
│   └── test_component_handler.py   # Existing handler contract tests
├── unit/
│   └── adapters/
│       └── test_multi_agent.py     # MODIFY: Add routing unit tests
└── integration/
    └── test_multi_agent_components.py  # CREATE: Multi-agent integration tests

docs/
└── guides/
    └── multi-agent.md              # MODIFY: Document per-agent components

examples/
└── multi_agent_component_demo.py   # CREATE: Demo per-agent component evolution
```

**Structure Decision**: Single-project Python library with hexagonal architecture. Changes are localized to adapters/ layer with corresponding test additions across all three layers.

## Complexity Tracking

No violations - feature aligns with constitution principles.
