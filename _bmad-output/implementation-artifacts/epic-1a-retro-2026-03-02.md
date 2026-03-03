# Epic 1A Retrospective: Structural Refactoring

**Date:** 2026-03-02
**Facilitator:** Bob (Scrum Master)
**Participants:** Alice (Product Owner), Charlie (Senior Dev), Dana (QA Engineer), Elena (Junior Dev), Alberto-Codes (Project Lead)

## Epic Summary

| Metric | Value |
|--------|-------|
| Epic | 1A: Structural Refactoring |
| Stories | 3/3 completed (100%) |
| Blockers | 0 |
| Production Incidents | 0 |
| Test Growth | baseline -> 1788 tests |
| Technical Debt Added | 0 (reduced existing debt) |

### Stories Delivered

1. **1A.1 — Split Selector Protocol + Light Up Pre-Commit**: Established pre-commit hooks (ruff, ty, pytest contracts, docvet), split `selector.py` into 3 one-Protocol-per-file modules, added `py.typed` marker. Absorbed scope from Story 1B.3 (developer local tooling).
2. **1A.2 — Reorganize Adapters into Sub-Packages**: Moved 11 adapter modules into 7 concern-based sub-packages, created 35 deprecation tests for 33 re-exported symbols, wrote ADR-014. Fixed 51 docvet findings and pre-existing ty/yamllint issues.
3. **1A.3 — Define EvolutionResultProtocol**: Created project's first data-attribute Protocol (5 data fields + 2 computed properties), wrote 5 contract tests, authored ADR-013. Piggybacked test infrastructure improvements: shared mock compliance tests, Gemini probe fix, API markers, executor wiring tests.

## What Went Well

### Architecture Spec Precision
The planning artifacts (architecture.md, epics.md) were detailed enough — down to exact symbol re-export maps and target directory trees — that implementation was mechanical. Zero ambiguity-related blockers across all 3 stories.

### Quality Gates from Day One
Absorbing Story 1B.3 into 1A.1 lit up pre-commit hooks from the first story. Every subsequent story was held to ruff, ty, pytest contracts, and docvet standards. This established a quality floor that prevented regression.

### Contract Testing Pattern
The `@runtime_checkable` Protocol + `isinstance()` contract testing pattern proved elegant and valuable. Story 1A.3's `EvolutionResultProtocol` was verified at the structural level, catching potential field renames or removals. The shared mock compliance tests guard 638 mock references across 27 test files.

### Test Infrastructure Growth
Test suite grew to 1788 tests by epic completion. Out-of-scope improvements (mock compliance tests, executor wiring tests) strengthened the test foundation beyond story requirements.

### Multi-Layer Code Review
Adversarial code review + Copilot automated review caught complementary issues. Manual review found logic gaps (missing timeout, convention violations, boundary test gaps). Copilot found structural concerns (eager network probes).

### Incremental Codebase Health
Structural refactoring surfaced and fixed pre-existing issues: unused type-ignore comments (5 test files), yamllint trailing whitespace, stale docstring cross-references (10 across 4 files).

## Challenges

### Docvet Tool Friction
Story 1A.2 required resolving 51 docvet findings across staged files. The `Note:` section boundary issue (not in `_SECTION_PATTERN`) required docstring reordering as a workaround. This is an upstream tool limitation that slows every story touching docstrings.

### Spec-Reality Drift on Details
The Story 1A.2 spec claimed 40 symbols for re-export but the actual count was 33. Small discrepancies like this create confusion during implementation and review. Concrete claims in story specs should be verified against the actual codebase.

### Out-of-Scope Expansion
2 of 3 stories included out-of-scope improvements that expanded the PR diff and review burden. While individually valuable (especially test infrastructure), this pattern needs explicit documentation and boundary management.

### Test Probe Reliability
The Gemini availability probe originally checked only for env var presence, not actual API connectivity. Tests that should have been skipped were failing at runtime. Fixed with a connectivity probe + lazy evaluation, but this was only discovered during Story 1A.3.

## Key Insights

1. **Structural refactoring doubles as a codebase health audit** — Pre-existing issues surface naturally when touching many files.
2. **"Previous Story Learnings" sections create valuable continuity** — Story 1A.3 explicitly documented lessons from 1A.2, preventing repeated mistakes.
3. **Data-attribute Protocols are a natural pattern** — For frozen dataclass fields, data annotations match the structural reality better than `@property` stubs.
4. **Lazy evaluation prevents unintended side effects** — Network probes in conftest should only fire when matching test markers are present.
5. **Multi-layer review is better than single-layer** — Adversarial human review and automated review have different strengths.

## Action Items

### Process Improvements

| # | Action | Owner | Success Criteria |
|---|--------|-------|------------------|
| 1 | Add "Previous Story Learnings" section to story creation workflow | Bob (SM) | Story 1B.1 contains a learnings section referencing 1A patterns |
| 2 | Establish scope boundary convention for out-of-scope improvements | Bob (SM) | Story template includes explicit "Out of Scope Piggybacked" section |
| 3 | Verify spec accuracy during story creation | Bob (SM) | Concrete claims (counts, file lists) verified against actual codebase |

### Team Agreements

- Piggybacking out-of-scope improvements is acceptable when they strengthen test infrastructure, but they MUST be documented separately and called out in the PR description
- Adversarial code review + automated PR review (Copilot) is the standard review pattern
- Pre-commit hooks remain the first quality gate — new CI checks should be considered for pre-commit if they run fast enough

## Next Epic: 1B Preparation

### Dependencies on Epic 1A

- Boundary enforcement scripts (1B.1) will validate the adapter sub-package structure from 1A.2
- Protocol coverage check (1B.1) will validate EvolutionResultProtocol from 1A.3
- ty cleanup (1B.3) will fix diagnostics first noticed during 1A.2

### Preparation Tasks

| Task | Owner |
|------|-------|
| Run `ty check src tests` and document current diagnostics for 1B.3 scoping | Charlie (Dev) |
| Install `google-adk==1.20.0` in isolation and capture failure inventory for 1B.2 | Charlie (Dev) |

### Risk Assessment

- **1B.1** (Boundary Scripts): Low risk — well-defined scope, grep/script-based
- **1B.2** (ADK 1.20.0 Compat): Medium risk — discovery-heavy, unknown failure count
- **1B.3** (ty Cleanup): Low risk — 9 known diagnostics, scoped

### Readiness Assessment

| Area | Status |
|------|--------|
| Testing & Quality | 1788 tests pass, pre-commit green |
| Technical Health | Codebase cleaner post-epic |
| Unresolved Blockers | None |
| Epic Update Needed | No — 1B plan is sound |

**Epic 1A is fully complete. No blockers to starting Epic 1B.**

---

*Generated by BMAD Retrospective Workflow on 2026-03-02*
