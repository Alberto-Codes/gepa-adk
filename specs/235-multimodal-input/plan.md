# Implementation Plan: Multimodal Input Support

**Branch**: `235-multimodal-input` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/235-multimodal-input/spec.md`

## Summary

Enable trainset/valset examples to include video files alongside text prompts. Videos are converted to inline data blobs and combined with text into multimodal content for agent execution. Full backward compatibility is maintained for text-only trainsets.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk >= 1.22.0 (Part, Content types), structlog >= 25.5.0, pathlib (stdlib), mimetypes (stdlib)
**Storage**: N/A (local filesystem video files, no persistent storage)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux/Windows/macOS (CLI tool)
**Project Type**: Single project (hexagonal architecture)
**Performance Goals**: Video loading should not significantly delay evolution iterations
**Constraints**: 2GB max file size (Gemini API constraint), memory-efficient loading
**Scale/Scope**: Support up to 5 videos per example, standard video sizes under 500MB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | PASS | New VideoBlobService in adapters/ behind port interface; executor update in adapters/ |
| **II. Async-First Design** | PASS | Video loading will be async; integrates with existing async flow |
| **III. Protocol-Based Interfaces** | PASS | New `VideoBlobServiceProtocol` in ports/ |
| **IV. Three-Layer Testing** | PASS | Contract tests for protocol, unit tests with mocks, integration tests with real files |
| **V. Observability & Code Documentation** | PASS | Structlog for video loading events, Google-style docstrings |
| **VI. Documentation Synchronization** | PASS | Update single-agent guide, add video evolution example |

**ADRs Applicable**:
- ADR-000: Hexagonal Architecture (service layer placement)
- ADR-001: Async-First Architecture (async video loading)
- ADR-002: Protocol for Interfaces (VideoBlobServiceProtocol)
- ADR-005: Three-Layer Testing (test structure)
- ADR-006: External Library Integration (google.genai.types imports in adapters only)
- ADR-008: Structured Logging (video loading observability)
- ADR-009: Exception Hierarchy (video validation errors)

## Project Structure

### Documentation (this feature)

```text
specs/235-multimodal-input/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
├── architecture.md      # Phase 2 output
└── tasks.md             # Phase 3 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   ├── exceptions.py    # Add VideoValidationError
│   └── models.py        # No changes (trainset is dict, not typed)
├── ports/
│   └── video_blob_service.py  # NEW: VideoBlobServiceProtocol
├── adapters/
│   ├── video_blob_service.py  # NEW: VideoBlobService implementation
│   ├── adk_adapter.py         # MODIFY: Content preparation in _run_single_example
│   └── agent_executor.py      # MODIFY: Accept str | Content input
├── api.py                     # MODIFY: Update _validate_dataset
└── utils/                     # No changes

tests/
├── contracts/
│   └── test_video_blob_contract.py  # NEW: Protocol compliance
├── unit/
│   └── adapters/
│       ├── test_video_blob_service.py  # NEW: Unit tests
│       └── test_adk_adapter_multimodal.py  # NEW: Multimodal example tests
└── integration/
    └── test_multimodal_evolution.py  # NEW: End-to-end with videos

docs/
├── guides/
│   └── single-agent.md  # MODIFY: Add multimodal section
examples/
└── video_evolution.py   # NEW: Video transcript evolution example
```

**Structure Decision**: Follows existing hexagonal architecture with ports/adapters separation. New service added in adapters/ with corresponding port protocol.

## Complexity Tracking

> No constitution violations - standard pattern following existing architecture.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
