# Implementation Plan: CriticScorer

**Branch**: `009-critic-scorer` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-critic-scorer/spec.md`
**GitHub Issue**: #9

## Summary

Implement a `CriticScorer` adapter that wraps ADK critic agents to provide structured scoring with feedback, dimension scores, and actionable guidance. The scorer will implement the existing `Scorer` protocol (from #5), enabling integration with gepa-adk's evaluation and evolution workflows.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: google-adk (LlmAgent, SequentialAgent, Runner, InMemorySessionService), pydantic (output schemas)
**Storage**: N/A (session state managed by ADK's SessionService)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Python async environment (Linux/Windows/macOS)
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: Scoring latency dominated by LLM response time; no additional overhead targets
**Constraints**: Must implement existing Scorer protocol for compatibility
**Scale/Scope**: Single-call scorer interface; batch processing out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | CriticScorer lives in `adapters/` layer; imports ADK (external lib) allowed here |
| **II. Async-First Design** | ✅ PASS | `async_score()` is primary; `score()` wraps with sync execution |
| **III. Protocol-Based Interfaces** | ✅ PASS | Implements existing `Scorer` protocol from `ports/scorer.py` |
| **IV. Three-Layer Testing** | ✅ PASS | Contract, unit, and integration tests planned |
| **V. Observability & Documentation** | ✅ PASS | Google docstrings, structlog logging, proper exception handling |

**ADR Compliance**:
- ADR-000 (Hexagonal): Adapter in `adapters/`, protocol in `ports/` ✅
- ADR-001 (Async-First): All scoring methods async ✅
- ADR-002 (Protocols): Uses existing Scorer protocol ✅
- ADR-005 (Three-Layer Testing): Tests across all three layers ✅
- ADR-006 (External Library Integration): ADK isolated in adapter layer ✅
- ADR-008 (Structured Logging): Will use structlog ✅
- ADR-009 (Exception Hierarchy): Will extend EvolutionError ✅
- ADR-010 (Docstring Quality): Google-style docstrings required ✅

## Project Structure

### Documentation (this feature)

```text
specs/009-critic-scorer/
├── plan.md              # This file
├── research.md          # Phase 0 output (ADK patterns research)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (usage guide)
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (implementation tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── adapters/
│   ├── adk_adapter.py       # Existing ADK adapter
│   └── critic_scorer.py     # NEW: CriticScorer implementation
├── domain/
│   ├── exceptions.py        # Add ScoringError exception
│   └── models.py            # Existing domain models
├── ports/
│   └── scorer.py            # Existing Scorer protocol (no changes)
└── engine/                   # No changes needed

tests/
├── contracts/
│   └── test_critic_scorer_contract.py  # NEW: Protocol compliance
├── integration/
│   └── test_critic_scorer_integration.py  # NEW: Real ADK calls
└── unit/
    └── test_critic_scorer_unit.py  # NEW: Mock-based tests
```

**Structure Decision**: Single project structure with hexagonal architecture. CriticScorer is an adapter that bridges the Scorer protocol to ADK's agent/runner system.

## Complexity Tracking

No constitution violations requiring justification.
