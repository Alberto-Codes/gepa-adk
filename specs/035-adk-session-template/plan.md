# Implementation Plan: ADK Session State Template Substitution

**Branch**: `035-adk-session-template` | **Date**: 2026-01-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/035-adk-session-template/spec.md`

## Summary

Enable ADK's native template substitution syntax (`{key}`) in reflection agent instructions so that session state values are automatically injected without manual user message construction. This replaces the current workaround of embedding data via Python f-strings in user messages.

**Key Finding**: The correct ADK syntax is `{key}` (not `{state.key}` as originally assumed in the spec). ADK's `inject_session_state()` function automatically processes these placeholders against `session.state[key]` during instruction processing.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, structlog>=25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux server (Python library)
**Project Type**: Single project (library)
**Performance Goals**: Performance neutral - no increase in execution time vs current workaround
**Constraints**: Must work across all supported LLM providers (Gemini, Ollama, OpenAI)
**Scale/Scope**: Targeted change to reflection agent instruction handling

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | PASS | Changes in `engine/` layer only; no new external imports |
| II. Async-First Design | PASS | Existing async flows unchanged; no new sync/async bridging |
| III. Protocol-Based Interfaces | PASS | No protocol changes; internal implementation detail |
| IV. Three-Layer Testing | PASS | Unit tests for template substitution; integration tests for multi-provider |
| V. Observability & Code Documentation | PASS | Existing structlog patterns; update docstrings |
| VI. Documentation Synchronization | PASS | Update reflection-prompts guide; no new examples needed |

**Gate Result**: PASS - All principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/035-adk-session-template/
├── plan.md              # This file
├── research.md          # Phase 0 output - ADK template syntax research
├── architecture.md      # ADK substitution methodology + reflection agent design
├── data-model.md        # Phase 1 output - minimal (no new entities)
├── quickstart.md        # Phase 1 output - usage examples
├── contracts/           # Phase 1 output - N/A (no new APIs)
├── checklists/
│   └── requirements.md  # Specification validation checklist
└── tasks.md             # Phase 3 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── engine/
│   └── adk_reflection.py  # MODIFY: Use template syntax in instruction
├── adapters/              # No changes
├── ports/                 # No changes
├── domain/                # No changes
└── utils/                 # No changes

tests/
├── unit/
│   └── engine/
│       └── test_adk_reflection.py  # ADD: Template substitution tests
└── integration/
    └── test_reflection_template.py  # ADD: Multi-provider template tests

docs/
└── guides/
    └── reflection-prompts.md  # MODIFY: Document {key} template syntax
```

**Structure Decision**: Single project structure. This feature modifies existing `engine/adk_reflection.py` to use ADK's native template substitution instead of manual message construction. No new modules or architectural changes.

## Complexity Tracking

> No violations - feature aligns with all constitution principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
