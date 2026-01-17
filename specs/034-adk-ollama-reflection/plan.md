# Implementation Plan: ADK Ollama Reflection

**Branch**: `034-adk-ollama-reflection` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/034-adk-ollama-reflection/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Enable ADK LlmAgents to work as reflection agents with Ollama/LiteLLM models that don't support native structured output. The implementation will enhance extraction logic to filter reasoning text, inject schema guidance into prompts for non-compliant models, and improve fallback patterns to ensure clean instruction extraction from free-form responses.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, litellm >= 1.80.13, structlog >= 25.5.0
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest with three-layer strategy (contracts, unit, integration)
**Target Platform**: Linux server (development), cross-platform (runtime)
**Project Type**: Single project (Python library)
**Performance Goals**: Extraction should add negligible overhead (<10ms per call)
**Constraints**: Must work with existing ProposerProtocol interface; no breaking changes to public API
**Scale/Scope**: Affects single component flow (reflection → extraction → proposal)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | Changes confined to engine/ (proposer.py) and utils/ (events.py); no new external imports in domain/ports |
| II. Async-First Design | ✅ PASS | create_adk_reflection_fn() already async; all new logic will remain async |
| III. Protocol-Based Interfaces | ✅ PASS | No changes to ProposerProtocol interface; internal implementation only |
| IV. Three-Layer Testing | ✅ REQUIRED | Must add unit tests for extraction patterns, contract tests for protocol compliance, integration tests for Ollama models |
| V. Observability & Documentation | ✅ REQUIRED | Must log extraction method used; update docstrings for new parameters |
| VI. Documentation Synchronization | ✅ REQUIRED | Update examples/multi_agent.py; update guides for reflection_agent configuration |

**ADRs Applicable**:
- ADR-000: Hexagonal Architecture - extraction logic stays in engine layer
- ADR-001: Async-First - maintain async flow in reflection functions
- ADR-006: External Library Integration - no new external libs (regex from stdlib)
- ADR-008: Structured Logging - log extraction method for observability

**Gate Result**: ✅ PASSED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/034-adk-ollama-reflection/
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
├── domain/              # NO CHANGES - pure domain models
│   ├── models.py
│   ├── types.py
│   └── exceptions.py
│
├── ports/               # NO CHANGES - protocol interfaces
│   ├── proposer.py
│   └── adapter.py
│
├── engine/              # PRIMARY CHANGES
│   └── proposer.py      # Enhanced extraction logic, schema-in-prompt injection
│
├── adapters/            # MINOR CHANGES
│   └── adk_adapter.py   # Pass schema config to reflection function
│
└── utils/               # POTENTIAL CHANGES
    └── events.py        # Shared extraction utilities (if refactored)

tests/
├── contracts/           # Protocol compliance
│   └── test_proposer_protocol.py
├── unit/                # Business logic with mocks
│   ├── engine/
│   │   └── test_proposer.py
│   └── utils/
│       └── test_events.py
└── integration/         # Real ADK/LLM calls
    └── engine/
        └── test_proposer_integration.py

examples/
└── multi_agent.py       # Update with Ollama reflection agent example

docs/guides/
└── multi-agent.md       # Update reflection_agent documentation
```

**Structure Decision**: Single project structure following existing hexagonal architecture. Changes primarily in engine/proposer.py with supporting test and documentation updates.

## Complexity Tracking

> **No violations identified** - All changes fit within existing architecture patterns.
