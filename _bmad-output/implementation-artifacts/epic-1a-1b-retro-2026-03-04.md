# Epic 1A + 1B Combined Retrospective: Structural Refactoring & Quality Infrastructure

**Date:** 2026-03-04
**Facilitator:** Bob (Scrum Master)
**Participants:** Winston (Architect), Amelia (Developer), Murat (Test Architect), Paige (Tech Writer), Alberto-Codes (Project Lead)

## Epic Summary

| Metric | Epic 1A | Epic 1B | Combined |
|--------|---------|---------|----------|
| Epic | Structural Refactoring | Quality Infrastructure & ADK Compatibility | Foundation Phase |
| Stories | 3/3 completed (100%) | 6/6 completed (100%) | 9/9 (100%) |
| Blockers | 0 | 0 | 0 |
| Production Incidents | 0 | 0 | 0 |
| Test Count (start / end) | baseline / 1788 | 1788 / 1855 | +1855 total |
| Coverage | ~88% | ~89.3% | Maintained >85% |
| Tech Debt | Reduced existing | Reduced further | Net reduction |
| Version | pre-release | v1.0.0 + v1.0.1 | Stable release |

### Stories Delivered

**Epic 1A — Structural Refactoring:**

1. **1A.1 — Split Selector Protocol + Light Up Pre-Commit**: Established pre-commit hooks (ruff, ty, pytest contracts, docvet), split `selector.py` into 3 one-Protocol-per-file modules, added `py.typed` marker. Absorbed scope from original 1B.3 (developer local tooling).
2. **1A.2 — Reorganize Adapters into Sub-Packages**: Moved 11 adapter modules into 7 concern-based sub-packages, created 35 deprecation tests for 33 re-exported symbols, wrote ADR-014. Fixed 51 docvet findings.
3. **1A.3 — Define EvolutionResultProtocol**: Created project's first data-attribute Protocol (5 data fields + 2 computed properties), wrote 5 contract tests, authored ADR-013. Piggybacked test infrastructure improvements.

**Epic 1B — Quality Infrastructure & ADK Compatibility:**

1. **1B.1 — Architectural Boundary Enforcement Scripts**: Created `check_boundaries.sh` and `check_protocol_coverage.py`, added `boundaries.yml` CI workflow. Discovered 7 pre-existing boundary violations.
2. **1B.2 — ADK 1.20.0 Compatibility Layer**: Discovery found zero API differences — no shims needed. Lowered dependency floor to `>=1.20.0`, added CI version matrix (1.20.0 + latest), created 16 import contract tests. Piggybacked: activated 14 dormant EvaluationPolicyProtocol contract tests.
3. **1B.3 — Clean Up ty Type-Check Diagnostics**: Removed 3 stale ty overrides, replaced 13 `# type: ignore` comments (6 fixed with type-narrowing, 7 converted to `# ty: ignore[rule]`). Updated project-context.md. Piggybacked: 28 new unit tests for untested methods.
4. **1B.4 — Fix Pre-Existing Boundary Violations**: Resolved all 7 violations — moved `reflection_agents.py` to `adapters/agents/`, moved `config_utils.py` to `adapters/config_adapter.py`, simplified `adk_reflection.py`, hardened CI boundary gate to blocking. 35+ files changed.
5. **1B.5 — Eliminate ty Type-Narrowing Workarounds**: Eliminated all 7 `ty: ignore` from src/ — redefined `ReflectionFn` to 3-param, added `@overload` with `Literal[True]`/`Literal[False]`, deleted dead `event.session` code, removed dead `session_service` and `output_field` params. Resolved tech debt td-001 and td-002.
6. **1B.6 — Migrate Trunk-Based Main Release 1.0.0**: Migrated from `develop` to `main` as default branch. Updated all CI workflows, dependabot, release-please, documentation, and tooling configs. Released v1.0.0.

## Previous Retro (Epic 1A) Action Item Follow-Through

| # | Action Item | Status | Evidence |
|---|------------|--------|----------|
| 1 | Add "Previous Story Learnings" section to story creation | ✅ Completed | Every 1B story (1B.1 through 1B.6) includes the section, each referencing the prior story |
| 2 | Establish scope boundary convention for out-of-scope improvements | ✅ Completed | 1B.2 and 1B.3 documented piggybacked improvements in Completion Notes |
| 3 | Verify spec accuracy during story creation | ⏳ Partial | 1B.3 found spec-reality drift (ty behavior). Stories added "re-verify before starting" mitigation |

## What Went Well

### Discovery-First Philosophy

Stories 1B.2 and 1B.3 both expected significant work but discovery gates found less than scoped. 1B.2 expected compatibility shims but found zero API differences between ADK 1.20.0 and 1.22.0. 1B.3 expected 9 ty diagnostics but all were resolved by tool upgrades. The decision gates prevented two stories from doing unnecessary work.

### Continuity Across Stories

The "Previous Story Learnings" section, adopted from the Epic 1A retro, created a knowledge chain across all 6 stories in 1B. Patterns propagated: pre-commit strictness, docvet quirks, `__all__` placement, `create_mock_adapter()` factory, "line numbers are advisory." Each discovered once, never repeated.

### Party Mode Consensus for Architecture

Stories 1B.4, 1B.5, and 1B.6 used full-panel reviews for architectural decisions. Key outcomes: reflection_agents relocation strategy, dead code deletion vs casting, `refactor` vs `BREAKING CHANGE` commit type, release strategy for 1.0.0. Each decision well-documented with rationale.

### Multi-Layer Review Process

Adversarial code review + Copilot automated review + party mode discussion. Each layer caught different issues. Copilot found structural concerns (stale class names, docstring precision). Adversarial review found file list mismatches and stale docstrings. Party mode refined architectural decisions.

### Quality Infrastructure Compounding

Each story built on previous infrastructure: 1B.1 created boundary scripts -> 1B.4 used them to fix violations -> 1B.4 hardened CI to blocking. 1B.3 cleaned ty config -> 1B.5 eliminated remaining workarounds. Compounding effect made each successive story safer.

### Zero Regressions

9 stories, 35+ source files touched in the largest stories, 0 production incidents, 0 test regressions. The pre-commit hooks + 85% coverage floor + boundary enforcement created a quality floor that held through heavy refactoring.

## Challenges

### Spec-Reality Drift on Technical Details

1A.2 spec claimed 40 symbols but actual was 33. 1B.3 spec said ty ignores `# type: ignore` but ty 0.0.18 does recognize them. Story specs with concrete technical claims need verification against the actual codebase at creation time.

### Large Blast Radius Stories

1B.4 touched 35+ files, 1B.5 touched 22 files. Both required updating dozens of test call sites. The mechanical nature (find-and-replace) kept risk low, but review burden was high.

### Upstream Tool Limitations

Docvet's `Note:` section boundary issue persisted from 1A.2 through the entire epic. Team worked around it but it added friction to every story touching docstrings.

### Backlog Scope Drift

Stories consistently found different scope than planned because prior stories changed the codebase. Line numbers shifted, violations were partially resolved, behavior changed. The "re-verify before starting" mitigation became standard but adds startup cost.

### Documentation Impact Not Systematically Tracked

Several stories required documentation updates (docstrings, guides, examples) that were caught during review rather than planned during story creation. Documentation impact should be analyzed at story creation time, not discovered during code review.

## Key Insights

1. **Decision gates prevent unnecessary work** — 1B.2 and 1B.3 both used "discover first, then decide scope" gates that cut work dramatically.
2. **Structural refactoring doubles as a codebase health audit** — Touching many files naturally surfaces pre-existing issues (dead code, stale comments, dormant tests).
3. **CI gates compound over time** — Each new gate builds on the last. The 1B.4 boundary hardening would have been risky without the 1B.1 scripts and 1B.2/1B.3 cleanups.
4. **"Previous Story Learnings" is the most impactful process improvement** — Created a learning chain that prevented repeated mistakes across 6 stories.
5. **Party mode consensus is most valuable for architectural decisions** — Routine implementation doesn't need it, but move-vs-refactor-vs-delete decisions benefit from multi-perspective review.
6. **Two-phase execution models work for infrastructure stories** — 1B.6 used Phase 1 (config PR) + Phase 2 (manual ops) to avoid chicken-and-egg problems.
7. **Testing improvements piggyback naturally on refactoring** — 1B.2 activated 14 dormant tests, 1B.3 added 28 new tests. Cross-cutting testing maturity should be an explicit part of every story.

## Tech Debt Status

| Item | Source | Status | Notes |
|------|--------|--------|-------|
| td-001: dead `session_service` param | 1B.4 review | ✅ Resolved in 1B.5 | |
| td-002: dead `output_field` param | 1B.4 review | ✅ Resolved in 1B.5 | |
| Nullable trajectories (`list \| None`) | 1B.5 scoping | Deferred | Explicit out-of-scope decision; doesn't produce ty errors |
| `ProposerProtocol` vs concrete type | 1B.4 | Deferred | `Any` used; future `MutationProposerProtocol` possible |
| Docvet `Note:` section boundary | 1A.2 | Open (upstream) | Workaround: reorder docstring sections |

## Action Items

### Process Improvements

| # | Action | Owner | Success Criteria |
|---|--------|-------|------------------|
| 1 | Verify spec technical claims against actual codebase at story creation | Bob (SM) | Story specs include actual counts/behavior verified against codebase |
| 2 | Add decision gates to discovery-heavy stories | Bob (SM) | Stories with unknowns have explicit "Decision Gate" checkpoints |
| 3 | Continue "Previous Story Learnings" practice | Bob (SM) | Every Epic 2 story includes the section |
| 4 | Docs impact analysis in create-story and code-review workflows | Alberto-Codes | ✅ Done — both workflows updated with docs impact sections |
| 5 | TEA testing maturity item in create-story workflow | Alberto-Codes | ✅ Done — cross-cutting `[TEA]` optional task in every story |

### Team Agreements

- **Discovery-first for unknowns**: Any story with "unknown" complexity gets a discovery task with a decision gate before implementation tasks
- **Party mode for architecture, not routine**: Use full-panel consensus for move/delete/refactor decisions; skip for mechanical changes
- **Multi-layer review continues**: Adversarial + automated + party mode (when needed) is the standard
- **Pre-commit hooks remain the first quality gate**: All CI checks that run < 5s are candidates for pre-commit
- **Piggybacking is acceptable with documentation**: Out-of-scope improvements must be documented in Completion Notes and called out in PR descriptions
- **Documentation impact is mandatory analysis**: Every story must have a "Documentation Impact" section (even if "No impact — confirmed")
- **Testing maturity is cross-cutting**: TEA identifies one small, high-risk testing improvement per story regardless of feature scope

## Next Epic: Epic 2 Preparation

### Epic 2 Overview

**Single-Agent Evolution** — 9 stories focused on evolution result quality: StopReason enum, serialization, display enhancements, graceful interrupt, pre-flight validation, sync wrapper, seed determinism, mutation rationale capture, credential redaction.

### Dependencies on Epics 1A/1B

| Dependency | Source | Status |
|------------|--------|--------|
| `EvolutionResultProtocol` | Story 1A.3 | ✅ Complete |
| Hexagonal boundaries enforced | Story 1B.4 | ✅ Blocking CI gate |
| ty clean codebase | Story 1B.5 | ✅ Zero ignores in src/ |
| Trunk-based on main | Story 1B.6 | ✅ v1.0.0 released |
| ADK 1.20.0 compat matrix | Story 1B.2 | ✅ CI runs both versions |

All prerequisites complete and stable. No blockers to starting Epic 2.

### Risk Assessment for Epic 2

| Story | Risk | Notes |
|-------|------|-------|
| 2.1 (StopReason + Schema Version) | Low | Domain model additions, well-scoped |
| 2.2 (Result Serialization) | Low | stdlib-only, test fixture based |
| 2.3 (Display Enhancements) | Low | Presentation layer, no core changes |
| 2.4 (Graceful Interrupt) | Medium | Async signal handling, KeyboardInterrupt in event loops |
| 2.5 (Pre-Flight Validation) | Low | Local-only checks, no network calls |
| 2.6 (Sync Wrapper + API Polish) | Medium | Breaking change to signatures (keyword-only separator) |
| 2.7 (Seed Determinism) | Medium | Threading RNG through all stochastic components |
| 2.8 (Mutation Rationale) | Low | Optional field addition, backward compatible |
| 2.9 (Credential Redaction) | Low | Default change, backward compatible via explicit override |

### Preparation Tasks

| Task | Notes |
|------|-------|
| Read `EvolutionResult` and `MultiAgentEvolutionResult` current state | Story 2.1 depends on these dataclasses |
| Verify ADR-015 doesn't exist yet | Story 2.1 creates it |
| Check `evolve_sync()` current implementation | Story 2.6 modifies it |
| Review `TrajectoryConfig` defaults | Story 2.9 changes them |
| Verify `EvolutionResultProtocol` includes all fields Story 2.1 needs to add | Protocol may need updating |

### Readiness Assessment

| Area | Status |
|------|--------|
| Testing & Quality | 1855 tests pass, pre-commit green, 89%+ coverage |
| Technical Health | Zero ty ignores, zero boundary violations, clean CI |
| Unresolved Blockers | None |
| Epic Update Needed | No — Epic 2 plan is sound |

**Epics 1A and 1B are fully complete. v1.0.0 released. No blockers to starting Epic 2.**

---

*Generated by BMAD Retrospective Workflow on 2026-03-04*
