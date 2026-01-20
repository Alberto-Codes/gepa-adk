# Implementation Plan: Standardize Critic Feedback Schema

**Branch**: `141-critic-feedback-schema` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/141-critic-feedback-schema/spec.md`

## Summary

Standardize critic feedback schema following KISS principles, enabling simple scorers to return `(score, string)` and advanced scorers to return `(score, dict)`, with internal normalization plumbing ensuring the reflection agent always receives a consistent format with `score` and `feedback_text` as required fields.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory normalization)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Python library (cross-platform)
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: N/A (pure function, negligible overhead)
**Constraints**: Must not break existing scorer implementations
**Scale/Scope**: ~3 files modified, ~50 lines of normalization logic

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applicable? | Compliance | Notes |
|-----------|-------------|------------|-------|
| **I. Hexagonal Architecture** | ✅ Yes | ✅ Pass | Normalization in adapters/ layer (TrialBuilder); no domain layer changes |
| **II. Async-First Design** | ❌ No | N/A | Normalization is a pure sync utility (no I/O) |
| **III. Protocol-Based Interfaces** | ✅ Yes | ✅ Pass | Scorer protocol unchanged; normalization is internal plumbing |
| **IV. Three-Layer Testing** | ✅ Yes | ✅ Pass | Contract tests for protocol, unit tests for normalization logic, integration tests for end-to-end |
| **V. Observability & Code Documentation** | ✅ Yes | ✅ Pass | Google-style docstrings required; structlog for any debug logging |
| **VI. Documentation Synchronization** | ✅ Yes | ⚠️ Required | Critic Agents guide (`docs/guides/critic-agents.md`) must document both feedback formats |

**Relevant ADRs**:
- ADR-000: Hexagonal Architecture - Normalization stays in adapters/
- ADR-005: Three-Layer Testing - Contract + unit + integration tests required
- ADR-010: Docstring Quality - Google-style docstrings required

**Gate Status**: ✅ PASS - All applicable principles satisfied; documentation update identified for Phase 1

## Project Structure

### Documentation (this feature)

```text
specs/141-critic-feedback-schema/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (conditional)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 3 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/              # Pure Python domain models (unchanged)
├── ports/
│   └── scorer.py        # Scorer protocol (unchanged - returns tuple[float, dict[str, Any]])
├── adapters/
│   ├── trial_builder.py # TrialBuilder.build_feedback() - PRIMARY CHANGE LOCATION
│   ├── critic_scorer.py # normalize_feedback() exists but unused - INTEGRATE
│   ├── adk_adapter.py   # Uses TrialBuilder (no direct changes)
│   └── multi_agent.py   # Uses TrialBuilder (no direct changes)
├── engine/
│   └── adk_reflection.py # Receives normalized trials (unchanged)
└── utils/               # Shared utilities (unchanged)

tests/
├── contracts/
│   └── test_reflection_example_metadata.py  # Contract tests for feedback structure
├── integration/
│   └── test_critic_reflection_metadata.py   # End-to-end reflection metadata tests
└── unit/
    └── adapters/
        └── test_trial_builder.py            # Unit tests for normalization logic

docs/guides/
└── critic-agents.md     # UPDATE: Document simple vs advanced feedback formats
```

**Structure Decision**: Single project with hexagonal architecture. Normalization logic consolidated in `adapters/trial_builder.py` as the single point of truth for trial construction. No new files required.

## Complexity Tracking

> No violations - feature is straightforward internal refactoring with no architectural deviations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
