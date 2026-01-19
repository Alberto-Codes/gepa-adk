# Implementation Plan: Output Schema Evolution

**Branch**: `123-output-schema-evolution` | **Date**: 2026-01-18 | **Spec**: [./spec.md](./spec.md)
**Input**: Feature specification from `/specs/123-output-schema-evolution/spec.md`

## Summary

Enable evolution of Pydantic output schemas as components within the existing gepa-adk architecture. Add three utilities (serialize, validate, deserialize) to the `utils/` layer. The existing component system is already generic and requires **no modifications** to domain models or the evolution engine.

**Key Approach**:
- Serialize via `inspect.getsource()` (Python source code, not JSON Schema)
- Validate via `ast.parse()` + controlled `exec()` for security
- Integrate validation into acceptance flow to reject invalid proposals

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: pydantic (existing), structlog (existing), ast (stdlib), inspect (stdlib)
**Storage**: N/A (in-memory evolution)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Cross-platform (Linux, macOS, Windows)
**Project Type**: Single project - Python library
**Performance Goals**: Validation <10ms per schema, no blocking I/O
**Constraints**: Self-contained schemas only (no external imports), security via AST validation
**Scale/Scope**: Single utility module, ~200-300 lines of code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Hexagonal Architecture ✅

| Requirement | Status | Evidence |
|-------------|--------|----------|
| domain/ has no external imports | ✅ | No domain changes; SchemaValidationError already exists |
| ports/ defines protocols | ✅ | No new protocols needed |
| adapters/ contains external libs | ✅ | No adapter changes |
| engine/ depends on ports only | ✅ | Engine calls utils/, not adapters/ |
| utils/ has minimal external deps | ✅ | New module uses stdlib (ast, inspect) + pydantic |

### II. Async-First Design ✅

| Requirement | Status | Evidence |
|-------------|--------|----------|
| I/O-bound operations async | ✅ | Schema utilities are CPU-bound, no I/O |
| No internal sync/async bridging | ✅ | Pure synchronous utilities |

### III. Protocol-Based Interfaces ✅

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Uses typing.Protocol | ✅ | No new protocols needed |

### IV. Three-Layer Testing ✅

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Contract tests | ✅ | `contracts/schema_utils_contract.py` created |
| Unit tests | ⏳ | To be created in `tests/unit/utils/` |
| Integration tests | ⏳ | To be created in `tests/integration/` |

### V. Observability & Documentation ✅

| Requirement | Status | Evidence |
|-------------|--------|----------|
| structlog usage | ✅ | Will use existing logger pattern |
| Google-style docstrings | ✅ | Will follow existing conventions |
| Exception with cause | ✅ | SchemaValidationError already has cause |

### VI. Documentation Synchronization ✅

| Requirement | Status | Evidence |
|-------------|--------|----------|
| docs/ update needed | ✅ | Will update guides/single-agent.md |
| examples/ update needed | ✅ | Will add schema evolution example |

## Project Structure

### Documentation (this feature)

```text
specs/123-output-schema-evolution/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Data structures
├── quickstart.md        # Phase 1: Usage guide
├── contracts/           # Phase 1: Contract tests
│   └── schema_utils_contract.py
├── architecture.md      # Phase 2: Architecture diagrams
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 3: Implementation tasks (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/gepa_adk/
├── utils/
│   ├── schema_utils.py      # NEW: serialize, validate, deserialize
│   ├── events.py            # Existing
│   └── ...
├── domain/
│   └── exceptions.py        # EXTEND: SchemaValidationError fields
├── engine/
│   └── async_engine.py      # HOOK: Call validation before accept
└── ...

tests/
├── contracts/
│   └── test_schema_utils_contract.py    # NEW
├── unit/
│   └── utils/
│       └── test_schema_utils.py         # NEW
└── integration/
    └── test_output_schema_evolution.py  # NEW
```

**Structure Decision**: Single project structure following existing hexagonal architecture. New utilities in `utils/` layer with integration hook in `engine/`.

## Complexity Tracking

> No violations - feature fits within existing architecture.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Implementation Phases

### Phase 0: Research ✅ Complete

See [research.md](./research.md) for detailed findings:
- Serialization: `inspect.getsource()` chosen over JSON Schema
- Validation: `ast.parse()` + controlled `exec()` for security
- Integration: Existing component system is fully generic

### Phase 1: Design ✅ Complete

- [data-model.md](./data-model.md): SchemaValidationResult, allowed namespace
- [contracts/](./contracts/): Contract tests for schema_utils module
- [quickstart.md](./quickstart.md): Usage guide for developers

### Phase 2: Architecture ✅ Complete

See [architecture.md](./architecture.md) for:
- Component diagram showing new schema_utils module
- Sequence diagrams for evolution and validation flows
- Hexagonal architecture alignment

### Phase 3: Tasks (Next Step)

Run `/speckit.tasks` to generate implementation tasks from this plan.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/gepa_adk/utils/schema_utils.py` | CREATE | Serialize, validate, deserialize functions |
| `src/gepa_adk/domain/exceptions.py` | MODIFY | Add fields to SchemaValidationError |
| `src/gepa_adk/engine/async_engine.py` | MODIFY | Integration hook for validation |
| `tests/contracts/test_schema_utils_contract.py` | CREATE | Contract tests |
| `tests/unit/utils/test_schema_utils.py` | CREATE | Unit tests |
| `tests/integration/test_output_schema_evolution.py` | CREATE | Integration tests |
| `docs/guides/single-agent.md` | MODIFY | Add output_schema evolution section |
| `docs/reference/glossary.md` | MODIFY | Add schema evolution terminology |
| `examples/schema_evolution_example.py` | CREATE | Working example |

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Code execution via exec() | Security vulnerability | AST validation + controlled namespace whitelist |
| LLM proposes invalid schemas | Evolution stalls | Validation rejects; engine continues with previous best |
| inspect.getsource() fails for dynamic classes | Serialization fails | Document requirement for .py-defined classes |
| Schema name collisions during deserialization | Namespace pollution | Unique namespace per validation call |

## Success Criteria Mapping

| Spec Criterion | Implementation |
|----------------|----------------|
| SC-001: Evolve with components=["output_schema"] | Engine accepts "output_schema" as component name |
| SC-002: 100% invalid schemas rejected | validate_schema_text() with comprehensive rules |
| SC-003: Deserialized schemas work | deserialize_schema() returns usable BaseModel |
| SC-004: Measurable improvement | Same metrics as instruction evolution |
| SC-005: Evolution completes without errors | Validation integration prevents invalid proposals |
| SC-006: Evolve both instruction and output_schema | Existing component selector supports multiple |
