---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
---

# gepa-adk - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for gepa-adk, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

**Single-Agent Evolution**

FR1 [MVP]: A developer can evolve a single agent's definition across all enabled surfaces (instruction, output schema, generation config) by providing the agent, a training set, and a scorer.
FR2 [MVP]: A developer receives a structured evolution result containing the evolved agent definition, generation history, and summary statistics.
FR3 [MVP]: A developer can view a diff between the original and evolved agent definition, showing what changed across each component.
FR4 [MVP]: A developer can view per-component mutation attribution in the evolution result, identifying which surface produced the highest-impact change.
FR5 [MVP]: The system identifies which evolvable surface produced the highest-impact mutation for a given evolution run.
FR6 [MVP]: A developer can use each API entry point independently — evolve() requires no knowledge of evolve_group() or evolve_workflow(), and each is usable as a standalone capability.
FR7 [Growth]: A developer can run evolution with specific surfaces disabled (e.g., instruction-only mode) to compare multi-surface vs. single-surface outcomes on the same agent.

**Multi-Agent & Workflow Evolution**

FR8 [MVP]: A developer can evolve a group of agents simultaneously by providing individual agent scorers and an aggregate pipeline scorer.
FR9 [MVP]: The system applies round-robin agent selection across generations during group evolution, ensuring each agent is a mutation target.
FR10 [MVP]: The system's final evolution result does not include agents whose scores are below their pre-evolution baseline.
FR11 [MVP]: A developer can view per-agent score breakdown during and after group evolution.
FR12 [MVP]: A developer can evolve a workflow structure while preserving the topology of SequentialAgent, LoopAgent, and ParallelAgent compositions.
FR13 [MVP]: The system supports google-adk versions from 1.20.0 through latest, including enterprise-deployed versions. A compatibility layer abstracts API differences across ADK versions, and CI tests against both adk==1.20.0 (minimum) and adk-latest.
FR14 [Growth]: A developer can run evolution across a fleet of agents using batch orchestration.

**Evolution Control & Extensibility**

FR15 [MVP]: A developer can implement a custom scorer by conforming to the Scorer Protocol.
FR16 [MVP]: A developer can use critic agents (SimpleCriticOutput, CriticOutput) for structured multi-dimensional evaluation.
FR17 [MVP]: A developer can configure evolution termination using stoppers (budget limit, plateau detection, generation limit).
FR18 [MVP]: A developer can choose between reflection agent implementations (LiteLLM-based, ADK-based) for mutation generation.
FR19 [MVP]: A developer can customize the reflection prompt to control mutation behavior.
FR20 [MVP]: The system applies component-aware reflection specialization, producing mutations tailored to each surface type (instruction vs. schema vs. config).
FR21 [MVP]: A contributor can add a new evolvable surface by implementing the ComponentHandler Protocol and registering it — without modifying the core evolution engine.
FR22 [MVP]: A contributor can customize agent creation and cloning by implementing the AgentProviderProtocol.
FR23 [Growth]: A contributor can add model selection as an evolvable surface via the ComponentHandler Protocol.
FR24 [Growth]: A developer can estimate evolution cost before execution — within 20% of actual cost for stable workloads — by providing population parameters and per-token pricing configuration.
FR25 [Vision]: A contributor can implement an adapter for a non-ADK agent framework via a framework adapter Protocol.

**Observability & Audit**

FR26 [MVP]: The system emits structured log events for every evolution decision (mutation proposed, mutation accepted/rejected, score change, generation summary).
FR27 [MVP]: The system captures every evolutionary event as an ADK session event, producing an audit trail queryable via session persistence.
FR28 [MVP]: A developer can view a human-readable mutation rationale as a structured, queryable field in the evolution result summary — explaining not just what was mutated but why.
FR29 [MVP]: The system surfaces scorer signal diagnostics in the evolution result summary, including scorer discrimination analysis and mutation diversity tracking.
FR30 [MVP]: A platform engineer can configure session persistence to an external backend (e.g., PostgreSQL) for enterprise audit requirements.

**Pareto & Multi-Objective Optimization**

FR31 [MVP]: The system tracks a Pareto frontier across multiple objectives (e.g., quality, cost, latency) during evolution.
FR32 [MVP]: The system classifies candidates as dominated or non-dominated on the Pareto frontier, using dominance relationships for selection.
FR33 [MVP]: The system detects regression during multi-agent evolution via Pareto dominance — candidates that improve one dimension but worsen the aggregate are recorded but not selected as parents.
FR34 [MVP]: A developer can export Pareto frontier state as structured data (JSON) for external analysis, dashboards, or organizational reporting.
FR35 [Vision]: A platform engineer can view fleet-level optimization dashboards showing agent quality, cost, and compliance across the organization.

**Safety & Invariant Enforcement**

FR36 [MVP]: A developer can declare schema field preservation constraints (required fields, type compatibility) that evolution never violates, regardless of generation count or fitness score.
FR37 [MVP]: A developer can declare instruction boundary patterns (StateGuardTokens) that constrain the mutation space for instructions.
FR38 [MVP]: The system enforces bounded mutation ranges for generation config parameters, preventing evolution from producing configurations outside developer-declared ranges.
FR39 [MVP]: When candidates score within 5% of each other, the system prefers the candidate with shorter instruction length and more interpretable definitions — favoring auditable evolved agents over opaque high-scoring ones.
FR40 [MVP]: The system guarantees deterministic evolutionary decisions (component selection, candidate selection, Pareto state updates) given the same seed, agents, scorer, and fitness scores — independent of stochastic LLM inference.
FR41 [MVP]: Two concurrent evolution runs with different session IDs never interfere with each other's state or results.

### NonFunctional Requirements

**Performance**

NFR1: Engine Overhead Proportionality — The evolution engine's processing time (mutation selection, Pareto frontier update, candidate management, generation bookkeeping) is negligible relative to LLM inference costs. For evolution runs where LLM inference accounts for >90% of wall-clock time, engine overhead is <1% of total generation time. For workloads where LLM inference is <90% of wall-clock time, engine overhead is bounded at <500ms per generation for populations up to 50.

NFR2: Evolution Scale Characteristics — Evolution state (population, Pareto frontier, generation history, per-agent score tracking) for population sizes up to 50 and generation counts up to 30 occupies <100MB of heap memory, excluding LLM response caching. Beyond documented scale limits, the system raises an explicit error if memory constraints are exceeded.

**Integration**

NFR3: Structured Log Schema Stability — The structured log event schema (field names, types, event names) is documented, versioned, and stable across minor releases. The schema is part of the public API surface.

NFR4: Session Persistence Compatibility — Evolution session events are compatible with ADK's session persistence interface. Any backend that implements ADK's session storage contract can receive evolution events without gepa-adk-specific adapters.

NFR5: Enterprise Observability Routing — Structured log output is routable to enterprise observability platforms (Splunk, Arize/Phoenix, Datadog) via structlog's standard formatter pipeline. No custom adapters required.

NFR6: Credential Redaction — LLM provider API keys, authentication tokens, and other credentials are never included in structured log output, evolution results, or session events. A redaction filter in the logging pipeline ensures sensitive values cannot leak into audit trails.

**Reliability**

NFR7: Explicit Completion Semantics — Evolution runs complete fully or fail explicitly — no silent partial completion. If evolution fails, the system raises a typed exception identifying the failure generation and cause.

NFR8: Typed Exception Coverage — Every failure mode produces a gepa-adk-specific typed exception. The developer never encounters a raw traceback without a wrapping exception type.

NFR9: Diagnostic Error Messages — Every typed exception includes a diagnostic message suggesting the most likely cause and the next investigation step.

NFR10: Observability Completeness — Structured log events are emitted synchronously with evolution execution. No event is lost or delayed. Event count must match decision count.

**Maintainability**

NFR11: Test Coverage Floor — 85%+ test coverage maintained, enforced in CI on every commit.

NFR12: Protocol Contract Tests — Every public Protocol has a corresponding contract test suite. Adding a new Protocol requires adding contract tests.

NFR13: Architectural Boundary Enforcement — Evolution logic has zero direct imports from ADK types outside the adapter module. Enforced via CI static analysis.

**Compatibility**

NFR14: Python Version — Python >=3.12, <3.13. Python 3.13 support deferred post-MVP.

NFR15: ADK Version Range — The system supports google-adk >=1.20.0 through latest, CI-tested against minimum (1.20.0) and latest. Compatibility breakage on any supported ADK version blocks release.

NFR16: LLM Provider Diversity — Any LLM provider supported by LiteLLM works for reflection agent inference without gepa-adk code changes.

### Additional Requirements

**From Architecture — Structural Refactoring (Must Happen Before Feature Work)**

- No starter template (brownfield project with existing codebase ~25 modules across 5 layers)
- Selector Protocol split: refactor `ports/selector.py` into three separate files (`ports/candidate_selector.py`, `ports/evaluation_policy.py`, `ports/component_selector.py`)
- Adapter sub-package reorganization (ADR-014): restructure flat `adapters/` into 8 sub-packages (`execution/`, `scoring/`, `evolution/`, `selection/`, `components/`, `stoppers/`, `workflow/`, `media/`) with backward-compatible re-exports
- Deprecation tests that verify every old import path resolves to the same object as the new sub-package path

**From Architecture — Infrastructure and CI/CD**

- Create `scripts/check_boundaries.sh` — grep-based hexagonal layer import enforcement
- Create `scripts/check_protocol_coverage.py` — CI script that counts Protocols vs contract tests
- Add `py.typed` PEP 561 zero-byte marker file at `src/gepa_adk/py.typed`
- Set up GitHub Actions CI workflows: `tests.yml` (pytest + 85% coverage + ADK version matrix testing adk==1.20.0 and adk-latest), `type-check.yml` (ty check), `boundaries.yml` (boundary enforcement), `docs.yml` (MkDocs), `codeql.yml` (security), `release-please.yml` (automated releases)
- ADK compatibility layer: identify and abstract API differences between adk 1.20.0 and latest, ensuring gepa-adk works across the full supported range without version-conditional code in business logic
- Create `.pre-commit-config.yaml` with full local gate chain (ruff format, ruff check, ty check, pytest contracts — sub-5s budget)
- Add `interrogate` (95% docstring coverage) and `docvet check` (docstring accuracy) in CI

**From Architecture — Architectural Decisions Requiring Implementation**

- Decision 1 (ADR-013): `EvolutionResultProtocol` in `ports/evolution_result.py` with 5 data fields + 2 computed properties + `stop_reason` field; contract test
- Decision 3: `create_critic()` factory function with 3 MVP presets (`structured_output`, `accuracy`, `relevance`); re-export via `gepa_adk.__init__`
- Decision 4 (ADR-015): `schema_version: int = 1` on result types + `to_dict()`/`from_dict()` methods; test fixture `tests/fixtures/evolution_result_v1.json`
- Decision 5 (ADR-014): Full adapter sub-package restructure with re-exports
- Write ADR-013, ADR-014, ADR-015 documents in `docs/adr/`

**From Architecture — Domain Model Requirements**

- Add `StopReason` enum to `domain/types.py` (COMPLETED, MAX_ITERATIONS, STOPPER_TRIGGERED, KEYBOARD_INTERRUPT, TIMEOUT, CANCELLED)
- Add `stop_reason: StopReason` field to `EvolutionResult` and `MultiAgentEvolutionResult`
- Engine must wrap evolution loop in `try/except (KeyboardInterrupt, asyncio.CancelledError)` for partial result construction
- Component name constants in `domain/types.py` (no raw strings)

**From Architecture — Testing Infrastructure**

- Create `tests/factories/` directory with mock factories following declarative pattern
- Protocol auto-discovery registry (`PROTOCOL_REGISTRY`) in `tests/contracts/conftest.py`
- Organize `tests/integration/` by dependency (`adk/`, `ollama/`, `workflow/`)
- Minimum 4-test contract test bar per Protocol implementation
- Contract test time budget <5 seconds for pre-commit

**From Architecture — Documentation and Examples**

- Populate `examples/` directory with runnable scripts (syntax-checked in CI)
- Create `docs/contributing/architecture.md` pointer file
- Create Growth-phase placeholder guide pages

**From Architecture — Implementation Priority Sequence**

1. Selector Protocol split
2. Adapter sub-package reorganization
3. `py.typed` + `scripts/` directory + CI boundary check
4. `create_critic()` factory
5. `StopReason` enum + `stop_reason` field
6. `EvolutionResultProtocol` (ADR-013)
7. `schema_version` + serialization (ADR-015)

**From UX Design — API Surface**

- `evolve()` as primary entry point with keyword-only optional parameters after `*`
- Consistent parameter ordering across `evolve()`, `evolve_group()`, `evolve_workflow()`
- `run_sync(coroutine)` as single sync wrapper (no per-function sync variants)
- Pre-flight validation before starting evolution (model availability, critic format, trainset structure)
- Direct keyword arguments override corresponding `EvolutionConfig` fields

**From UX Design — Result Object**

- `EvolutionResult` frozen dataclass with `.improvement`, `.evolved_components`, `.iteration_history`, `.reflection_reasoning`, `.stop_reason`, `.config`, `.metadata`, `.status`
- Narrative `__repr__()` format (improvement first, greppable, no box-drawing)
- `show_diff()` with git-diff-style output
- `to_json()` / `from_json()` serialization round-trip for all status variants
- `EvolutionStatus` enum: COMPLETE, PARTIAL, FAILED
- PARTIAL results fully usable with same attributes as COMPLETE
- `_repr_html_()` for Jupyter rendering

**From UX Design — Error Handling**

- Base `GepaError` with hierarchy: `ConfigurationError`, `EvaluationError`, `ReflectionError`
- Every subclass carries structured fields: `expected`, `received`, `suggestion`, `context`
- `suggestion` must be actionable (commands/steps, not descriptions)
- Stateless retry pattern (no re-import or restart needed)

**From UX Design — Terminal Output**

- One-line-per-iteration progress format with score, mutation, patience
- TTY mode (colored, Unicode) vs JSON mode (structlog JSON, no color) auto-detected via `sys.stdout.isatty()`
- Three-step encoding fallback (UTF-8 -> Unicode Fallback Table -> `errors='replace'`)
- Color is enhancement only, never information carrier

**From UX Design — Configuration**

- `EvolutionConfig` zero-arg defaults produce reasonable evolution (`patience=3`, `max_iterations=10`)
- Fields organized by progressive disclosure (Day 2 -> Day 3 -> Day 7+)
- `seed=42` for reproducible runs; seed always logged in results
- Critic progressive adoption: `None` -> `"string"` preset -> custom `Agent`

**From UX Design — Documentation**

- Getting-started guide: pip install to first result in 15 minutes
- Every guide page with copy-paste-runnable examples and expected output
- Progressive sidebar navigation matching learning journey
- Common Errors section on every guide page
- MkDocs Material theme with deep blue primary, mutation green accent

### FR Coverage Map

FR1: Epic 2 — Evolve single agent across surfaces
FR2: Epic 2 — Structured evolution result
FR3: Epic 2 — Diff between original and evolved
FR4: Epic 2 — Per-component mutation attribution
FR5: Epic 2 — Highest-impact surface identification
FR6: Epic 2 — Independent API entry points
FR7: *Growth backlog* — Surface-disabled evolution mode
FR8: *(pre-built — evolve_group() fully implemented with per-agent components and shared session)*
FR9: *(pre-built — round-robin component selection in evolve_group())*
FR10: Epic 6 — Per-agent score attribution in multi-agent results
FR11: Epic 6 — Per-agent score breakdown in multi-agent results
FR12: *(pre-built — evolve_workflow() preserves SequentialAgent/LoopAgent/ParallelAgent topology)*
FR13: Epic 1B — ADK 1.20.0+ version range and compatibility layer
FR14: *Growth backlog* — Batch/fleet orchestration
FR15: Epic 3 — Custom scorer via Protocol
FR16: Epic 3 — Critic agents for evaluation
FR17: Epic 3 — Stopper configuration
FR18: Epic 3 — Reflection agent selection
FR19: Epic 3 — Reflection prompt customization
FR20: Epic 3 — Component-aware reflection
FR21: Epic 3 — ComponentHandler extension
FR22: Epic 3 — AgentProviderProtocol
FR23: *Growth backlog* — Model selection surface
FR24: *Growth backlog* — Cost estimation
FR25: *Vision backlog* — Non-ADK framework adapter
FR26: *(pre-built — structlog events throughout codebase with dot-notation naming)*
FR27: *(pre-built — 802-line ADK event extraction pipeline in utils/events.py)*
FR28: Epic 2 — Mutation rationale capture in iteration records
FR29: *(pre-built — CriticScorer returns dimension_scores + actionable_guidance)*
FR30: Epic 8 — External session persistence documentation guide
FR31: *(pre-built — ParetoFrontier with 4 frontier types: INSTANCE, OBJECTIVE, HYBRID, CARTESIAN)*
FR32: *(pre-built — dominance classification in ParetoFrontier.get_non_dominated())*
FR33: Epic 6 — Regression detection stopper
FR34: Epic 6 — Pareto frontier JSON export
FR35: *Vision backlog* — Fleet optimization dashboards
FR36: *(pre-built — SchemaConstraints frozen dataclass + OutputSchemaHandler validation)*
FR37: *(pre-built — StateGuardTokens in utils/state_guard.py, 484 test lines)*
FR38: *(pre-built — validate_generate_config() enforces bounded ranges)*
FR39: *Growth backlog* — Interpretability preference (requires length-aware scorer)
FR40: Epic 2 — Seed-based determinism for reproducible runs
FR41: *(pre-built — BaseSessionService injection with InMemorySessionService default)*

**Coverage: 34/35 MVP FRs mapped to epics (12 pre-built, 22 requiring new stories). FR39 deferred to Growth. 5 Growth + 2 Vision in backlog.**

## Epic List

### Epic 1A: Structural Refactoring
Codebase structural alignment that enables safe parallel feature development — selector split, adapter sub-packages, and internal Protocol unification.
**FRs covered:** *(internal — enables all subsequent epics)*
**Scope:** Selector Protocol split (3 files), adapter sub-package reorganization (ADR-014), re-export backward compatibility, deprecation tests, EvolutionResultProtocol (ADR-013), write ADR-013 + ADR-014 documents

### Epic 1B: Quality Infrastructure & ADK Compatibility
A developer on ADK 1.20.0+ can use the library with CI-enforced quality gates, type checking support, and architectural boundary protection.
**FRs covered:** FR13
**NFRs addressed:** NFR11, NFR13, NFR14, NFR15, NFR16
**Scope:** CI pipelines (boundary check, protocol coverage, ADK version matrix 1.20.0 + latest), ADK 1.20.0 compatibility layer, scripts/ directory *(pre-commit, py.typed, docvet config moved to Story 1A.1)*

### Epic 2: Single-Agent Evolution
A developer can evolve a single agent's definition and receive a structured, serializable result with improvement metrics, diffs, mutation attribution, graceful interrupt support, reproducible runs, and observability enhancements.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR28, FR40
**NFRs as stories:** NFR6 (credential redaction defaults)
**Includes (from architecture decisions):** StopReason enum + stop_reason field, schema_version + to_dict()/from_dict() (ADR-015), write ADR-015 document
**UX scope:** evolve() API polish, EvolutionResult narrative repr, show_diff(), to_json()/from_json(), Ctrl+C -> partial result, pre-flight validation, run_sync()
**Added from party mode (Epics 4/5 triage):** seed-based determinism (FR40), mutation rationale capture (FR28), credential redaction defaults (NFR6)

### Epic 3: Evolution Control & Extensibility
A developer can customize evolution behavior through scoring, critics, stoppers, and reflection configuration, and a contributor can extend the system with new surfaces and agent providers.
**FRs covered:** FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22
**Scope:** Custom scorer via Protocol, create_critic() factory (3 MVP presets), stopper configuration, reflection agent selection, reflection prompt customization, component-aware reflection, ComponentHandler extension (FR21), AgentProviderProtocol (FR22)

### ~~Epic 4: Safety, Invariants & Determinism~~ — DELETED
*Codebase exploration verified: FR36 (SchemaConstraints + OutputSchemaHandler), FR37 (StateGuardTokens, 484 test lines), FR38 (validate_generate_config()), FR41 (BaseSessionService isolation) are all fully implemented and tested. FR40 (seed determinism) moved to Epic 2. FR39 (interpretability preference) deferred to Growth.*

### ~~Epic 5: Observability & Audit Trail~~ — DELETED
*Codebase exploration verified: FR26 (structlog events throughout), FR27 (802-line event extraction pipeline), FR29 (CriticScorer dimension_scores + actionable_guidance) are all fully implemented. FR28 (mutation rationale) and NFR6 (credential redaction) moved to Epic 2. FR30 (external session persistence docs) moved to Epic 8.*

### Epic 6: Evolution Analytics
A developer can detect regressions, export Pareto frontier state as JSON, and view per-agent score attribution for data-driven evolution decisions.
**FRs covered:** FR10, FR11, FR33, FR34
*Note: FR31 (Pareto tracking) and FR32 (dominance classification) verified as pre-built. Epic restructured from "Pareto Multi-Objective" to "Evolution Analytics" absorbing multi-agent attribution from deleted Epic 7.*

### ~~Epic 7: Multi-Agent & Workflow Evolution~~ — DELETED
*Codebase exploration verified: FR8 (evolve_group() — 330 lines), FR9 (round-robin component selection), FR12 (evolve_workflow() — 255 lines with recursive agent discovery) are all fully implemented and tested. FR10+FR11 (per-agent attribution) moved to Epic 6.*

### Epic 8: Developer Experience & Documentation
A developer has rich terminal output and comprehensive, up-to-date documentation with runnable examples.
**FRs covered:** FR30 (session persistence documentation)
**UX/DX scope:** Terminal output formatter (TTY vs JSON modes), documentation updates (getting-started, new feature guides, session persistence guide, examples/)
*Note: Error hierarchy (1126-line exceptions.py, 15 types) and MkDocs infrastructure (191-line mkdocs.yml, 28 docs, 11 ADRs) verified as pre-built.*

### Dependency Graph

```
Epic 1A (Structural) ──> Epic 1B (Infra/Compat) ──> All feature epics
                                                 ──> Epic 2 (Single-Agent + Observability)
                                                 ──> Epic 3 (Control & Extensibility)
                                                 ──> Epic 6 (Evolution Analytics)
                                                 ──> Epic 8 (DX & Docs) [cross-cutting, ongoing]
```

### NFR Distribution

NFRs are mapped as acceptance criteria on functional stories rather than standalone epics:

- **NFR1** (Engine overhead <1%): AC on Epic 2 engine stories
- **NFR2** (Memory <100MB at scale): AC on Epic 2 engine stories
- **NFR3** (Log schema stability): AC on Epic 2 observability stories
- **NFR4** (Session persistence compatibility): *(pre-built — BaseSessionService compatible with ADK persistence)*
- **NFR5** (Enterprise observability routing): *(pre-built — structlog standard formatter pipeline)*
- **NFR6** (Credential redaction): Standalone story in Epic 2 (default sensitive_keys)
- **NFR7** (Explicit completion semantics): AC on Epic 2 result stories
- **NFR8** (Typed exception coverage): *(pre-built — 15 typed exceptions in 1126-line hierarchy)*
- **NFR9** (Diagnostic error messages): *(pre-built — every exception includes contextual __str__)*
- **NFR10** (Observability completeness): *(pre-built — structlog events throughout codebase)*
- **NFR11** (85% test coverage): Definition of Done across ALL epics
- **NFR12** (Protocol contract tests): AC on any story adding/modifying Protocols
- **NFR13** (Boundary enforcement): Story in Epic 1B (CI script)
- **NFR14** (Python 3.12): Constraint on Epic 1B CI matrix
- **NFR15** (ADK 1.20.0+ range): Story in Epic 1B (compatibility layer + CI matrix)
- **NFR16** (LiteLLM provider diversity): AC on Epic 3 reflection stories

## Epic 1A: Structural Refactoring

Codebase structural alignment that enables safe parallel feature development — selector split, adapter sub-packages, and internal Protocol unification.

### Story 1A.1: Split Selector Protocol into Three Port Files + Light Up Pre-Commit

As a contributor,
I want each selector Protocol in its own file following the one-Protocol-per-file convention, with local quality gates active from day one,
So that new Protocols can be added without modifying a monolithic selector module, and every file touched from this point forward is incrementally aligned.

**Acceptance Criteria:**

*Pre-Commit & Tooling (absorbed from Story 1B.3):*

**Given** the project uses ruff, ty, pytest, interrogate (already configured at 95%), and docvet (already in dev deps)
**When** `.pre-commit-config.yaml` is created
**Then** the hook chain runs: `ruff format --check`, `ruff check`, `ty check`, `pytest tests/contracts/ -x --no-header`
**And** the full pre-commit chain completes in under 5 seconds
**And** if contract tests exceed 5-second budget, they are split into a fast subset (pre-commit) and full subset (CI only)
**And** `[tool.docvet]` section is added to `pyproject.toml` with `fail-on = ["enrichment", "freshness", "coverage", "griffe"]` (mirroring sister project docvet)
**And** `tool.ruff.lint.isort.known-first-party` is corrected from `"agent_workflow_suite"` to `"gepa_adk"`
**And** `py.typed` PEP 561 zero-byte marker file exists at `src/gepa_adk/py.typed`
**And** `docvet check` is documented as a recommended pre-commit step but not enforced in the hook chain (too slow for sub-5s budget); developers run `docvet check` on touched files manually or in CI

*Selector Protocol Split:*

**Given** `ports/selector.py` contains `CandidateSelectorProtocol`, `EvaluationPolicyProtocol`, and `ComponentSelectorProtocol`
**When** the refactoring is applied
**Then** three new files exist: `ports/candidate_selector.py`, `ports/evaluation_policy.py`, `ports/component_selector.py`
**And** each file contains exactly one `@runtime_checkable` Protocol + `__all__`
**And** `ports/__init__.py` re-exports all three Protocols and `__all__` is updated with the new module exports
**And** existing contract tests (`test_candidate_selector_protocol.py`, `test_evaluation_policy_protocol.py`, `test_component_selector_protocol.py`) verify import from both the new direct path (e.g., `gepa_adk.ports.candidate_selector`) and the re-export path (`gepa_adk.ports`) resolve to the same class
**And** all existing tests pass without modification
**And** pre-commit hooks pass clean on all new/modified files

### Story 1A.2: Reorganize Adapters into Sub-Packages

As a contributor,
I want adapters organized by concern in sub-packages with backward-compatible re-exports,
So that I can navigate and extend the adapter layer without cognitive overload.

**Acceptance Criteria:**

**Given** a flat `adapters/` directory with 11 root modules plus an existing `stoppers/` sub-package
**When** the reorganization is applied
**Then** 7 new sub-packages exist: `execution/`, `scoring/`, `evolution/`, `selection/`, `components/`, `workflow/`, `media/`
**And** the existing `stoppers/` sub-package remains untouched — no file moves, no new `__init__.py`
**And** each sub-package has an `__init__.py` that exports its public symbols
**And** single-module packages include a docstring in `__init__.py` explaining the package's purpose and anticipated growth
**And** `adapters/__init__.py` re-exports every previously-importable symbol to its new sub-package location
**And** deprecation tests systematically verify every previously-importable symbol: `assert adapters.X is adapters.subpkg.X`
**And** full `pytest` run passes with zero failures, zero import warnings, and no coverage drop below current level
**And** ADR-014 document is written at `docs/adr/ADR-014-adapter-reorganization.md`

### Story 1A.3: Define EvolutionResultProtocol

As a contributor,
I want a shared Protocol that both `EvolutionResult` and `MultiAgentEvolutionResult` structurally satisfy,
So that engine and utility code can accept either result type without type unions.

**Acceptance Criteria:**

**Given** two frozen result dataclasses sharing 5 data fields and 2 computed properties
**When** `EvolutionResultProtocol` is defined in `ports/evolution_result.py`
**Then** the Protocol declares 5 data fields (`original_score`, `final_score`, `evolved_components`, `iteration_history`, `total_iterations`) + 2 computed properties (`improvement`, `improved`)
**And** `stop_reason` is NOT included in this Protocol definition (deferred to Epic 2 when the field is added to result types)
**And** both `EvolutionResult` and `MultiAgentEvolutionResult` pass `isinstance()` checks against the Protocol without any code changes to the result types
**And** a contract test at `tests/contracts/test_evolution_result_protocol.py` includes minimum 4 tests: isinstance check for both result types, property return type verification, happy path field access, structural equivalence (both types return same types for shared fields)
**And** ADR-013 document is written at `docs/adr/ADR-013-result-type-protocol.md`
**And** the Protocol is exported in `ports/__init__.py` and `__all__` is updated

## Epic 1B: Quality Infrastructure & ADK Compatibility

A developer on ADK 1.20.0+ can use the library with CI-enforced quality gates and architectural boundary protection.
*Note: Developer local tooling (pre-commit, py.typed, docvet config) absorbed into Story 1A.1 to light up quality gates from the first story.*

### Story 1B.1: Architectural Boundary Enforcement Scripts

As a contributor,
I want CI to automatically detect hexagonal layer violations,
So that architectural boundaries are enforced without manual code review.

**Acceptance Criteria:**

**Given** the hexagonal architecture with domain/ports/adapters/engine/utils layers
**When** `scripts/check_boundaries.sh` is run
**Then** it fails if ADK/LiteLLM imports appear outside `adapters/`
**And** it fails if adapter imports appear in `domain/` or `ports/`
**And** it fails if engine imports appear in `domain/`, `ports/`, or `adapters/`
**And** it handles `TYPE_CHECKING`-guarded imports via grep heuristic (skip import lines within 3 lines of a `TYPE_CHECKING` line) — sufficient for MVP, AST-based upgrade deferred to Growth
**And** `scripts/check_protocol_coverage.py` counts `@runtime_checkable` Protocols in `ports/` against contract test files in `tests/contracts/` and fails if any Protocol lacks a contract test
**And** a `boundaries.yml` GitHub Actions workflow runs both scripts on every PR

### Story 1B.2: ADK 1.20.0 Compatibility Layer

As a developer using an enterprise-deployed ADK version,
I want gepa-adk to work with google-adk 1.20.0 through latest,
So that I can adopt the library without upgrading my ADK version.

**Acceptance Criteria:**

**Given** the current dependency floor is google-adk>=1.22.0 with no compatibility shims
**When** the compatibility work is performed
**Then** discovery is done first: install adk==1.20.0 in isolation, run full test suite, categorize failures as import errors, API signature changes, or behavioral changes
**And** compatibility shims are implemented in the adapters layer — no version-conditional code in domain/ports/engine
**And** `pyproject.toml` dependency is updated from `google-adk>=1.22.0` to `google-adk>=1.20.0`
**And** the existing `tests.yml` CI workflow is updated with an ADK version matrix testing against adk==1.20.0 and adk-latest
**And** no test uses version-conditional assertions — tests assert behavior, not version
**And** API differences are documented in a compatibility section in the ADK adapter module docstring

### ~~Story 1B.3: Developer Local Tooling~~ — ABSORBED INTO Story 1A.1
*Pre-commit hook chain, py.typed, docvet config, and isort fix all moved to Story 1A.1 to ensure quality gates are active from the very first story. No remaining scope.*

### Story 1B.3: Clean Up ty Type-Check Diagnostics

As a contributor,
I want the ty type-check CI gate to pass green,
So that the type-check workflow is a reliable quality signal and new regressions are immediately visible.

**Acceptance Criteria:**

**Given** ty check currently reports 9 diagnostics (2 errors, 7 warnings) that also fail the CI type-check job on develop
**When** the cleanup is performed
**Then** all fixable `unused-type-ignore-comment` warnings are resolved by removing stale `# type: ignore` comments from test files
**And** the `invalid-argument-type` errors in `engine/proposer.py` are resolved (narrow `Mapping` to `dict` or add explicit casts)
**And** `uv run ty check` exits 0 with no errors and no warnings
**And** the CI type-check job passes green
**And** no test behavior changes — all existing tests still pass
**And** ty override rules in `pyproject.toml` are reduced to only those that are genuinely unfixable (dynamic BaseModel subclasses, pytest.MonkeyPatch.context() ty bug)

### Story 1B.4: Fix Pre-Existing Boundary Violations

As a contributor,
I want zero boundary violations so the CI gate can be hardened to blocking,
So that architectural drift is caught immediately on every PR.

**Acceptance Criteria:**

**Given** Story 1B.1 discovered 7 pre-existing import boundary violations and the `boundaries.yml` workflow runs with `continue-on-error: true`
**When** the violations are resolved
**Then** `engine/reflection_agents.py` no longer imports `google.adk.agents` or `google.adk.tools` at module level — ADK agent creation is moved to adapters or injected
**And** `engine/adk_reflection.py` no longer lazy-imports `google.adk.sessions.InMemorySessionService` — session service is injected via constructor
**And** `utils/config_utils.py` no longer lazy-imports `google.genai.types.GenerateContentConfig` — type is injected or import is moved to adapters
**And** `adapters/evolution/adk_adapter.py` no longer imports from `gepa_adk.engine` — engine components are injected via constructor or factory
**And** `adapters/evolution/multi_agent.py` no longer imports from `gepa_adk.engine` — engine components are injected
**And** `scripts/check_boundaries.sh` exits 0 (zero violations)
**And** `boundaries.yml` `continue-on-error` is removed, making the gate blocking

## Epic 2: Single-Agent Evolution

A developer can evolve a single agent's definition and receive a structured, serializable result with improvement metrics, diffs, mutation attribution, and graceful interrupt support.

### Story 2.1: Add StopReason, Schema Version, and Stop Reason to Results

As a developer,
I want to know why my evolution run stopped and have versioned result schemas,
So that I can distinguish between completion modes and safely serialize results across versions.

**Acceptance Criteria:**

**Given** evolution runs currently complete without a structured stop reason or schema version
**When** domain model changes are applied
**Then** `StopReason` enum is added to `domain/types.py` with values: `COMPLETED`, `MAX_ITERATIONS`, `STOPPER_TRIGGERED`, `KEYBOARD_INTERRUPT`, `TIMEOUT`, `CANCELLED`
**And** `stop_reason: StopReason` field is added to both `EvolutionResult` and `MultiAgentEvolutionResult` (defaulting to `StopReason.COMPLETED`)
**And** `schema_version: int = 1` frozen field is added to both result types
**And** the `EvolutionResultProtocol` (from Story 1A.3) is updated to include `stop_reason` and `schema_version`
**And** the engine sets the appropriate `StopReason` based on termination condition (max iterations, stopper triggered, etc.)
**And** ADR-015 document is written at `docs/adr/ADR-015-result-schema-versioning.md`
**And** existing tests pass and new tests verify each stop reason is set correctly
**And** every test asserting on results includes `result.schema_version == 1`

### Story 2.2: Result Serialization

As a developer,
I want to serialize and deserialize evolution results,
So that I can save results, compare across sessions, and integrate with external tools.

**Acceptance Criteria:**

**Given** `EvolutionResult` and `MultiAgentEvolutionResult` now have `schema_version` and `stop_reason` fields (from Story 2.1)
**When** serialization methods are added
**Then** `to_dict()` instance method produces a stdlib-only dict representation including all fields
**And** `from_dict()` class method reconstructs the result from a dict, validating `schema_version`
**And** round-trip holds: fields of `from_dict(result.to_dict())` match the original for all status variants (complete, partial, failed)
**And** a test fixture `tests/fixtures/evolution_result_v1.json` is created for regression testing
**And** `to_dict()` and `from_dict()` use only stdlib (no external serialization libraries)

### Story 2.3: Evolution Result Display Enhancements

As a developer,
I want a readable, informative result representation,
So that I can quickly understand what happened during evolution without parsing raw data.

**Acceptance Criteria:**

**Given** `EvolutionResult` currently uses the default dataclass repr
**When** display enhancements are implemented
**Then** `__repr__()` uses narrative format: improvement percentage first, then iterations/stop reason, then components, then truncated reflection summary — no box-drawing characters, every line greppable, 2-space indent
**And** `show_diff()` produces git-diff-style (`---`/`+++`/`@@`) before/after comparison of evolved components
**And** regex-based structural tests verify format elements are present (improvement line, iterations line, greppable output) — no brittle snapshot tests until format stabilizes
**And** `_repr_html_()` renders formatted HTML tables for Jupyter rendering

### Story 2.4: Graceful Interrupt with Partial Results

As a developer,
I want Ctrl+C during evolution to return my best results so far,
So that I don't lose progress from long-running evolution runs.

**Acceptance Criteria:**

**Given** an evolution run in progress with no current KeyboardInterrupt handling
**When** the developer presses Ctrl+C
**Then** the engine catches `KeyboardInterrupt` and `asyncio.CancelledError` in the evolution loop
**And** a partial `EvolutionResult` is constructed with `stop_reason=StopReason.KEYBOARD_INTERRUPT`
**And** the partial result contains the best-so-far evolved components and all completed iteration records
**And** the partial result serializes correctly via `to_dict()`/`from_dict()`
**And** re-running evolution after interrupt requires no cleanup (stateless retry)
**And** tested via integration test with mock scorer that raises KeyboardInterrupt after N iterations, verifying N iteration records and correct stop_reason (marked `pytest.mark.integration`)
**And** works alongside existing `SignalStopper` — engine catch handles immediate interrupts mid-LLM-call, SignalStopper handles graceful inter-iteration stops

### Story 2.5: Pre-Flight Validation Enhancements

As a developer,
I want immediate local feedback if my evolution setup is invalid,
So that I don't waste time waiting for a run to fail on the first iteration.

**Acceptance Criteria:**

**Given** existing validation checks agent type and trainset structure
**When** pre-flight validation is enhanced
**Then** additional local-only checks run before the first iteration: critic type validity, config field ranges, component name validity, EvolutionConfig consistency
**And** model availability is NOT checked in pre-flight (deferred to first-iteration failure with clear `ConfigurationError` including `expected`, `received`, `suggestion` fields)
**And** all validation errors raise `ConfigurationError` immediately — before any LLM call
**And** no error state requires re-importing or restarting the Python process to retry
**And** no pre-flight check makes network calls

### Story 2.6: Universal Sync Wrapper and API Surface Polish

As a developer working in scripts or REPLs,
I want a single sync wrapper for any async evolution call,
So that I don't need to manage asyncio boilerplate.

**Acceptance Criteria:**

**Given** `evolve_sync()` currently exists wrapping only `evolve()`
**When** the universal sync wrapper is implemented
**Then** `run_sync(coroutine)` wraps any async `evolve_*()` call using `asyncio.run()` with nest_asyncio fallback
**And** `evolve_sync()` is retained as a deprecated alias pointing to `run_sync(evolve(...))`
**And** `run_sync` is exported in `gepa_adk.__init__.py.__all__`
**And** `run_sync()` is documented as incompatible with Jupyter (which has a running event loop)
**And** the `evolve()` signature is updated to use `*` keyword-only separator after `trainset` for optional parameters (breaking change documented in ADR-015)
**And** `evolve_group()` and `evolve_workflow()` signatures are similarly updated for consistency

### Story 2.7: Seed-Based Determinism

As a developer,
I want to set a seed for reproducible evolution runs,
So that I can debug, compare, and reproduce evolutionary decisions deterministically.

**Acceptance Criteria:**

**Given** `EvolutionConfig` has no `seed` parameter and RNG is inconsistent across components
**When** seed-based determinism is implemented
**Then** `seed: int | None = None` field is added to `EvolutionConfig`
**And** when seed is provided, a central `random.Random(seed)` is created and passed to all stochastic components (candidate selector, merge proposer, component selector)
**And** when seed is `None`, components use default random behavior (backward compatible)
**And** seed is always logged in evolution results metadata: `result.config.seed`
**And** two runs with identical seed, agents, scorer, and fitness scores produce identical evolutionary decisions (component selection order, candidate selection, Pareto state updates)
**And** determinism applies only to engine decisions — LLM inference is inherently stochastic and NOT covered by seed guarantee
**And** tested via unit test: run engine twice with same seed and mock scorer returning fixed scores, assert identical iteration histories

### Story 2.8: Mutation Rationale Capture

As a developer,
I want to see why the reflection agent proposed each mutation,
So that I can understand the evolutionary reasoning and debug unexpected changes.

**Acceptance Criteria:**

**Given** reflection agent output is currently consumed but not persisted
**When** mutation rationale capture is implemented
**Then** `reflection_reasoning: str | None = None` field is added to `IterationRecord`
**And** the engine captures the reflection agent's text output (the reasoning explaining the mutation) and stores it in the iteration record
**And** `EvolutionResult` exposes `.reflection_reasoning` property returning the last iteration's reasoning (convenience accessor)
**And** reflection reasoning is included in `to_dict()` serialization
**And** existing tests pass with the new optional field defaulting to None
**And** new test verifies reasoning is captured when reflection agent produces text output

### Story 2.9: Credential Redaction Defaults

As a developer,
I want sensible default credential redaction in trajectory logging,
So that API keys and tokens never leak into logs or evolution results without explicit configuration.

**Acceptance Criteria:**

**Given** `TrajectoryConfig` has `sensitive_keys` defaulting to empty tuple and `redact_sensitive` defaulting to False
**When** credential redaction defaults are implemented
**Then** `DEFAULT_SENSITIVE_KEYS` constant is added to `utils/events.py` containing common sensitive key patterns: `("api_key", "token", "secret", "password", "credential", "authorization", "bearer")`
**And** `TrajectoryConfig.sensitive_keys` defaults to `DEFAULT_SENSITIVE_KEYS`
**And** `TrajectoryConfig.redact_sensitive` defaults to `True`
**And** backward compatibility: users who explicitly pass `sensitive_keys=()` or `redact_sensitive=False` can disable redaction
**And** redaction applies to trajectory tool_call arguments/results and state_deltas (existing recursive `_redact_sensitive()` function)
**And** tested: default config redacts common key patterns; explicit empty config preserves all values

## Epic 3: Evolution Control & Extensibility

A developer can customize evolution behavior through scoring, critics, stoppers, and reflection configuration, and a contributor can extend the system with new surfaces and agent providers.

*Note: Scorer Protocol (12 tests), Stopper Protocol (16 tests), ComponentHandler (16 tests), AgentProvider (13 tests), and component-aware reflection (3 specialized factories) all already exist and exceed the 4-test minimum contract test bar. FR18 (reflection agent selection) is satisfied via configurable model parameter in ADK reflection — LiteLLM serves as the model proxy, not a separate implementation.*

### Story 3.1: Implement Critic Preset Factory

As a developer,
I want to use pre-built critic agents by name,
So that I can add structured evaluation without defining custom critic agents.

**Acceptance Criteria:**

**Given** `CriticScorer` exists but no preset factory function
**When** `create_critic(name, *, model=None)` is implemented in `adapters/scoring/critic_scorer.py`
**Then** 3 MVP presets are available: `"structured_output"`, `"accuracy"`, `"relevance"`
**And** each preset returns a configured `LlmAgent` ready to use as a critic
**And** invalid preset names raise `ConfigurationError` with `suggestion` listing all valid presets
**And** `create_critic` is re-exported via `gepa_adk.__init__`
**And** `gepa_adk.critic_presets` dict maps preset name to human-readable description
**And** 4 deterministic tests: one per preset + invalid-name error test

### Story 3.2: Fill Contract Test Gaps

As a contributor,
I want every public Protocol to have contract tests,
So that the protocol coverage CI check (from Story 1B.1) passes and new implementations are validated.

**Acceptance Criteria:**

**Given** `ProposerProtocol` and `VideoBlobServiceProtocol` lack contract tests
**When** contract tests are added
**Then** `tests/contracts/test_proposer_protocol.py` exists with minimum 4 tests: isinstance check, async method signature verification, happy path returns `ProposalResult | None`, error contract
**And** `tests/contracts/test_video_blob_service_protocol.py` exists with minimum 4 tests: isinstance check, method signature verification, happy path, error contract
**And** `scripts/check_protocol_coverage.py` (from Story 1B.1) passes with zero missing Protocols

### Story 3.3: Extension Point Documentation

As a contributor,
I want clear documentation for extending the system,
So that I can add new evolvable surfaces or agent providers without reading internal code.

**Acceptance Criteria:**

**Given** `ComponentHandler` Protocol (FR21) and `AgentProviderProtocol` (FR22) exist with mature contract tests
**When** extension documentation is created
**Then** each extension point has a dedicated guide page with: Protocol definition, step-by-step implementation recipe, registration process, runnable example, and common pitfalls
**And** contract test skeletons are provided as a starting point for new implementations
**And** the extension points are accessible using only public API imports — no internal module imports required
**And** guide pages are added to MkDocs navigation under a "Contributing" or "Extending" section

## Epic 6: Evolution Analytics

A developer can detect regressions, export Pareto frontier state as JSON, and view per-agent score attribution for data-driven evolution decisions.

*Note: FR31 (Pareto tracking) and FR32 (dominance classification) verified as pre-built with 4 frontier types (INSTANCE, OBJECTIVE, HYBRID, CARTESIAN) in domain/state.py. FR8 (group evolution), FR9 (round-robin), FR12 (workflow topology) verified as pre-built in api.py. This epic covers the remaining analytical gaps.*

### Story 6.1: Regression Detection Stopper

As a developer,
I want evolution to stop automatically if scores consistently decline,
So that I don't waste compute on evolution runs that are degrading.

**Acceptance Criteria:**

**Given** no explicit regression detection exists (only stagnation via patience counter)
**When** a `RegressionStopper` is implemented
**Then** `adapters/stoppers/regression.py` contains `RegressionStopper` implementing `StopperProtocol`
**And** the stopper detects score decline: when best_score at iteration N is lower than best_score at iteration N-K (configurable lookback window, default K=3)
**And** `stop_reason` is set to `StopReason.STOPPER_TRIGGERED` when regression is detected
**And** the stopper can be composed with existing stoppers via `CompositeStopCondition`
**And** contract test at `tests/contracts/test_regression_stopper_contract.py` with minimum 4 tests: isinstance check, method signature, happy path (no regression), regression detected
**And** unit tests cover: regression with default window, custom window, no regression with improving scores, edge case with insufficient history

### Story 6.2: Pareto Frontier JSON Export

As a developer,
I want to export Pareto frontier state as structured JSON,
So that I can analyze frontier evolution in external dashboards or organizational reporting.

**Acceptance Criteria:**

**Given** `ParetoState` and `ParetoFrontier` have no serialization methods
**When** JSON export is implemented
**Then** `to_dict()` methods are added to `ParetoFrontier` and `ParetoState`
**And** exported dict includes: frontier leaders, best scores, candidate genealogy, frontier type
**And** `to_json(indent=2)` convenience method wraps `json.dumps(self.to_dict())`
**And** enum values serialize as strings (e.g., `FrontierType.INSTANCE` → `"instance"`)
**And** round-trip test: fields of reconstructed `ParetoState` match original
**And** export includes enough information for external visualization of Pareto front (candidate scores, domination relationships)

### Story 6.3: Per-Agent Score Attribution

As a developer,
I want per-agent score breakdowns in multi-agent evolution results,
So that I can identify which agents improved and which degraded.

**Acceptance Criteria:**

**Given** `MultiAgentEvolutionResult` tracks aggregate scores but no per-agent breakdown
**When** per-agent attribution is implemented
**Then** `per_agent_scores: dict[str, float] | None` field is added to `MultiAgentEvolutionResult` (optional, None for single-agent)
**And** per-agent scores are computed from iteration history by grouping `IterationRecord.evolved_component` by agent name prefix
**And** `per_agent_improvement: dict[str, float]` computed property returns improvement per agent
**And** baseline filtering (FR10): `MultiAgentEvolutionResult.improved_agents` property returns only agents whose final score exceeds their pre-evolution baseline
**And** `to_dict()` includes per_agent_scores in serialization
**And** tested: multi-agent run with mock scores verifies per-agent breakdown matches expected values

## Epic 8: Developer Experience & Documentation

A developer has rich terminal output and comprehensive, up-to-date documentation with runnable examples.

*Note: Error hierarchy (1126-line exceptions.py, 15 types with contextual __str__) and MkDocs infrastructure (191-line mkdocs.yml, 28 docs, 11 ADRs, 11 plugins) verified as pre-built. This epic covers the remaining DX gaps.*

### Story 8.1: Terminal Output Formatter

As a developer,
I want human-readable terminal output during evolution runs,
So that I can monitor progress without parsing raw log output.

**Acceptance Criteria:**

**Given** the API returns structured objects with no terminal presentation layer
**When** terminal output is implemented
**Then** a `TerminalFormatter` class in `utils/terminal.py` produces one-line-per-iteration progress output: iteration number, score, mutation target, patience counter, improvement delta
**And** TTY mode (auto-detected via `sys.stdout.isatty()`) uses color (ANSI codes) and Unicode indicators
**And** JSON mode (non-TTY) emits structlog JSON lines for machine consumption
**And** three-step encoding fallback: UTF-8 → Unicode Fallback Table (existing `EncodingSafeProcessor`) → `errors='replace'`
**And** color is enhancement only — never the sole carrier of information (all status also shown via text labels)
**And** the formatter is opt-in: `evolve(..., verbose=True)` or environment variable `GEPA_VERBOSE=1`
**And** tested: TTY mock verifies ANSI output, non-TTY mock verifies JSON output

### Story 8.2: Documentation Updates

As a developer,
I want up-to-date documentation covering all new features,
So that I can adopt new capabilities without reading source code.

**Acceptance Criteria:**

**Given** 6 guides, 11 ADRs, and extensive MkDocs infrastructure already exist
**When** documentation updates are applied
**Then** getting-started guide is updated with current API surface (including `run_sync()`, `create_critic()`, seed parameter)
**And** new guide page: "External Session Persistence" covering how to plug in custom `BaseSessionService` implementations (Redis, PostgreSQL examples)
**And** each new feature from Epics 2, 3, 6 has a corresponding section in the relevant existing guide or a new guide page
**And** `examples/` directory contains at minimum: `basic_evolution.py`, `multi_agent_evolution.py`, `custom_scorer.py`, `critic_presets.py`
**And** examples are syntax-checked in CI (import validation, no runtime errors with mock fixtures)
**And** Common Errors section added to getting-started guide with top 5 developer errors and their solutions
