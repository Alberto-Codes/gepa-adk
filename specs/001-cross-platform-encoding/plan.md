# Implementation Plan: Cross-Platform Encoding Support

**Branch**: `001-cross-platform-encoding` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-cross-platform-encoding/spec.md`

## Summary

Implement cross-platform encoding support for logging to prevent `UnicodeEncodeError` exceptions on Windows consoles when logging LLM-generated content. The solution adds a custom structlog processor (`EncodingSafeProcessor`) to the logging pipeline that sanitizes strings before they reach the console renderer, using smart character replacement for common Unicode characters and fallback replacement for others.

**Why custom processor?** Research confirmed structlog's built-in `UnicodeEncoder` doesn't solve this - it produces `bytes` (not sanitized `str`), causing ConsoleRenderer to output ugly `b'...'` repr strings. Other solutions (`sys.stdout.reconfigure()`, `PYTHONIOENCODING`) either modify global state or require user configuration. See [research.md](./research.md) for full analysis.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: structlog>=25.5.0 (existing), stdlib `sys` and `codecs`
**Storage**: N/A (logging infrastructure only)
**Testing**: pytest with mock console encodings
**Target Platform**: Windows (cp1252), macOS (UTF-8), Linux (UTF-8)
**Project Type**: Single Python package (hexagonal architecture)
**Performance Goals**: Negligible logging overhead (<1ms per log event)
**Constraints**: No user environment configuration required; stdlib-only for encoding logic
**Scale/Scope**: All log statements in library automatically protected

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate (Phase 0)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | Processor lives in `utils/` layer (shared utilities) |
| II. Async-First Design | ✅ PASS | Processor is sync (appropriate for logging) |
| III. Protocol-Based Interfaces | ✅ PASS | Follows structlog processor protocol (callable) |
| IV. Three-Layer Testing | ✅ PASS | Unit tests for processor, contract tests for protocol |
| V. Observability & Code Documentation | ✅ PASS | Extends ADR-008 logging pattern |
| VI. Documentation Synchronization | ✅ PASS | ADR-011 documents the decision |

### Post-Design Gate (Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | `utils/encoding.py` - no external imports |
| II. Async-First Design | ✅ PASS | Not applicable (sync processor) |
| III. Protocol-Based Interfaces | ✅ PASS | Matches structlog processor protocol |
| IV. Three-Layer Testing | ✅ PASS | See testing strategy in research.md |
| V. Observability & Code Documentation | ✅ PASS | Google-style docstrings required |
| VI. Documentation Synchronization | ✅ PASS | ADR created, no user-facing guides needed |

### Applicable ADRs

| ADR | Relevance | Alignment |
|-----|-----------|-----------|
| ADR-000 (Hexagonal) | Processor placement in layers | ✅ `utils/` is appropriate |
| ADR-006 (External Libs) | structlog is already approved | ✅ No new dependencies |
| ADR-008 (Structured Logging) | Extends processor chain | ✅ Follows pattern |
| ADR-010 (Docstring Quality) | Documentation requirements | ✅ Will comply |
| ADR-011 (NEW) | Cross-platform encoding | ✅ To be created |

## Project Structure

### Documentation (this feature)

```text
specs/001-cross-platform-encoding/
├── plan.md              # This file
├── research.md          # Phase 0 output (COMPLETE)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output (SKIPPED - see below)
└── tasks.md             # Phase 3 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── utils/
│   ├── __init__.py          # Export EncodingSafeProcessor
│   ├── encoding.py          # NEW: EncodingSafeProcessor implementation
│   └── events.py            # Existing trajectory utilities
├── adapters/
│   └── ...                  # No changes needed
└── ...

tests/
├── unit/
│   └── test_encoding.py     # NEW: Unit tests for processor
├── contract/
│   └── test_encoding_contract.py  # NEW: Protocol compliance
└── integration/
    └── test_encoding_integration.py  # NEW: Real structlog pipeline test

docs/adr/
└── ADR-011-cross-platform-encoding.md  # NEW: Decision record
```

**Structure Decision**: Single project layout maintained. New file `src/gepa_adk/utils/encoding.py` follows hexagonal architecture (utils layer, stdlib-only). Tests follow three-layer strategy from ADR-005.

## Complexity Tracking

> No violations - design follows all constitution principles.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Phase 2: Architecture Decision

**Status**: SKIPPED

**Justification**: architecture.md is not generated because this feature:
- Touches only 1 layer (`utils/`) - single file modification
- Has no external system integrations - uses existing structlog
- Has no complex data flow - simple string transformation in processor chain
- References primarily ADR-008 (structured logging) - straightforward extension

The `EncodingSafeProcessor` is a focused utility that fits cleanly into the existing structlog pipeline without requiring architectural diagrams or complex flow documentation.
