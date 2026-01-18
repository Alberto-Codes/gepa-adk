# Implementation Plan: ADK Session State Management for Reflection Agent

**Branch**: `122-adk-session-state` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/122-adk-session-state/spec.md`
**Related Issue**: GitHub Issue #100

## Summary

Enable the reflection agent to fully leverage ADK's session state management by:
1. Injecting input data (component_text, trials) via session state instead of message construction
2. Configuring output_key for automatic result storage in session state
3. Supporting multi-agent workflows where state flows between agents via ADK session

The implementation builds on existing patterns in `adk_reflection.py` which already uses session state for input injection. The main additions are output_key configuration and state-based output retrieval.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0
**Storage**: N/A (in-memory session state via ADK's InMemorySessionService)
**Testing**: pytest with contract/unit/integration layers
**Target Platform**: Linux server / Python runtime
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: No regression from current reflection performance
**Constraints**: Backward compatibility with existing `adk_reflection_fn` interface
**Scale/Scope**: Affects 2-3 modules in adapters/ and engine/ layers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicable? | Status | Notes |
|-----------|-------------|--------|-------|
| I. Hexagonal Architecture | Yes | ✅ PASS | Changes confined to adapters/ and engine/ layers. Domain models unchanged. |
| II. Async-First Design | Yes | ✅ PASS | ADK reflection already async. No sync/async bridging needed. |
| III. Protocol-Based Interfaces | Yes | ✅ PASS | ReflectionFn signature unchanged. No new protocols needed. |
| IV. Three-Layer Testing | Yes | ⚠️ REQUIRED | Must add contract tests (protocol compliance), unit tests (mocks), integration tests (real ADK). |
| V. Observability & Code Documentation | Yes | ⚠️ REQUIRED | Existing structlog patterns. Google-style docstrings required. |
| VI. Documentation Synchronization | No | N/A | Internal implementation change, not user-facing API change. No docs/ updates needed. |

**Gate Result**: ✅ PASS - No violations. Testing and documentation requirements noted for implementation.

## Project Structure

### Documentation (this feature)

```text
specs/122-adk-session-state/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (conditional)
└── tasks.md             # Phase 3 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/              # NO CHANGES - models unchanged
├── ports/               # NO CHANGES - protocols unchanged
├── adapters/
│   └── multi_agent.py   # REFACTOR - use shared extract_output_from_state()
├── engine/
│   ├── adk_reflection.py # MODIFY - add output_key config, use shared extractor
│   └── proposer.py      # NO CHANGES - interface unchanged
└── utils/
    └── events.py        # ADD - extract_output_from_state() shared utility

tests/
├── contracts/           # ADD - protocol compliance tests
├── unit/
│   ├── engine/
│   │   └── test_adk_reflection_state.py  # ADD - unit tests
│   ├── utils/
│   │   └── test_events_state.py          # ADD - utility tests
│   └── adapters/
│       └── test_multi_agent_refactor.py  # ADD - refactor verification
└── integration/
    └── test_adk_state_flow.py            # ADD - integration tests
```

**Structure Decision**: Single project with hexagonal layers. Shared extraction logic in `utils/` (accessible from both adapters/ and engine/ per hexagonal rules). Domain and ports layers untouched.

### Architectural Decision: Shared Utility Location

**Problem**: Both `engine/adk_reflection.py` and `adapters/multi_agent.py` need output_key extraction logic.

**Constraint**: Engine layer CANNOT import from adapters/ (Constitution §I, ADR-000).

**Solution**: Extract shared logic to `utils/events.py`:
- `utils/` is accessible from both adapters/ and engine/
- Follows DRY principle
- `extract_output_from_state()` complements existing `extract_final_output()`

**Impact**:
1. **ADD** `extract_output_from_state()` to `utils/events.py`
2. **REFACTOR** `multi_agent.py._extract_primary_output()` to use shared utility
3. **USE** shared utility in `engine/adk_reflection.py`

## Complexity Tracking

> No violations requiring justification. Implementation follows existing patterns.

| Aspect | Assessment |
|--------|------------|
| Layer changes | 3 layers (utils, adapters, engine) - within limits |
| New files | 1 utility function + 4-5 test files |
| Pattern reuse | output_key pattern extracted to shared utility |
| Refactoring | Minor refactor of multi_agent.py (use shared utility) |
| Interface changes | None - backward compatible |
