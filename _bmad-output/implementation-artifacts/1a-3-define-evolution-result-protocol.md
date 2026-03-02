# Story 1A.3: Define EvolutionResultProtocol

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want a shared Protocol that both `EvolutionResult` and `MultiAgentEvolutionResult` structurally satisfy,
so that engine and utility code can accept either result type without type unions.

## Acceptance Criteria

1. **`EvolutionResultProtocol` defined** in `ports/evolution_result.py` declaring 5 data fields (`original_score`, `final_score`, `evolved_components`, `iteration_history`, `total_iterations`) + 2 computed properties (`improvement`, `improved`)
2. **`stop_reason` NOT included** in this Protocol definition (deferred to Epic 2, Story 2.1 when the field is added to result types)
3. **Both result types pass `isinstance()`** against the Protocol without any code changes to `EvolutionResult` or `MultiAgentEvolutionResult`
4. **Contract test** at `tests/contracts/test_evolution_result_protocol.py` includes minimum 4 tests: isinstance check for both result types, property return type verification, happy path field access, structural equivalence (both types return same types for shared fields)
5. **ADR-013** document is written at `docs/adr/ADR-013-result-type-protocol.md`
6. **Protocol exported** in `ports/__init__.py` and `__all__` updated

## Tasks / Subtasks

- [x] Task 1: Create `src/gepa_adk/ports/evolution_result.py` (AC: 1, 2)
  - [x] 1.1 Create file with module docstring following existing port patterns (see `ports/scorer.py` or `ports/stopper.py`)
  - [x] 1.2 Import `Protocol`, `runtime_checkable` from `typing`; import `IterationRecord` from `gepa_adk.domain.models`
  - [x] 1.3 Define `EvolutionResultProtocol` with `@runtime_checkable` decorator
  - [x] 1.4 Declare 5 data fields: `original_score: float`, `final_score: float`, `evolved_components: dict[str, str]`, `iteration_history: list[IterationRecord]`, `total_iterations: int`
  - [x] 1.5 Declare 2 computed `@property` methods: `improvement(self) -> float: ...` and `improved(self) -> bool: ...`
  - [x] 1.6 Add `__all__ = ["EvolutionResultProtocol"]` at file bottom
  - [x] 1.7 Verify `stop_reason` is NOT included
- [x] Task 2: Update `src/gepa_adk/ports/__init__.py` (AC: 6)
  - [x] 2.1 Add import: `from gepa_adk.ports.evolution_result import EvolutionResultProtocol`
  - [x] 2.2 Add `"EvolutionResultProtocol"` to `__all__` list
  - [x] 2.3 Add `EvolutionResultProtocol (protocol)` to module docstring `Attributes:` section
  - [x] 2.4 Add example import to module docstring `Examples:` section
  - [x] 2.5 Add cross-reference to `See Also:` section
- [x] Task 3: Create contract tests at `tests/contracts/test_evolution_result_protocol.py` (AC: 3, 4)
  - [x] 3.1 Create file with module docstring, `pytestmark = pytest.mark.contract`
  - [x] 3.2 Test 1 — isinstance positive (single-agent): `isinstance(EvolutionResult(...), EvolutionResultProtocol)` returns `True`
  - [x] 3.3 Test 2 — isinstance positive (multi-agent): `isinstance(MultiAgentEvolutionResult(...), EvolutionResultProtocol)` returns `True`
  - [x] 3.4 Test 3 — property return types: `improvement` returns `float`, `improved` returns `bool` on both types
  - [x] 3.5 Test 4 — happy path field access + type verification: construct both types, access all 5 data fields, assert correct types (`isinstance(result.original_score, float)`, etc.)
  - [x] 3.6 Test 5 — negative: class missing `improvement` property fails `isinstance()` (protocol boundary enforcement)
- [x] Task 4: Write ADR-013 at `docs/adr/ADR-013-result-type-protocol.md` and update ADR index (AC: 5)
  - [x] 4.1 Follow ADR format from existing ADRs (Status, Date, Deciders, Context, Decision, Rationale, Consequences, Alternatives)
  - [x] 4.2 Reference ADR-002 (protocol-for-interfaces) as foundation
  - [x] 4.3 Document the 5+2 Protocol surface and rationale for minimal shared contract
  - [x] 4.4 Explain `stop_reason` deferral rationale
  - [x] 4.5 Document that this is the project's first data-attribute Protocol and explain why data annotations were chosen over `@property` stubs
  - [x] 4.6 Update `docs/adr/index.md` with ADR-013 entry AND backfill missing ADR-014 entry (ADR-014 was created in Story 1A.2 but never added to index)
- [x] Task 5: Validate (AC: all)
  - [x] 5.1 Run `ruff format` + `ruff check --fix` on all new/modified files
  - [x] 5.2 Run `ty check src tests`
  - [x] 5.3 Run full `pytest` — zero failures (1375 unit+contract pass; 1 pre-existing integration failure unrelated to changes)
  - [x] 5.4 Run `docvet check` on new/modified docstrings
  - [x] 5.5 Run pre-commit hooks (`pre-commit run --all-files`)

## Dev Notes

### Protocol Specification (from Architecture Decision 1)

The protocol is exactly as defined in the architecture document:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from gepa_adk.domain.models import IterationRecord

@runtime_checkable
class EvolutionResultProtocol(Protocol):
    """Protocol for evolution result types.

    Both EvolutionResult and MultiAgentEvolutionResult satisfy this
    protocol structurally. Consumers that need the common shape program
    against this Protocol; consumers that need mode-specific data
    (valset_score, primary_agent) use the concrete type.

    This is the project's first data-attribute Protocol. Existing
    Protocols in ports/ are method-only. Data annotations were chosen
    here because the shared surface is frozen dataclass fields, not
    methods — data annotations match the structural reality exactly.
    """

    original_score: float
    final_score: float
    evolved_components: dict[str, str]
    iteration_history: list[IterationRecord]
    total_iterations: int

    @property
    def improvement(self) -> float: ...

    @property
    def improved(self) -> bool: ...
```

### Verified Structural Compatibility

Both result types already satisfy this protocol WITHOUT any code changes:

| Field / Property | `EvolutionResult` | `MultiAgentEvolutionResult` |
|---|---|---|
| `original_score: float` | Required field | Required field |
| `final_score: float` | Required field | Required field |
| `evolved_components: dict[str, str]` | Required field | Required field |
| `iteration_history: list[IterationRecord]` | Required field | Required field |
| `total_iterations: int` | Required field | Required field |
| `improvement -> float` | `@property` | `@property` |
| `improved -> bool` | `@property` | `@property` |

**Mode-specific fields NOT in protocol:**
- `EvolutionResult`: `valset_score`, `trainset_score`, `objective_scores`
- `MultiAgentEvolutionResult`: `primary_agent`, `agent_names` property

### Port Module Pattern

Follow the exact pattern of existing port files. Key conventions from `ports/scorer.py`:
- `from __future__ import annotations` at top
- `@runtime_checkable` decorator on Protocol class
- Protocol body uses `...` (Ellipsis) — NOT `pass` or `raise NotImplementedError`
- Comprehensive module docstring with `Attributes:`, `Examples:`, `See Also:` sections
- `__all__` at file bottom

### Import Boundary for Protocol File

The Protocol file is in `ports/` which may import from `domain/` + stdlib only (ADR-000). Importing `IterationRecord` from `domain.models` is permitted. Use `TYPE_CHECKING` guard if needed to avoid circular imports — but since `IterationRecord` is a pure domain model, a direct import is fine.

### Contract Test Pattern

Follow the pattern from `tests/contracts/test_scorer_protocol.py`:
- `pytestmark = pytest.mark.contract` at module level
- Tests organized in a class (e.g., `TestEvolutionResultProtocol`)
- Create actual instances of `EvolutionResult` and `MultiAgentEvolutionResult` (not mocks)
- Use `isinstance()` for runtime checkable verification — in Python 3.12, `isinstance()` checks BOTH data attributes and methods/properties via internal `hasattr()` calls, so no supplemental `hasattr()` is needed for positive tests
- Include a negative test: class missing `improvement` property should fail `isinstance()`

### Recommended Test Matrix (5 tests)

| # | Test | What it validates |
|---|------|-------------------|
| 1 | `isinstance(EvolutionResult(...), Protocol)` | Positive — single-agent type satisfies protocol |
| 2 | `isinstance(MultiAgentEvolutionResult(...), Protocol)` | Positive — multi-agent type satisfies protocol |
| 3 | `result.improvement` is `float`, `result.improved` is `bool` (both types) | Property return types |
| 4 | All 5 fields accessible with correct types on both types | Happy path field access + type verification |
| 5 | Class missing `improvement` property fails `isinstance()` | Negative — protocol boundary enforcement |

Tests 3 and 4 can be combined if the dev prefers fewer test methods — the key is that both property return types AND data field types are explicitly asserted.

To construct test instances:
```python
from gepa_adk.domain.models import EvolutionResult, MultiAgentEvolutionResult

# EvolutionResult requires: original_score, final_score, evolved_components,
#                           iteration_history, total_iterations
result = EvolutionResult(
    original_score=0.5,
    final_score=0.8,
    evolved_components={"instruction": "Be helpful"},
    iteration_history=[],
    total_iterations=3,
)

# MultiAgentEvolutionResult additionally requires: primary_agent
multi_result = MultiAgentEvolutionResult(
    original_score=0.5,
    final_score=0.8,
    evolved_components={"agent1.instruction": "Be helpful"},
    iteration_history=[],
    total_iterations=3,
    primary_agent="agent1",
)
```

### ADR-013 Content

- **Title**: Result Type Unification via Shared Protocol
- **Status**: Accepted
- **Context**: Two frozen result dataclasses (`EvolutionResult`, `MultiAgentEvolutionResult`) share 5 data fields and 2 computed properties. Engine and utility code currently must accept `EvolutionResult | MultiAgentEvolutionResult` type unions.
- **Decision**: Define `EvolutionResultProtocol` in `ports/evolution_result.py` — minimal shared contract via structural subtyping (ADR-002)
- **Novel pattern**: This is the project's first data-attribute Protocol. All 11 existing Protocols use method stubs only. Data annotations were chosen because the shared surface consists of frozen dataclass fields — data annotations match the structural reality exactly and keep the Protocol simple. `@property` stubs were considered but rejected as unnecessary indirection since the fields are plain attributes on both types.
- **Key**: `stop_reason` deferred to Story 2.1 — Protocol will be updated then
- **Alternatives**: (1) ABC base class — rejected, violates ADR-002; (2) Type union everywhere — rejected, doesn't scale to `WorkflowEvolutionResult`

### ADR Index Maintenance

`docs/adr/index.md` must be updated with the ADR-013 entry. Additionally, ADR-014 (created in Story 1A.2) was never added to the index — backfill it in the same edit. The index is a simple markdown table; add rows in numerical order matching the existing format.

### Project Structure Notes

- New file `src/gepa_adk/ports/evolution_result.py` follows the one-Protocol-per-file convention (Story 1A.1 established this pattern)
- Protocol is in `ports/` layer — imports only from `domain/` + stdlib (hexagonal boundary respected)
- No changes to `domain/models.py` — both result types already satisfy the protocol structurally
- After this story, Epic 2 Story 2.1 will add `stop_reason` to both result types AND update this Protocol

### Previous Story Learnings (from Story 1A.2)

- Pre-commit hooks are strict: yamllint, ruff, ty, pytest, docvet all enforced
- `docvet check` catches missing Examples sections, cross-references, typed Attributes in module docstrings — run after every docstring change
- Module docstrings require `Attributes:` listing `__all__` contents
- `ty check src tests` is enforced — ensure Protocol type annotations are correct
- All test functions must be inside classes, not flat
- `__all__` at file BOTTOM, after all definitions

### Git Intelligence

Recent commits show:
- `d8ba3a0` — ci(release): sync uv.lock (CI infrastructure)
- `21f2951` — refactor(adapters): reorganize into concern-based sub-packages (Story 1A.2 — predecessor)
- `f8d900e` — refactor(ports): split selector.py into one-Protocol-per-file modules (Story 1A.1 — predecessor)

Both predecessor stories were mechanical refactors. This story adds a NEW protocol (additive) rather than reorganizing existing code.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 1] — EvolutionResultProtocol specification (5 fields + 2 properties)
- [Source: _bmad-output/planning-artifacts/architecture.md#Target Directory Tree] — `ports/evolution_result.py` placement
- [Source: _bmad-output/planning-artifacts/architecture.md#ADR Registry] — ADR-013 reserved
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1A.3] — Acceptance criteria with BDD format
- [Source: _bmad-output/project-context.md] — 95 implementation rules (protocol patterns, testing standards, docstring pipeline)
- [Source: docs/adr/ADR-002-protocol-for-interfaces.md] — Structural subtyping foundation
- [Source: docs/adr/ADR-000-hexagonal-architecture.md] — Layer boundary rules
- [Source: src/gepa_adk/domain/models.py:319-399] — EvolutionResult definition (5 required + 3 optional fields, 2 properties)
- [Source: src/gepa_adk/domain/models.py:449-537] — MultiAgentEvolutionResult definition (6 required fields, 3 properties)
- [Source: src/gepa_adk/ports/__init__.py] — Current port re-exports pattern
- [Source: tests/contracts/test_scorer_protocol.py] — Contract test reference pattern

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- All 5 tasks completed successfully
- Created `EvolutionResultProtocol` with 5 data fields + 2 computed properties in `ports/evolution_result.py`
- Protocol is the project's first data-attribute protocol (all 11 existing protocols are method-only)
- Both `EvolutionResult` and `MultiAgentEvolutionResult` pass `isinstance()` without any code changes
- `stop_reason` intentionally excluded (deferred to Epic 2, Story 2.1)
- 5 contract tests created: 2 isinstance positive, 1 property return types, 1 field access + types, 1 negative boundary
- ADR-013 written documenting the decision, rationale, and novel data-attribute pattern
- ADR index updated with both ADR-013 (new) and ADR-014 (backfill from Story 1A.2)
- `ports/__init__.py` updated: import, `__all__`, Attributes, Examples, See Also sections
- All pre-commit hooks pass: ruff format, ruff check, ty check, docvet (0 findings)
- 1375 unit + contract tests pass with 0 failures
- Fixed one E501 line-too-long in module docstring See Also cross-reference

### File List

**New files (3):**
- `src/gepa_adk/ports/evolution_result.py`
- `tests/contracts/test_evolution_result_protocol.py`
- `docs/adr/ADR-013-result-type-protocol.md`

**Modified files (3):**
- `src/gepa_adk/ports/__init__.py` (import, __all__, docstring updates)
- `docs/adr/index.md` (ADR-013 entry + ADR-014 backfill)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (status update)

**Modified planning artifacts (1):**
- `_bmad-output/implementation-artifacts/1a-3-define-evolution-result-protocol.md` (this file)

### Change Log

| Change | Reason |
|--------|--------|
| Created `ports/evolution_result.py` with `EvolutionResultProtocol` | AC 1, 2 |
| Updated `ports/__init__.py` with re-export and docstring | AC 6 |
| Created 5 contract tests in `test_evolution_result_protocol.py` | AC 3, 4 |
| Written ADR-013 documenting result type unification decision | AC 5 |
| Backfilled ADR-014 in `docs/adr/index.md` | Gap from Story 1A.2 |
