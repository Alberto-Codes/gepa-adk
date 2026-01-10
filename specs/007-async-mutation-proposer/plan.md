# Implementation Plan: AsyncReflectiveMutationProposer

**Branch**: `007-async-mutation-proposer` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/007-async-mutation-proposer/spec.md`

## Summary

Implement `AsyncReflectiveMutationProposer`, a standalone proposer class that generates instruction mutations via LiteLLM reflection. The proposer takes a candidate's current instruction text and a reflective dataset containing feedback, then uses async LLM calls to propose improved instruction text. It handles empty datasets gracefully by returning `None` without making LLM calls.

**Technical Approach**: Use `litellm.acompletion()` directly for async LLM calls. Follow fail-fast error handling pattern (consistent with AsyncGEPAEngine). Implement as standalone class in engine layer, not tied to any specific adapter.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: litellm 1.80.13 (for async LLM calls)  
**Storage**: N/A (stateless proposer)  
**Testing**: pytest with pytest-asyncio, mocked litellm.acompletion()  
**Target Platform**: Linux/macOS/Windows (cross-platform)  
**Project Type**: Single package (src/gepa_adk/)  
**Performance Goals**: <10ms for empty dataset detection (no LLM call), async non-blocking for LLM calls  
**Constraints**: Handle `None` content from LLM responses gracefully  
**Scale/Scope**: One class, ~150 lines of implementation code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Hexagonal Architecture** | ✅ PASS | Proposer in engine/ layer, depends only on stdlib + litellm. No adapter imports. |
| **II. Async-First Design** | ✅ PASS | `propose()` is `async def`, uses `await litellm.acompletion()`. |
| **III. Protocol-Based Interfaces** | ✅ PASS | Proposer is standalone class; could define `MutationProposer` protocol if needed later. |
| **IV. Three-Layer Testing** | ✅ PASS | Will have contract tests (behavior guarantees), unit tests (mocked LLM), integration tests (@pytest.mark.slow). |
| **V. Observability & Documentation** | ✅ PASS | Google docstrings, structlog for logging, exceptions propagate with context. |

**Gate Status**: All principles PASS. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/007-async-mutation-proposer/
├── plan.md              # This file (completed)
├── research.md          # Phase 0 output (completed)
├── data-model.md        # Phase 1 output (completed)
├── quickstart.md        # Phase 1 output (completed)
├── contracts/           # Phase 1 output (completed)
│   └── proposer-api.md  # API contract
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── exceptions.py    # Existing: EvolutionError hierarchy
│   └── models.py        # Existing: Candidate, EvolutionConfig
├── engine/
│   ├── __init__.py
│   ├── async_engine.py  # Existing: AsyncGEPAEngine (will integrate)
│   └── proposer.py      # NEW: AsyncReflectiveMutationProposer
├── ports/
│   └── adapter.py       # Existing: AsyncGEPAAdapter protocol
└── utils/

tests/
├── contracts/
│   └── test_proposer_contracts.py  # NEW: Behavioral guarantees
├── integration/
│   └── engine/
│       └── test_proposer_integration.py  # NEW: Real LiteLLM calls
└── unit/
    └── engine/
        └── test_proposer.py  # NEW: Mocked LiteLLM
```

**Structure Decision**: Following existing hexagonal architecture. Proposer lives in `engine/` layer (orchestration logic). It's a standalone utility class that adapters or engine can use.

## Complexity Tracking

> **All Constitution gates PASS. No violations requiring justification.**

| Item | Notes |
|------|-------|
| Dependencies | litellm 1.80.13 - already added to project |
| External Imports | litellm in engine/proposer.py only (acceptable per ADR-006) |
| Async Pattern | Standard async/await, no complex semaphore patterns needed |
| Error Handling | Fail-fast propagation (consistent with existing engine) |

## Phase Summary

| Phase | Artifact | Status |
|-------|----------|--------|
| Phase 0 | research.md | ✅ Complete |
| Phase 1 | data-model.md | ✅ Complete |
| Phase 1 | contracts/proposer-api.md | ✅ Complete |
| Phase 1 | quickstart.md | ✅ Complete |
| Phase 2 | tasks.md | ⏳ Next (via /speckit.tasks) |

## Key Design Decisions

1. **Standalone class**: Not a protocol/interface - concrete implementation that adapters can compose
2. **litellm direct**: Use litellm.acompletion() directly, not wrapped in google-adk
3. **Fail-fast errors**: LiteLLM exceptions propagate unchanged to caller
4. **None for empty**: Return None (not empty dict) when no proposals possible
5. **Handle None content**: LLM Message.content can be None - return original text in that case
