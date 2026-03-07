---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-01'
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/product-brief-gepa-adk-2026-03-01.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - '_bmad-output/planning-artifacts/prd-validation-report.md'
  - '_bmad-output/project-context.md'
  - '_bmad-output/planning-artifacts/research/domain-evolutionary-automated-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/market-automated-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/technical-hybrid-prompt-optimization-research-2026-03-01.md'
  - 'docs/index.md'
  - 'docs/getting-started.md'
  - 'docs/project-management.md'
  - 'docs/concepts/index.md'
  - 'docs/concepts/gepa-fundamentals.md'
  - 'docs/concepts/single-agent-evolution.md'
  - 'docs/concepts/multi-agent-evolution.md'
  - 'docs/concepts/workflow-agents.md'
  - 'docs/guides/single-agent.md'
  - 'docs/guides/multi-agent.md'
  - 'docs/guides/critic-agents.md'
  - 'docs/guides/reflection-prompts.md'
  - 'docs/guides/stoppers.md'
  - 'docs/guides/workflows.md'
  - 'docs/reference/glossary.md'
  - 'docs/reference/index.md'
  - 'docs/adr/index.md'
  - 'docs/adr/ADR-000-hexagonal-architecture.md'
  - 'docs/adr/ADR-001-async-first-architecture.md'
  - 'docs/adr/ADR-002-protocol-for-interfaces.md'
  - 'docs/proposals/001-initial-package-proposal.md'
  - 'docs/contributing/docstring-templates.md'
  - 'docs/contributing/releasing.md'
workflowType: 'architecture'
project_name: 'gepa-adk'
user_name: 'Alberto-Codes'
date: '2026-03-01'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (41 FRs across 6 capability areas):**

| Capability Area | FR Count | Phase | Architectural Implication |
|----------------|----------|-------|--------------------------|
| Single-agent evolution | ~12 | MVP | Core engine loop, adapter contract, scorer protocol |
| Multi-agent pipeline evolution | ~7 | MVP/Growth | Round-robin component selection, qualified naming, session sharing |
| Workflow structure evolution | ~5 | MVP/Growth | Recursive cloning, structure preservation invariants |
| Multi-surface component evolution | ~9 | MVP | ComponentHandler protocol, per-surface validation (text/AST/YAML) |
| Enterprise observability | ~5 | MVP/Growth | structlog integration, ADK session events, trajectory capture |
| Extension protocols | ~3 | Growth | Protocol-based ports, contract test enforcement |

**Non-Functional Requirements (16 NFRs across 5 categories):**

| Category | Key Constraints | Architectural Impact |
|----------|----------------|---------------------|
| Performance | Engine overhead <1%, <100MB heap | In-memory Pareto state, no unnecessary copies |
| Integration | Zero ADK imports outside adapter layer | Strict hexagonal boundary enforcement |
| Reliability | 99%+ completion for shipped features | Graceful degradation, partial result on interrupt |
| Maintainability | 85%+ coverage, contract tests for every Protocol impl | Three-layer test strategy, CI enforcement |
| Compatibility | ADK version range (>=1.22.0), Python >=3.12,<3.13 | Version-isolated adapter layer, no internal ADK API usage |

**Scale & Complexity:**

- Primary domain: Python library (framework extension for Google ADK)
- Complexity level: Medium-High
- Existing architectural components: ~25 modules across 5 layers (domain, ports, adapters, engine, utils)
- Brownfield status: Core engine, 3 evolvable surfaces, progressive API, hexagonal architecture, 10 ADRs — all shipped and tested

### Technical Constraints & Dependencies

**Hard Constraints (from project-context.md and ADRs):**

- Python 3.12 strict (`>=3.12,<3.13`) — modern syntax required (`X | Y`, `list[X]`)
- google-adk >= 1.22.0 — types from `google.adk.agents` and `google.genai.types`
- litellm >= 1.80.13 — LLM proxy for multi-provider support (reflection agents)
- structlog >= 25.5.0 — the ONLY external library allowed in `domain/` layer
- nest-asyncio >= 1.6.0 — enables `asyncio.run()` in sync wrappers
- All core APIs are `async def` — sync wrapper via `asyncio.run()` exists ONLY in `api.py`
- `typing.Protocol` with `@runtime_checkable` — never `abc.ABC`
- Implementations do NOT inherit from Protocols (structural subtyping)
- `@dataclass(slots=True, kw_only=True)` standard; `frozen=True` for immutable records
- Exception hierarchy: all inherit `EvolutionError`, keyword-only `__init__`, both `cause=e` AND `from e`

**Dependency Boundaries (hexagonal layer rules):**

```
domain/   → stdlib only (exception: structlog)
ports/    → domain + stdlib
adapters/ → ports + domain + external libs (ADK, LiteLLM)
engine/   → ports + domain + structlog (may import adapter defaults)
utils/    → stdlib + structlog
```

**Toolchain Constraints:**

- Package manager: `uv` (never pip/poetry)
- Linter/Formatter: `ruff` (line-length 88 formatter, 100 linter)
- Type checker: `ty` (Astral) — NOT mypy
- Docstring coverage: `interrogate` at 95%
- Docstring accuracy: `docvet check`
- Testing: `pytest` with `asyncio_mode = "auto"`, 85% coverage floor

### Architectural Decisions Already Established

This is a brownfield project with 10 accepted ADRs:

| ADR | Decision | Architectural Significance |
|-----|----------|---------------------------|
| ADR-000 | Hexagonal Architecture | Load-bearing decision — all other decisions flow from domain/ports/adapters/engine layer separation |
| ADR-001 | Async-First | All I/O paths are async; single `evolve_sync()` at API boundary |
| ADR-002 | Protocol-Based Interfaces | Structural subtyping via `typing.Protocol`; implementations never inherit from Protocols |
| ADR-005 | Three-Layer Testing | Unit/contract/integration with contract tests for every Protocol implementation |
| ADR-006 | External Library Integration | All external deps isolated in adapters/ |
| ADR-008 | Structured Logging | structlog events at every engine decision point |
| ADR-009 | Exception Hierarchy | `EvolutionError` base with `cause=e` + `from e` |
| ADR-010 | Docstring Quality | Google-style, 95%+ coverage, `docvet` accuracy |
| ADR-011 | Cross-Platform Encoding | Encoding-safe logging for Windows cp1252 |
| ADR-012 | Multi-Agent Component Addressing | Dot-separated qualified names (`generator.instruction`) |

### The Adapter Layer as Subsystem

The adapter layer deserves special architectural attention. While domain/ is clean frozen dataclasses and ports/ is thin Protocol definitions, `adapters/` is where all integration complexity converges:

| Adapter Concern | What It Handles | Interaction With |
|-----------------|-----------------|-----------------|
| ADK Agent Execution | Runner, Session, Event extraction | google-adk |
| Critic Scoring | CriticScorer, feedback normalization | Scorer Protocol |
| Workflow Cloning | Structure-preserving recursive clone | ADK agent types |
| Reflection Wiring | Component-aware reflection agent factories | LiteLLM / ADK LlmAgent |
| Component Handling | Per-surface extract/apply/validate (text, AST, YAML) | ComponentHandler Protocol |
| Stopper Evaluation | Patience, max iterations, convergence detection | StopperProtocol |

**Architectural implication:** The adapter layer needs clear internal boundaries. Growth-phase features (hybrid optimization, model selection, batch evolution) each add new adapter complexity. The architecture should mandate: every new adapter ships with a corresponding mock factory for testing in isolation.

### Progressive API as Architectural Decision

The PRD defines three progressive entry points — `evolve()`, `evolve_group()`, `evolve_workflow()` — with related but distinct return types. The UX spec requires these to "feel identical in usage pattern." This is a structural decision:

- **Shared engine infrastructure** — a single `AsyncGEPAEngine` with mode-specific configuration, or three separate engines?
- **Return type hierarchy** — do `EvolutionResult`, `MultiAgentEvolutionResult`, and `WorkflowEvolutionResult` share a common base, or are they structurally compatible via duck typing?
- **Config propagation** — `EvolutionConfig` flows from API through engine into adapters, proposers, and stoppers. Each component needs different config subsets. The architecture must define whether each component receives the full config or the engine destructures it.

### Cross-Cutting Concerns Identified

1. **Async propagation** — Every I/O path is async from public API through engine through adapters. No internal sync/async bridging. Single `evolve_sync()` wrapper at `api.py` boundary only.

2. **Protocol contract enforcement** — Every port defined as `typing.Protocol` with `@runtime_checkable`. Every implementation has a contract test in `tests/contracts/`. Contract test minimum: `isinstance` check + method signature verification + async behavior validation + error handling contract.

3. **Structured observability** — structlog events at every engine decision point (iteration start/end, mutation accepted/rejected, stop reason). ADK session events capture agent execution trajectories. Both channels are independently queryable.

4. **Component addressing** — Dot-separated qualified names (`generator.instruction`) unambiguously address components in single-agent, multi-agent, and workflow contexts. `ComponentSpec` dataclass provides construction and parsing.

5. **Error diagnostics** — `EvolutionError` → `ConfigurationError` | `EvaluationError` | `ReflectionError`. Every error carries `cause`, keyword-only context, and overrides `__str__` with diagnostic fields. Layer identification in error messages.

6. **Import boundary enforcement** — Hexagonal layer rules enforced by convention and code review. Engine receives adapters via constructor injection. New adapters wired through factory functions.

7. **Multi-surface validation** — Each evolvable surface (instruction text, output_schema Pydantic models, generate_content_config YAML) requires different validation strategies. ComponentHandler protocol abstracts this with `extract()`, `apply()`, `describe()` methods.

8. **Workflow structure preservation** — `clone_workflow_with_overrides()` recursively clones ADK workflow agents while preserving type, sub_agent order, LoopAgent iteration counts, and ParallelAgent concurrency semantics.

9. **Evolution state management** — `ParetoState`, `Candidate`, `IterationRecord`, `EvaluationBatch` form a state machine flowing through the engine. State is created, mutated during iterations, and frozen into immutable `EvolutionResult` at completion. This data flow model is the core architectural pattern — not just "in-memory Pareto state" but the entire lifecycle from initialization through iteration through result construction.

10. **Configuration propagation** — `EvolutionConfig` flows from public API through engine into adapters, proposers, and stoppers. Different components need different config subsets (reflection agent needs `reflection_model`; stopper needs `patience` and `max_iterations`; engine needs everything). The architecture must define how config is destructured and distributed.

### Growth-Phase Architectural Considerations

**Port evolution strategy:** Growth features (model selection evolution, batch evolution, hybrid optimization, experiment tracking) each require new ports or port extensions. The architecture must define how new Protocol methods or new Protocols are added without breaking existing adapter implementations. Options: (a) new standalone Protocols, (b) Protocol composition via multiple inheritance, (c) optional Protocol methods with default implementations.

**Critic preset registry:** The PRD and UX spec define string-shortcut critics (`critic="structured_output"`). The architecture must address: where does the registry live (module-level dict vs. discoverable plugin system)? How do Growth-phase community-contributed critics register?

**Result schema versioning:** The UX spec defines cross-session result comparison via `to_json()`/`from_json()`. Serialized results loaded later require forward-compatible schemas — `EvolutionResult` needs a version field and migration strategy, not just JSON round-tripping.

**Mock boundary definition:** Every new adapter must ship with a corresponding mock factory for testing in isolation. The existing `create_mock_adapter` pattern establishes the convention; Growth-phase features (gradient signal mocks, fleet orchestration mocks) must follow the same pattern.

## Starter Template Evaluation (Brownfield)

### Primary Technology Domain

**Python library** extending Google's Agent Development Kit (ADK). Not a web/mobile/CLI application — no starter template to select. This section documents the existing technical foundation and evaluates its readiness for MVP polish and Growth-phase features.

### Runtime Dependencies

| Dependency | Pinned Range | Latest (March 2026) | Layer | Purpose |
|-----------|-------------|---------------------|-------|---------|
| google-adk | >=1.22.0 | ~1.26.0 | adapters/ | ADK agent types, Runner, Session, Event |
| litellm | >=1.80.13 | ~1.81.16 | adapters/ | Multi-provider LLM proxy for reflection agents |
| structlog | >=25.5.0 | ~25.5.0 | domain/ + engine/ | Structured logging (only external lib in domain/) |
| nest-asyncio | >=1.6.0 | ~1.6.0 | api.py | Enables `asyncio.run()` in sync wrappers |

**Version pinning strategy:** Minimum-supported-version pins (`>=X.Y.Z`) are correct for a library — users bring their own versions. Architectural mitigation: ADK version matrix in CI testing against both `adk==1.22.0` (minimum) and `adk-latest` to catch compatibility regressions across the supported range.

### Development Toolchain

| Tool | Version | Purpose | Gate Level |
|------|---------|---------|-----------|
| uv | latest | Package management + build backend (`uv_build`) | Local + CI |
| ruff | latest | Linting (line-length 100) + formatting (line-length 88) | Pre-commit + CI |
| ty (Astral) | latest | Type checking (NOT mypy) | Pre-commit + CI |
| interrogate | latest | Docstring coverage enforcement (95% floor) | CI |
| docvet | latest | Docstring accuracy verification (signature match) | CI |
| pytest | latest | Testing with `asyncio_mode = "auto"` | Pre-commit (contracts) + CI (full) |

**Toolchain note on `ty`:** Astral's `ty` is a deliberate choice over mypy, aligned with the ruff/uv ecosystem. Risk mitigation: if `ty` gaps appear with ADK type stubs, document in a dedicated ADR rather than switching type checkers.

**Docstring double-gate:** `interrogate` enforces *coverage* (docstring exists), `docvet` enforces *accuracy* (docstring matches signature). Together they prevent the worst failure mode: docstrings that are present but wrong.

### Project Structure

```
src/gepa_adk/
├── api.py              # Public API: evolve(), evolve_sync(), evolve_group(), evolve_workflow()
├── domain/             # Pure domain models (stdlib + structlog only)
│   ├── models.py       # Candidate, ParetoState, IterationRecord, EvaluationBatch
│   ├── results.py      # EvolutionResult, MultiAgentEvolutionResult, WorkflowEvolutionResult
│   ├── config.py       # EvolutionConfig
│   └── exceptions.py   # EvolutionError hierarchy
├── ports/              # Protocol definitions (domain + stdlib only)
│   ├── scorer.py       # Scorer Protocol
│   ├── adapter.py      # AsyncGEPAAdapter Protocol
│   ├── stopper.py      # StopperProtocol
│   ├── component.py    # ComponentHandler Protocol
│   └── provider.py     # AgentProvider Protocol
├── adapters/           # External integrations (ADK, LiteLLM)
│   ├── adk/            # ADK agent execution, workflow cloning
│   ├── critics/        # CriticScorer implementations
│   ├── reflection/     # Reflection agent factories
│   ├── components/     # Per-surface handlers (text, AST, YAML)
│   └── stoppers/       # Patience, max iterations, convergence
├── engine/             # Core evolution loop (ports + domain + structlog)
│   └── engine.py       # AsyncGEPAEngine
└── utils/              # Shared utilities (stdlib + structlog)
    └── encoding.py     # Cross-platform encoding safety
```

**Hexagonal boundary enforcement:**
- `domain/` → stdlib only (exception: structlog)
- `ports/` → domain + stdlib
- `adapters/` → ports + domain + external libs
- `engine/` → ports + domain + structlog
- `utils/` → stdlib + structlog

### Testing Infrastructure

```
tests/
├── unit/               # Isolated unit tests per module
├── contracts/          # Protocol contract tests (1:1 with Protocol impls)
│   └── conftest.py     # Protocol auto-discovery registry (PROTOCOL_REGISTRY)
├── integration/        # Cross-layer integration tests
├── factories/          # Mock factories per adapter ({adapter_name}.py)
└── conftest.py         # Shared fixtures, async test configuration
```

**Three-layer testing strategy (ADR-005):**
- **Unit:** Isolated module tests, no external dependencies
- **Contract:** Every Protocol implementation has a contract test — `isinstance` check + method signature verification + async behavior validation + error handling contract
- **Integration:** Cross-layer tests validating adapter ↔ engine ↔ domain flows

**Coverage floor:** 85% line coverage enforced in CI.

**Structural invariant:** CI check that counts `@runtime_checkable` Protocol definitions in `ports/` against contract test files in `tests/contracts/`. If any Protocol lacks a contract test, CI fails. This is more precise than coverage percentage for ensuring architectural contracts are honored.

**Mock factory convention:** Every new adapter ships with a mock factory at `tests/factories/{adapter_name}.py`. Predictable paths for Growth-phase adapter testing.

### CI Pipeline

**Pre-commit local gates** (`.pre-commit-config.yaml`):
- `ruff format --check` — formatting
- `ruff check` — linting
- `ty check` — type checking
- `pytest tests/contracts/ -x --no-header` — sub-second Protocol contract validation

**GitHub Actions CI:**
- Full pre-commit gate chain
- `interrogate` — 95% docstring coverage
- `docvet check` — docstring accuracy
- `pytest` — full test suite with 85% coverage enforcement
- ADK version matrix: `adk==1.22.0` (minimum) + `adk-latest` (compatibility)

### Growth-Phase Readiness Assessment

| Concern | Current State | Gap | Mitigation |
|---------|--------------|-----|-----------|
| New adapters | Convention established | No structural enforcement | Protocol auto-discovery registry + CI structural check |
| Mock factories | Pattern exists (`create_mock_adapter`) | No location convention | Standardize to `tests/factories/{adapter_name}.py` |
| ADK compatibility | Minimum pin only | No multi-version testing | ADK version matrix in CI |
| Type checker gaps | `ty` in use | Potential ADK stub issues | ADR protocol: document gaps, don't switch |
| Pre-commit completeness | Referenced in CI | Local gates may be incomplete | Full `.pre-commit-config.yaml` with contract tests |

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Return type unification strategy
2. Port evolution strategy for Growth phase

**Important Decisions (Shape Architecture):**
3. Critic preset registry
4. Result schema versioning
5. Adapter internal organization

**Deferred Decisions (Post-MVP):**
6. Stopper registration pattern — keep direct instantiation, revisit if user friction emerges

### Decisions Already Established

| Decision | Source | Status |
|----------|--------|--------|
| Single `AsyncGEPAEngine` with adapter injection for all modes | Implementation | Shipped — single/multi/workflow determined by adapter, not engine topology |
| Config propagation: whole `EvolutionConfig` to engine, API destructures for wiring | Implementation | Working pattern — API reads specific fields for adapter/reflection setup, engine receives whole object |
| Component handler registry (module-level singleton dict) | `adapters/component_handlers.py` | Shipped — `ComponentHandlerRegistry` with `register()`/`get()` + convenience functions |
| Factory functions for named selectors | `adapters/candidate_selector.py`, `component_selector.py` | Shipped — `create_candidate_selector("pareto")`, `create_component_selector("round_robin")` |
| `evolve_workflow()` delegates to `evolve_group()` | `api.py` | Shipped — workflow discovery + delegation, no separate engine path |
| Stopper sub-package with `stop_callbacks` list | `adapters/stoppers/` + `EvolutionConfig` | Shipped — composite, timeout, threshold, file, signal, evaluations stoppers |

### Decision 1: Return Type Unification — Shared Protocol

**Decision:** Define a minimal `EvolutionResultProtocol` in `ports/` that both `EvolutionResult` and `MultiAgentEvolutionResult` satisfy structurally.

**Protocol surface (5 data fields + 2 computed properties):**

```python
@runtime_checkable
class EvolutionResultProtocol(Protocol):
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

**Rationale:**
- Consistent with ADR-002 structural subtyping — Protocol at the boundary, implementations stay independent
- Zero code change to existing domain types — both already satisfy the Protocol structurally
- Mode-specific fields (`valset_score`, `primary_agent`) remain on their concrete types
- Consumers who need the common shape program against the Protocol; consumers who need mode-specific data use the concrete type

**Contract test requirement:** `tests/contracts/test_evolution_result_protocol.py` verifies both result types pass `isinstance()` checks against the Protocol. Catches future field renames or removals that would silently break the contract.

**Affects:** Public API type hints, result comparison utilities, serialization layer

### Decision 2: Port Evolution — New Standalone Protocols

**Decision:** Each Growth-phase feature gets its own Protocol file in `ports/`. No Protocol composition or plugin systems.

**Rationale:**
- Matches the existing pattern — 11 Protocols already work this way
- Clean separation — no risk of breaking existing adapter implementations
- Engine constructor growth is manageable via optional parameters with `None` defaults (same pattern as `candidate_selector`, `component_selector`, `evaluation_policy`, `merge_proposer`)
- Each new Protocol gets its own contract test automatically via the CI structural check

**Naming convention:** Growth Protocol files use `{capability}_{role}.py` format. Example: `hybrid_gradient_provider.py`, not `gradient.py`. When `ports/` has 15+ files, the name must telegraph the capability without opening the file.

**PR rule:** Any PR that adds a new Protocol file to `ports/` must include a corresponding contract test skeleton in `tests/contracts/`. The CI structural invariant check (Protocol count vs. contract test count) enforces this automatically.

**Affects:** Growth-phase features (batch evolution, model selection, hybrid optimization, experiment tracking)

### Decision 3: Critic Presets — Factory Function (MVP)

**Decision:** Factory function for MVP (`create_critic()`), evolving to registry pattern for Growth phase when community critics arrive.

**Factory signature:**

```python
def create_critic(name: str, *, model: str | None = None) -> LlmAgent
```

If `model` is None, uses the default reflection model. Invalid name raises `ConfigurationError`.

**MVP presets:**

| Name | Schema | Instruction | Use Case |
|------|--------|------------|----------|
| `"structured_output"` | `CriticOutput` | `STRUCTURED_OUTPUT_CRITIC_INSTRUCTION` | Score output structure with per-dimension diagnostics |
| `"accuracy"` | `CriticOutput` | `ACCURACY_CRITIC_INSTRUCTION` | Score factual correctness with error diagnosis |
| `"relevance"` | `CriticOutput` | `RELEVANCE_CRITIC_INSTRUCTION` | Score topical relevance with coverage analysis |

> **Amendment (2026-03-06):** All presets use `CriticOutput` (not `SimpleCriticOutput` for structured_output). Each preset has a dedicated ASI-optimized instruction constant requesting `dimension_scores` and `actionable_guidance`. Rationale: GEPA paper (arXiv:2507.19457) defines Actionable Side Information as "the text-optimization analogue of a gradient." `CriticOutput` fields map directly to GEPA's ASI contract — `feedback` = diagnostic text, `dimension_scores` = multi-objective Pareto input, `actionable_guidance` = targeted reflector input. Maximizing ASI quality improves evolution outcomes. gepa-adk is the only GEPA implementation providing structured ASI schemas and preset critics.

**Growth phase presets (trajectory-dependent):**

| Name | Schema | Evaluation Surface | Pipeline Requirement |
|------|--------|--------------------|---------------------|
| `"tool_use"` | `CriticOutput` | Action trajectory (tool selection, arguments, sequencing, efficiency) | Requires trajectory data in `CriticScorer._format_critic_input()` |
| `"safety"` | `CriticOutput` | Content + actions (policy compliance, data leakage, boundary adherence) | Content works now; action evaluation needs trajectory |
| `"efficiency"` | `CriticOutput` | Action trajectory (step count, token cost, redundancy, directness) | Requires step count and token usage in critic input |

Growth phase presets require a pipeline change: `CriticScorer._format_critic_input()` must accept optional trajectory data so the critic can evaluate the agent's *behavior*, not just its *output*. This enables evolving agent instructions for better tool-use strategy (e.g., an agent using Playwright MCP, search APIs, or database tools).

**Location:** `adapters/scoring/critic_scorer.py` (post-reorganization), re-exported via `gepa_adk.__init__`.

> **Tech Debt (2026-03-07, Story 3.1 implementation review):** The MVP uses two parallel dicts keyed by preset name: `critic_presets` (name → description) and `_PRESET_INSTRUCTIONS` (name → instruction text). Adding a preset to one but not the other is a silent bug. When Growth phase presets are added (Stories 3.4-3.6), consolidate into a single data structure (e.g., `NamedTuple` or `dataclass` mapping name → description + instruction). Acceptable for 3 entries; becomes a maintenance risk at 6+.

**Test matrix:** Three deterministic tests — one per preset name — plus invalid-name error test. No LLM calls required.

**Affects:** Public API (`evolve(critic="structured_output")`), UX progressive disclosure

### Decision 4: Result Schema Versioning — Domain-Layer Serialization

**Decision:** Add `schema_version: int = 1` frozen field to result types. Add `to_dict()` instance method and `from_dict()` class method using stdlib only.

**Design rules:**
- `to_dict()` outputs `{"schema_version": N, ...}` — version is always included
- `from_dict()` accepts `schema_version <= CURRENT_VERSION` — explicit migration per version step
- `from_dict()` always returns the current-version type — missing Growth-phase fields get `None` defaults
- Output `schema_version` is always `CURRENT_VERSION` regardless of input version — version is output metadata, not preserved from serialized data
- Unknown `schema_version > CURRENT_VERSION` raises `ConfigurationError` with migration guidance

**Rationale:** Keeps everything in the domain layer with stdlib only (respects hexagonal boundaries). Version is part of the frozen record. Migration logic lives alongside the model.

**Test strategy:** Migration test fixtures per schema version in `tests/fixtures/evolution_result_v1.json`. When v2 ships, v1 fixture still passes `from_dict()` and produces a valid current-version result. Every test asserts `result.schema_version == CURRENT_VERSION`.

**Affects:** Cross-session result comparison, result persistence, experiment tracking (Growth)

### Decision 5: Adapter Organization — Sub-Packages with Re-Exports

**Decision:** Reorganize `adapters/` into sub-packages by concern now. Preserve existing import paths via `adapters/__init__.py` re-exports.

**Rationale:** A two-tier system (flat old code + nested new code) creates contributor confusion. One migration now, clean convention from then on.

**Package structure:**

```
adapters/
├── __init__.py          # Re-exports everything at old import paths
├── execution/           # AgentExecutor, TrialBuilder
├── scoring/             # CriticScorer, create_critic()
├── evolution/           # ADKAdapter, MultiAgentAdapter
├── selection/           # CandidateSelector, ComponentSelector, EvaluationPolicy
├── components/          # ComponentHandlerRegistry, handlers
├── stoppers/            # Already a sub-package (no change)
├── workflow/            # find_llm_agents, clone_workflow_with_overrides
└── media/               # VideoBlobService, future multimodal adapters
```

8 sub-packages. Each has a clear single concern.

**Migration safety:** Deprecation test verifies every old import path in `adapters/__init__.py` resolves to the same object as the new sub-package path: `assert adapters.CriticScorer is adapters.scoring.CriticScorer`. One test per re-exported symbol. Runs in CI to catch accidental re-export removal.

**Affects:** All adapter imports (preserved via re-exports), contributor onboarding, Growth-phase adapter placement

### Decision 6: Stopper Registration — Keep Direct Instantiation

**Decision:** No factory function or registry for stoppers. Users continue to instantiate directly.

**Rationale:** Stoppers take constructor arguments that vary per type (`TimeoutStopper(seconds=300)` vs `ThresholdStopper(target=0.95)`). A generic factory adds indirection without simplifying the API. The current pattern is explicit and clean: `config = EvolutionConfig(stop_callbacks=[TimeoutStopper(seconds=300)])`.

**Revisit trigger:** If user feedback indicates friction with stopper discovery or configuration, introduce a factory in Growth phase.

### Decision Impact Analysis

**Implementation Sequence:**
1. D1 (Result Protocol) — zero code change to domain types, add Protocol + contract test
2. D4 (Schema versioning) — add `schema_version` field + `to_dict()`/`from_dict()` to result types
3. D3 (Critic factory) — add `create_critic()` to `adapters/scoring/critic_scorer.py` + re-export
4. D5 (Adapter reorganization) — restructure adapters/ into sub-packages + re-exports + deprecation tests
5. D2 (Port evolution) — naming convention + PR rule, no code change until Growth features arrive
6. D6 (Stoppers) — no action, document decision

**Cross-Decision Dependencies:**
- D1 (Protocol) enables D4 (versioning) — `to_dict()`/`from_dict()` can reference the Protocol for shared serialization logic
- D5 (reorganization) should happen before D3 (critic factory) — so `create_critic()` is placed directly in the new `adapters/scoring/` sub-package
- D2 (port evolution) + D5 (adapter organization) together define where Growth-phase code lands: new Protocol in `ports/{capability}_{role}.py`, new adapter in `adapters/{concern}/`

## Implementation Patterns & Consistency Rules

### Conflict Analysis: Where Agents Diverge

The `project-context.md` covers 95 rules for syntax, naming, and layer boundaries. The remaining conflict points are *procedural* — agents know the rules but don't know the *recipes* for extending the codebase:

| Conflict Area | What Could Go Wrong |
|--------------|-------------------|
| Adding a new adapter | Agent puts class in wrong sub-package, skips contract test, forgets mock factory, doesn't update `__init__.py` |
| Adding a new Protocol | Agent puts helper types in Protocol file instead of `domain/types.py`, uses `pass` instead of `...`, forgets `@runtime_checkable` |
| Extending the engine | Agent adds hard dependency instead of optional constructor parameter, bypasses Protocol interface, adds string resolution in engine |
| Adding serialization | Agent uses Pydantic in domain layer (violates hexagonal boundary), forgets version field |
| Structlog events | Agent uses inconsistent event names, omits required context fields, logs at wrong level, doesn't bind evolution_id |
| Error creation | Agent uses positional args, forgets `from e`, omits context fields |
| Growing the public API | Agent exports from wrong module, breaks progressive disclosure, uses `Any` in parameter types |
| Extending config | Agent adds required field without default, breaks every existing `EvolutionConfig()` call |
| Adding evolvable surface | Agent creates handler but doesn't register it, skips component name constant |
| Modifying domain models | Agent changes field set but doesn't update test fixtures, leaving broken tests |

### Pattern 1: New Adapter Implementation Recipe

**Step sequence:**
0. **Check for existing adapter** — search `adapters/` for the Protocol name to avoid duplicating an implementation
1. Identify which Protocol the adapter implements (or define new Protocol first — see Pattern 2)
2. Create adapter class in appropriate `adapters/{concern}/` sub-package
3. Class uses `@dataclass(slots=True, kw_only=True)` if stateful, plain class if stateless
4. Class does NOT inherit from the Protocol (structural subtyping per ADR-002)
5. Create contract test in `tests/contracts/test_{protocol_name}.py` (minimum 4 tests — see Pattern 2)
6. Create mock factory in `tests/factories/{adapter_name}.py` following the shape convention: `create_mock_{thing}(config: {Thing}Config) -> Configurable{Thing}` — config dataclass controls behavior (what to return, when to error), making test setup declarative
7. Update `adapters/{concern}/__init__.py` with new exports
8. Update `adapters/__init__.py` re-exports if needed for backward compatibility
9. Update top-level `gepa_adk/__init__.py` if it's part of the public API (explicit named imports, no `import *`)

**Template:**

```python
# adapters/{concern}/{adapter_name}.py
"""Module docstring listing __all__ contents."""

import structlog

from gepa_adk.domain.models import ...
from gepa_adk.domain.exceptions import ...

logger = structlog.get_logger(__name__)


class NewAdapter:
    """One-line summary.

    Longer description if needed.

    Attributes:
        field_name: Description.
    """

    def __init__(self, *, dep1: Type1, dep2: Type2) -> None:
        """Initialize NewAdapter.

        Args:
            dep1: Description.
            dep2: Description.
        """
        self._dep1 = dep1
        self._dep2 = dep2

    async def protocol_method(self, ...) -> ReturnType:
        """Docstring matching Protocol method."""
        logger.info("adapter.operation_name", context_field=value)
        ...


__all__ = ["NewAdapter"]
```

**Anti-patterns:**
- Inheriting from the Protocol class
- Putting the adapter in `domain/` or `engine/`
- Creating a new adapter without a contract test
- Importing external libraries in `domain/` or `ports/`
- Creating mock factories with imperative setup instead of declarative config dataclass

### Pattern 2: New Protocol Definition Recipe

**Step sequence:**
1. Create Protocol file in `ports/` using naming convention: `{capability}_{role}.py`
2. Protocol uses `@runtime_checkable` decorator
3. Method bodies are `...` (Ellipsis), never `pass` or `raise NotImplementedError`
4. Helper/data types go in `domain/types.py`, NOT in the Protocol file
5. Create contract test skeleton immediately: `tests/contracts/test_{protocol_name}.py`
6. Update `ports/__init__.py` exports

**Template:**

```python
# ports/{capability}_{role}.py
"""Module docstring listing __all__ contents."""

from typing import Protocol, runtime_checkable

from gepa_adk.domain.models import DomainType


@runtime_checkable
class NewProtocol(Protocol):
    """One-line summary of the Protocol contract.

    Longer description of when and how implementations are used.
    """

    async def method_name(self, arg: ArgType) -> ReturnType:
        """What this method must do.

        Args:
            arg: Description.

        Returns:
            Description.

        Raises:
            SpecificError: When this happens.
        """
        ...


__all__ = ["NewProtocol"]
```

**Minimum contract test bar (4 tests required):**

```python
class TestNewProtocol:
    def test_is_runtime_checkable(self):
        impl = ConcreteImpl()
        assert isinstance(impl, NewProtocol)

    def test_method_signatures_are_async(self):
        import inspect
        for name in ["method_a", "method_b"]:
            assert inspect.iscoroutinefunction(getattr(NewProtocol, name))

    async def test_happy_path_returns_expected_type(self):
        impl = ConcreteImpl()
        result = await impl.method_a(valid_input)
        assert isinstance(result, ExpectedType)

    async def test_error_contract(self):
        impl = ConcreteImpl()
        with pytest.raises(SpecificError):
            await impl.method_a(invalid_input)
```

**Anti-patterns:**
- Putting implementation logic in the Protocol file
- Using `abc.ABC` or `abc.abstractmethod`
- Defining data types alongside the Protocol
- Forgetting `@runtime_checkable`
- Shipping a Protocol without a contract test skeleton

### Pattern 3: Engine Integration Recipe

**Rules:**
- New capabilities are **optional constructor parameters** with `None` defaults
- Engine conditionally uses the capability: `if self._new_capability is not None:`
- Engine NEVER imports adapter implementations directly (except pragmatic defaults for selectors — established exceptions)
- New capabilities are Protocol-typed in the constructor
- **The engine never sees strings** — the API layer (`api.py`) resolves all string shortcuts to Protocol instances before passing to the engine

**Template addition to engine constructor:**

```python
class AsyncGEPAEngine(Generic[DataInst, Trajectory, RolloutOutput]):
    def __init__(
        self,
        ...,  # existing params
        new_capability: NewProtocol | None = None,  # optional, Protocol-typed
    ) -> None:
        self._new_capability = new_capability
```

**Usage in engine loop:**

```python
if self._new_capability is not None:
    result = await self._new_capability.method_name(...)
    logger.info("engine.new_capability.applied", result=result)
```

**Anti-patterns:**
- Making the new capability a required parameter (breaks existing callers)
- Importing the adapter class directly instead of using the Protocol type
- Adding capability logic outside the engine loop (e.g., in `__init__`)
- Adding string-to-instance resolution inside the engine (belongs in `api.py`)

### Pattern 4: Structlog Event Convention

**Evolution run traceability:** At the start of `engine.run()`, bind an `evolution_id` UUID to the logger:

```python
async def run(self) -> EvolutionResult:
    logger = self._logger.bind(evolution_id=str(uuid4()))
    ...
```

All subsequent events in that run automatically carry the ID, making multi-run logs filterable.

**Log level guide:**

| Level | When | Examples |
|-------|------|---------|
| `info` | Engine decision points a user monitoring evolution cares about | Iteration start/end, candidate accepted/rejected, stop triggered |
| `debug` | Internal adapter operations, detailed data | Evaluation scores, reflection prompt construction, component extraction |
| `warning` | Recoverable issues that may affect quality | Fallback to default, retry succeeded, deprecated usage detected |
| `error` | Operations that failed and will affect the result | Evaluation failure, reflection timeout, schema validation failure |

**Event naming rules:**

| Context | Format | Example |
|---------|--------|---------|
| Engine decision point | `engine.{action}` | `engine.iteration.started`, `engine.candidate.accepted` |
| Adapter operation | `adapter.{operation}` | `adapter.evaluate.completed`, `adapter.reflection.started` |
| Configuration | `config.{field}.{state}` | `config.reflection_prompt.empty`, `config.merge.disabled` |
| Validation | `validation.{subject}.{result}` | `validation.schema.passed`, `validation.component.rejected` |
| Stopper | `stopper.{type}.{action}` | `stopper.patience.triggered`, `stopper.timeout.reached` |

**Required context fields per event type:**

| Event Category | Required Fields |
|---------------|----------------|
| Iteration events | `iteration`, `score`, `best_score` |
| Candidate events | `iteration`, `candidate_idx`, `component` |
| Evaluation events | `iteration`, `batch_size`, `duration_seconds` |
| Error events | `error_type`, `cause` (if chained), layer identifier |
| Stop events | `reason`, `iteration`, `stagnation_counter` |

**Anti-patterns:**
- Using `print()` instead of structlog
- Creating logger inside methods instead of module-level
- Logging sensitive data (full prompt texts) at INFO level — use DEBUG
- Inconsistent event names across similar operations
- Forgetting to bind `evolution_id` at run start

### Pattern 5: Domain Serialization Convention

```python
CURRENT_SCHEMA_VERSION = 1

@dataclass(slots=True, frozen=True, kw_only=True)
class EvolutionResult:
    schema_version: int = CURRENT_SCHEMA_VERSION
    ...

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "schema_version": self.schema_version,
            "original_score": self.original_score,
            ...
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvolutionResult:
        """Deserialize from dict with version migration.

        Args:
            data: Serialized result dict.

        Returns:
            Current-version EvolutionResult.

        Raises:
            ConfigurationError: If schema_version > CURRENT_SCHEMA_VERSION.
        """
        version = data.get("schema_version", 1)
        if version > CURRENT_SCHEMA_VERSION:
            raise ConfigurationError(...)
        migrated = _migrate(data, from_version=version)
        return cls(**migrated)
```

**Rules:**
- `to_dict()` uses stdlib only — no Pydantic, no third-party serializers
- `from_dict()` always returns current-version type
- Missing fields get `None` defaults
- Version migration is explicit per-step: `_migrate_v1_to_v2()`, `_migrate_v2_to_v3()`
- `IterationRecord` nested inside results serializes/deserializes recursively

### Pattern 6: Public API Extension Recipe

**Progressive disclosure rules:**
- Simple case has fewest parameters with good defaults
- Advanced options are keyword-only with `None` defaults
- String shortcuts resolve to Protocol implementations via factory functions *in the API layer*
- Return type is a frozen domain dataclass
- **No `Any` in parameter types** — `api.py` is the public surface, users see it in their IDE

**Wiring sequence (established by `evolve()`):**
1. Resolve dependencies (session service, app, runner)
2. Build subsidiary objects (scorer, reflection agent, executor)
3. Build adapter (inject dependencies)
4. Build initial candidate
5. Instantiate engine (inject adapter + optional protocols)
6. `await engine.run()` → return result

**Re-export chain:**
- Function defined in `api.py`
- Exported in `gepa_adk/__init__.py` via explicit named import (no `from api import *`)
- `__all__` in `__init__.py` includes the function name
- Documented in `docs/reference/`

### Pattern 7: Config Extension Recipe

**Rules:**
- New field MUST have a default value — `EvolutionConfig()` with no arguments must always work
- If the engine reads the field: access via `self.config.new_field` in the engine loop
- If only the API layer uses it for wiring: read in `api.py`, do NOT pass to engine
- Field type should be as specific as possible — avoid `Any`

**Template:**

```python
@dataclass(slots=True, kw_only=True)
class EvolutionConfig:
    ...  # existing fields
    new_field: FieldType = sensible_default  # always has a default
```

**Required test:** Add to `tests/unit/domain/test_config.py`:

```python
def test_default_config_includes_new_field(self):
    config = EvolutionConfig()
    assert config.new_field == sensible_default
```

**Anti-patterns:**
- Adding a required field (no default) — breaks every existing caller
- Using `field(default=MISSING)` or sentinel values
- Adding the field without a test verifying the default

### Pattern 8: Component Handler Registration Recipe

**Step sequence:**
1. Define the component name constant in `domain/types.py`: `COMPONENT_TOOL_CONFIG = "tool_config"`
2. Create handler class implementing `ComponentHandler` Protocol (methods: `serialize()`, `apply()`, `restore()`)
3. Register at module load in `adapters/components/component_handlers.py`:
   ```python
   component_handlers.register(COMPONENT_TOOL_CONFIG, ToolConfigHandler())
   ```
4. Add contract test in `tests/contracts/` verifying the handler satisfies `ComponentHandler`
5. Update default `components` list in `evolve()` if the new surface should be included by default
6. Add documentation for the new surface in `docs/guides/`

**Anti-patterns:**
- Creating a handler without registering it in the singleton
- Forgetting the component name constant (using raw string `"tool_config"` everywhere)
- Registering in `__init__` instead of at module load time

### Pattern 9: Test Fixture Migration Recipe

When a domain model changes (new field, renamed field, changed type):

**Step sequence:**
1. Update the domain model (e.g., add field to `EvolutionResult`)
2. Update serialized test fixtures in `tests/fixtures/` (JSON files, if schema versioning applies)
3. Update factory functions in `tests/fixtures/adapters.py` or relevant `conftest.py`
4. Run full test suite (`pytest`) — catch any fixture that constructs the changed type with now-missing/extra fields
5. If the change adds a field with a default, verify all existing fixture constructions still work without explicitly providing the new field

**Anti-patterns:**
- Changing a domain model without running the full test suite
- Updating only the tests you're writing, leaving existing fixtures broken
- Adding a field to a frozen dataclass without updating `to_dict()`/`from_dict()` if serialization exists

### Enforcement Guidelines

**All AI Agents MUST:**
1. Check `project-context.md` before implementing any code — it has 95 rules
2. Follow the appropriate recipe (Patterns 1-9) when extending the codebase
3. Run `ruff format && ruff check --fix && docvet check && ty check src tests` before marking any task complete
4. Create contract tests (minimum 4 tests) for any new Protocol implementation
5. Create mock factories (declarative config pattern) for any new adapter
6. Update `__all__` in every modified module
7. Run full test suite after modifying domain models to catch fixture breakage

**Pattern Enforcement:**
- CI structural check: Protocol count in `ports/` must equal contract test count in `tests/contracts/`
- CI coverage: 85% floor catches missing test coverage for new code
- Pre-commit hooks: formatting, linting, type checking, contract tests
- Code review: verify recipe steps were followed (contract test? mock factory? `__init__.py` updated? `__all__` updated?)

## Project Structure & Boundaries

### Requirements to Structure Mapping

| Capability Area | Primary Location | Supporting Locations |
|----------------|-----------------|---------------------|
| Single-agent evolution (~12 FRs) | `engine/async_engine.py`, `api.py:evolve()` | `adapters/evolution/adk_adapter.py`, `domain/models.py` |
| Multi-agent pipeline (~7 FRs) | `api.py:evolve_group()`, `adapters/evolution/multi_agent.py` | `adapters/selection/component_selector.py`, `domain/types.py` |
| Workflow structure (~5 FRs) | `api.py:evolve_workflow()`, `adapters/workflow/` | `adapters/evolution/multi_agent.py` |
| Multi-surface components (~9 FRs) | `adapters/components/`, `ports/component_handler.py` | `domain/types.py` (component name constants) |
| Enterprise observability (~5 FRs) | `engine/async_engine.py` (structlog), `adapters/execution/` | `domain/stopper.py` (StopperState) |
| Extension protocols (~3 FRs) | `ports/` (new Protocol files), `tests/contracts/` | `adapters/{concern}/` (new implementations) |

### Complete Project Directory Structure (Target State)

```
gepa-adk/
├── pyproject.toml                          # All tool config: uv, ruff, ty, pytest, interrogate
├── uv.lock                                 # Lockfile (uv)
├── .pre-commit-config.yaml                 # Local gate chain: ruff, ty, contract tests
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── tests.yml                       # pytest + coverage (85% floor) + ADK version matrix
│       ├── type-check.yml                  # ty check on PR ready_for_review
│       ├── boundaries.yml                  # Hexagonal boundary enforcement (grep-based)
│       ├── docs.yml                        # MkDocs build
│       ├── codeql.yml                      # Security analysis
│       └── release-please.yml              # Automated release PR
├── scripts/                                # CI helper scripts
│   ├── check_boundaries.sh                 # Hexagonal layer import enforcement
│   └── check_protocol_coverage.py          # Protocol count vs contract test count
├── examples/                               # Runnable standalone scripts for users
│   ├── single_agent_basic.py               # Minimal evolve() example
│   ├── single_agent_critic.py              # Custom critic agent
│   ├── multi_agent_pipeline.py             # evolve_group() with 2 agents
│   ├── workflow_evolution.py               # evolve_workflow() with SequentialAgent
│   └── custom_stopper.py                   # StopperProtocol implementation
├── docs/
│   ├── mkdocs.yml
│   ├── index.md
│   ├── getting-started.md
│   ├── concepts/                           # Conceptual guides
│   │   ├── gepa-fundamentals.md
│   │   ├── single-agent-evolution.md
│   │   ├── multi-agent-evolution.md
│   │   └── workflow-agents.md
│   ├── guides/                             # How-to guides
│   │   ├── single-agent.md
│   │   ├── multi-agent.md
│   │   ├── critic-agents.md
│   │   ├── reflection-prompts.md
│   │   ├── stoppers.md
│   │   ├── workflows.md
│   │   ├── hybrid-optimization.md          # Growth-phase placeholder
│   │   ├── batch-evolution.md              # Growth-phase placeholder
│   │   └── experiment-tracking.md          # Growth-phase placeholder
│   ├── reference/                          # API reference (every __init__.py symbol documented here)
│   │   ├── glossary.md
│   │   └── index.md
│   ├── adr/                                # Architecture Decision Records
│   │   ├── index.md                        # Includes reserved numbers for new decisions
│   │   ├── ADR-000-hexagonal-architecture.md
│   │   ├── ADR-001-async-first-architecture.md
│   │   ├── ADR-002-protocol-for-interfaces.md
│   │   ├── ADR-005-three-layer-testing.md
│   │   ├── ADR-006-external-library-integration.md
│   │   ├── ADR-008-structured-logging.md
│   │   ├── ADR-009-exception-hierarchy.md
│   │   ├── ADR-010-docstring-quality.md
│   │   ├── ADR-011-cross-platform-encoding.md
│   │   ├── ADR-012-multi-agent-component-addressing.md
│   │   ├── ADR-013-result-type-protocol.md          # Reserved (Decision 1)
│   │   ├── ADR-014-adapter-reorganization.md         # Reserved (Decision 5)
│   │   └── ADR-015-result-schema-versioning.md       # Reserved (Decision 4)
│   └── contributing/
│       ├── architecture.md                 # Pointer: architecture doc, ADRs, project-context, routing table
│       ├── docstring-templates.md
│       └── releasing.md
│
├── src/gepa_adk/
│   ├── __init__.py                         # Curated public API (every symbol in docs/reference/)
│   ├── py.typed                            # PEP 561 marker (zero-byte, enables downstream type checking)
│   ├── api.py                              # Public entry: evolve(), evolve_sync(), evolve_group(), evolve_workflow()
│   │
│   ├── domain/                             # stdlib + structlog ONLY — COLD (stable models)
│   │   ├── __init__.py
│   │   ├── models.py                       # Candidate, EvolutionResult, MultiAgentEvolutionResult, IterationRecord
│   │   ├── state.py                        # ParetoState, ParetoFrontier
│   │   ├── config.py                       # EvolutionConfig
│   │   ├── exceptions.py                   # EvolutionError hierarchy
│   │   ├── types.py                        # Type aliases, component name constants, enums
│   │   └── stopper.py                      # StopperState (frozen snapshot for stopper callbacks)
│   │
│   ├── ports/                              # domain + stdlib ONLY — one Protocol per file — COLD (stable contracts)
│   │   ├── __init__.py
│   │   ├── adapter.py                      # AsyncGEPAAdapter Protocol
│   │   ├── scorer.py                       # Scorer Protocol
│   │   ├── stopper.py                      # StopperProtocol
│   │   ├── component_handler.py            # ComponentHandler Protocol
│   │   ├── agent_provider.py               # AgentProvider Protocol
│   │   ├── agent_executor.py               # AgentExecutorProtocol
│   │   ├── proposer.py                     # ProposerProtocol
│   │   ├── candidate_selector.py           # CandidateSelectorProtocol (split from selector.py)
│   │   ├── evaluation_policy.py            # EvaluationPolicyProtocol (split from selector.py)
│   │   ├── component_selector.py           # ComponentSelectorProtocol (split from selector.py)
│   │   ├── video_blob_service.py           # VideoBlobServiceProtocol
│   │   ├── evolution_result.py             # EvolutionResultProtocol (→ ADR-013)
│   │   └── {capability}_{role}.py          # Growth-phase Protocols (Decision 2 naming convention)
│   │
│   ├── engine/                             # ports + domain + structlog — HOT (loop changes)
│   │   ├── __init__.py
│   │   └── async_engine.py                 # AsyncGEPAEngine (single engine, adapter-injected modes)
│   │
│   ├── adapters/                           # ports + domain + external libs — HOT (new features) (→ ADR-014)
│   │   ├── __init__.py                     # Re-exports preserving old import paths (see template below)
│   │   ├── execution/                      # Agent execution infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── agent_executor.py           # AgentExecutor (unified runner)
│   │   │   └── trial_builder.py            # TrialBuilder (reflective dataset construction)
│   │   ├── scoring/                        # Scoring infrastructure
│   │   │   ├── __init__.py
│   │   │   └── critic_scorer.py            # CriticScorer + create_critic() factory (Decision 3)
│   │   ├── evolution/                      # Core adapter implementations
│   │   │   ├── __init__.py
│   │   │   ├── adk_adapter.py              # ADKAdapter (single-agent)
│   │   │   └── multi_agent.py              # MultiAgentAdapter (multi-agent/workflow)
│   │   ├── selection/                      # Selection strategies
│   │   │   ├── __init__.py
│   │   │   ├── candidate_selector.py       # Pareto, CurrentBest, EpsilonGreedy + factory
│   │   │   ├── component_selector.py       # RoundRobin, All + factory
│   │   │   └── evaluation_policy.py        # Full, Subset policies
│   │   ├── components/                     # Evolvable surface handlers
│   │   │   ├── __init__.py
│   │   │   └── component_handlers.py       # Registry + Instruction/OutputSchema/GenerateConfig handlers
│   │   ├── stoppers/                       # Stop condition implementations (existing sub-package)
│   │   │   ├── __init__.py
│   │   │   ├── composite.py
│   │   │   ├── evaluations.py
│   │   │   ├── file.py
│   │   │   ├── signal.py
│   │   │   ├── threshold.py
│   │   │   └── timeout.py
│   │   ├── workflow/                       # Workflow utilities
│   │   │   ├── __init__.py
│   │   │   └── workflow.py                 # find_llm_agents, clone_workflow_with_overrides
│   │   └── media/                          # Multimodal adapters
│   │       ├── __init__.py
│   │       └── video_blob_service.py       # VideoBlobService
│   │
│   └── utils/                              # stdlib + structlog — COLD (utility additions)
│       ├── __init__.py
│       └── encoding.py                     # Cross-platform encoding safety
│
└── tests/
    ├── conftest.py                         # Root: MockScorer, MockExecutor, trainset/valset samples
    ├── unit/                               # Layer: fast, isolated — HOT (every feature)
    │   ├── conftest.py
    │   ├── domain/
    │   │   ├── test_models.py
    │   │   ├── test_config.py
    │   │   ├── test_state.py
    │   │   └── test_exceptions.py
    │   ├── engine/
    │   │   ├── conftest.py                 # mock_adapter, sample_config, sample_candidate
    │   │   └── test_async_engine.py
    │   ├── adapters/
    │   │   ├── conftest.py
    │   │   ├── test_critic_scorer.py
    │   │   ├── test_adk_adapter.py
    │   │   ├── test_multi_agent.py
    │   │   ├── test_component_handlers.py
    │   │   ├── test_stoppers.py
    │   │   └── test_workflow.py
    │   └── api/                            # API wiring tests (no LLM calls)
    │       ├── conftest.py                 # Mock adapters, mock engine
    │       ├── test_evolve.py              # evolve() wiring, parameter validation
    │       ├── test_evolve_group.py        # evolve_group() wiring, qualified names
    │       ├── test_evolve_workflow.py      # evolve_workflow() delegation
    │       └── test_create_critic.py       # create_critic() factory (Decision 3)
    ├── contracts/                           # Layer: Protocol compliance (1:1 with ports/)
    │   ├── conftest.py                     # PROTOCOL_REGISTRY auto-discovery (see implementation below)
    │   ├── test_adapter_protocol.py
    │   ├── test_scorer_protocol.py
    │   ├── test_stopper_protocol.py
    │   ├── test_component_handler_protocol.py
    │   ├── test_agent_executor_protocol.py
    │   ├── test_proposer_protocol.py
    │   ├── test_candidate_selector_protocol.py
    │   ├── test_evaluation_policy_protocol.py
    │   ├── test_component_selector_protocol.py
    │   ├── test_agent_provider_protocol.py
    │   └── test_evolution_result_protocol.py
    ├── integration/                        # Layer: cross-layer, real services
    │   ├── conftest.py                     # Real session services, test agents
    │   ├── adk/                            # Tests requiring google-adk runtime
    │   │   ├── conftest.py                 # pytestmark = [pytest.mark.integration, pytest.mark.api]
    │   │   ├── test_single_agent_evolution.py
    │   │   └── test_multi_agent_evolution.py
    │   ├── ollama/                          # Tests requiring local Ollama
    │   │   ├── conftest.py                 # pytestmark = [pytest.mark.integration, pytest.mark.requires_ollama]
    │   │   └── test_reflection_with_ollama.py
    │   └── workflow/                        # Tests requiring workflow agent types
    │       ├── conftest.py
    │       └── test_workflow_evolution.py
    ├── fixtures/                            # Shared test DATA and legacy mock adapter factory
    │   ├── adapters.py                     # create_mock_adapter, AdapterConfig, OutputMode (legacy)
    │   ├── evolution_result_v1.json        # Decision 4: versioned serialization fixtures
    │   └── ...
    └── factories/                          # NEW mock factories per adapter (Pattern 1 convention)
        ├── __init__.py
        └── {adapter_name}.py              # create_mock_{thing}(config: {Thing}Config) pattern
```

**Key distinctions:**
- `tests/fixtures/` — shared test **data** (JSON files, sample inputs) and the legacy `create_mock_adapter` factory
- `tests/factories/` — **new** mock factories following the `create_mock_{thing}(config)` declarative pattern
- `examples/` — **runnable standalone scripts** for users, not tests; syntax-checked in CI (`python -m py_compile`)

### Protocol Auto-Discovery Registry

```python
# tests/contracts/conftest.py
"""Auto-discover all @runtime_checkable Protocols in ports/."""

import importlib
import inspect
import pkgutil
from typing import Protocol, runtime_checkable

import pytest

import gepa_adk.ports as ports_pkg


def discover_protocols() -> dict[str, type]:
    """Discover all @runtime_checkable Protocols in the ports package."""
    protocols = {}
    for _importer, modname, _ispkg in pkgutil.iter_modules(ports_pkg.__path__):
        module = importlib.import_module(f"gepa_adk.ports.{modname}")
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                isinstance(obj, type)
                and issubclass(obj, Protocol)
                and getattr(obj, "_is_runtime_checkable", False)
            ):
                protocols[name] = obj
    return protocols


PROTOCOL_REGISTRY = discover_protocols()

pytestmark = pytest.mark.contract
```

### Adapter Re-Export Template

```python
# adapters/__init__.py
"""Adapter layer re-exports for backward compatibility.

All public symbols are re-exported from their sub-package locations.
New code should import from sub-packages directly.
"""

# Evolution adapters
from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.evolution.multi_agent import MultiAgentAdapter

# Scoring
from gepa_adk.adapters.scoring.critic_scorer import CriticScorer
from gepa_adk.adapters.scoring.critic_scorer import create_critic

# Execution
from gepa_adk.adapters.execution.agent_executor import AgentExecutor
from gepa_adk.adapters.execution.trial_builder import TrialBuilder

# ... every public symbol that was previously importable from adapters/

__all__ = [
    "ADKAdapter",
    "MultiAgentAdapter",
    "CriticScorer",
    "create_critic",
    "AgentExecutor",
    "TrialBuilder",
    # ... complete list
]
```

### Public API Curation Rule

Every symbol in `gepa_adk/__init__.py.__all__` must appear in `docs/reference/`. If it's not documented, it's not public. This prevents internal types from leaking into the public API surface.

### Architectural Boundaries

**Layer Communication Diagram:**

```
┌──────────────────────────────────────────────────────┐
│  api.py  (public surface)                            │
│  ┌─────────────────────────────────────────────────┐ │
│  │  engine/  (orchestration)                       │ │
│  │  ┌────────────┐  ┌───────────┐  ┌───────────┐  │ │
│  │  │  ports/    │←─│  domain/  │──│  utils/   │  │ │
│  │  └─────┬──────┘  └───────────┘  └───────────┘  │ │
│  │        │ Protocol contracts                      │ │
│  │  ┌─────▼──────┐                                  │ │
│  │  │ adapters/  │ (external lib integration)       │ │
│  │  └────────────┘                                  │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**Boundary rules:**
- `api.py` → imports from all layers; wires adapters to engine via constructor injection
- `engine/` → imports `ports/` (Protocol types) and `domain/` (models, config); receives adapters as constructor arguments
- `adapters/` → imports `ports/` (Protocol contracts) and `domain/` (models); imports external libs (ADK, LiteLLM)
- `ports/` → imports `domain/` only; one Protocol per file
- `domain/` → stdlib + structlog ONLY; no upward imports
- `utils/` → stdlib + structlog ONLY; imported by any layer

**CI Boundary Enforcement (`scripts/check_boundaries.sh`):**

```bash
#!/bin/bash
set -euo pipefail
echo "Checking hexagonal layer boundaries..."

# No ADK/LiteLLM imports outside adapters/
! grep -rn 'from google\.' src/gepa_adk/domain/ src/gepa_adk/ports/ src/gepa_adk/engine/ src/gepa_adk/utils/ 2>/dev/null
! grep -rn 'from litellm' src/gepa_adk/domain/ src/gepa_adk/ports/ src/gepa_adk/engine/ src/gepa_adk/utils/ 2>/dev/null

# No adapter imports in domain/ports
! grep -rn 'from gepa_adk.adapters' src/gepa_adk/domain/ src/gepa_adk/ports/ 2>/dev/null

# No engine imports in domain/ports/adapters
! grep -rn 'from gepa_adk.engine' src/gepa_adk/domain/ src/gepa_adk/ports/ src/gepa_adk/adapters/ 2>/dev/null

echo "All boundary checks passed."
```

### Integration Points

**Internal Data Flow (evolution loop):**

```
api.py:evolve()
  │ wires dependencies, resolves string shortcuts to Protocol instances
  ▼
AsyncGEPAEngine.run()
  │ binds evolution_id UUID to logger
  │ creates _EngineState + optional ParetoState
  ▼
┌─── Evolution Loop ───────────────────────────────────┐
│ 1. adapter.evaluate(batch, candidate)                │
│    → EvaluationBatch (scores, trajectories, outputs) │
│                                                      │
│ 2. adapter.make_reflective_dataset(candidate, batch) │
│    → Mapping (structured feedback for reflection)    │
│                                                      │
│ 3. adapter.propose_new_texts(candidate, dataset)     │
│    → dict[str, str] (mutated component texts)        │
│                                                      │
│ 4. Engine accepts/rejects based on score comparison  │
│    → Updates _EngineState, ParetoState               │
│                                                      │
│ 5. StopperProtocol callbacks check StopperState      │
│    → Continue or stop                                │
└──────────────────────────────────────────────────────┘
  │ freezes state into result
  ▼
EvolutionResult (frozen, immutable)
```

**External Integration Points:**

| Integration | Direction | Boundary | Protocol |
|------------|-----------|----------|----------|
| Google ADK (agent execution) | Outbound | `adapters/execution/` | `AgentExecutorProtocol` |
| Google ADK (agent types) | Inbound (types) | `adapters/evolution/` | `AsyncGEPAAdapter` |
| LiteLLM (reflection LLM) | Outbound | `adapters/scoring/` (via reflection agent) | ADK `LlmAgent` wrapping LiteLLM model |
| User's ADK agents | Inbound (API params) | `api.py` | Public function signatures |
| User's trainset data | Inbound (API params) | `api.py` | `list[dict[str, Any]]` |
| structlog (observability) | Outbound | All layers (domain, engine, adapters) | `structlog.get_logger()` |

### Cross-Cutting Concern Mapping

| Concern | Where It Lives | How It's Enforced |
|---------|---------------|-------------------|
| Async propagation | All I/O paths | ADR-001; `evolve_sync()` only in `api.py` |
| Protocol contracts | `ports/` definitions | Contract tests; `scripts/check_protocol_coverage.py` |
| Structured logging | `engine/`, `adapters/` | Pattern 4 event convention; structlog bound `evolution_id` |
| Error diagnostics | `domain/exceptions.py` | ADR-009; `cause=e` + `from e`; keyword-only context |
| Component addressing | `domain/types.py` | ADR-012; `ComponentSpec` dataclass |
| Schema versioning | `domain/models.py` | Decision 4 (→ ADR-015); `to_dict()`/`from_dict()` |
| Import boundaries | All layers | `scripts/check_boundaries.sh`; CI `boundaries.yml` |
| Docstring quality | All source files | `interrogate` 95% + `docvet check`; ADR-010 |
| Type checking | All source files | `py.typed` PEP 561 marker; `ty check` in CI |

### "Where Does This Go?" Routing Table

| I need to... | Put it in... |
|-------------|-------------|
| Define a new data type | `domain/types.py` or `domain/models.py` |
| Define a new interface | `ports/{capability}_{role}.py` |
| Implement an external integration | `adapters/{concern}/` |
| Add orchestration logic | `engine/async_engine.py` |
| Add a public function | `api.py` + `__init__.py` |
| Add a utility | `utils/` |
| Add a stop condition | `adapters/stoppers/` |
| Add an evolvable surface | `adapters/components/` |
| Add a CI script | `scripts/` |
| Write a concept guide | `docs/concepts/` |
| Write a how-to guide | `docs/guides/` |
| Record an architectural decision | `docs/adr/` |
| Add a runnable example | `examples/` |

### Implementation Sequence for Structural Changes

1. Selector Protocol split (`ports/selector.py` → 3 files) — small, self-contained
2. Adapter sub-package reorganization (→ ADR-014) — large but mechanical, own PR
3. `py.typed` marker + `scripts/` directory + CI boundary check — infrastructure
4. All subsequent feature work targets the new structure

### Directory Temperature Map

| Hot (frequent changes) | Cold (stable) |
|----------------------|--------------|
| `adapters/` (new features) | `domain/` (stable models) |
| `engine/async_engine.py` (loop changes) | `ports/` (stable contracts) |
| `api.py` (new entry points) | `utils/` (utility additions) |
| `tests/unit/` (every feature) | `docs/adr/` (occasional) |

### Reserved ADR Numbers

| ADR | Decision | Status |
|-----|----------|--------|
| ADR-013 | Return Type Unification via EvolutionResultProtocol (Decision 1) | Reserved |
| ADR-014 | Adapter Sub-Package Reorganization (Decision 5) | Reserved |
| ADR-015 | Result Schema Versioning (Decision 4) | Reserved |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**

| Decision Pair | Compatible? | Notes |
|--------------|-------------|-------|
| D1 (Result Protocol) + D4 (Schema Versioning) | ✅ | Protocol defines shared fields; `to_dict()`/`from_dict()` on concrete types |
| D3 (Critic Factory) + D5 (Adapter Reorganization) | ✅ | `create_critic()` placed directly in `adapters/scoring/critic_scorer.py` |
| D5 (Adapter Reorganization) + existing import paths | ✅ | Re-export template preserves backward compatibility; deprecation test enforces |
| D2 (Port Evolution) + CI structural check | ✅ | New Protocols auto-discovered by `PROTOCOL_REGISTRY`; `check_protocol_coverage.py` enforces |
| Hexagonal boundaries + ADK version matrix | ✅ | ADK isolated in `adapters/`; CI tests against `adk==1.22.0` and `adk-latest` |
| Pattern 3 (Engine never sees strings) + Pattern 6 (API resolves shortcuts) | ✅ | Consistent separation — API layer is the wiring point, engine is Protocol-only |

No contradictions found. All 6 decisions and 9 patterns are mutually reinforcing.

**Pattern Consistency:**

- Naming conventions consistent (snake_case files, PascalCase classes, UPPER_SNAKE constants) ✅
- Dataclass conventions consistent (`slots=True, kw_only=True`, `frozen=True` for immutable) ✅
- Protocol definition pattern consistent (one per file, `@runtime_checkable`, Ellipsis bodies) ✅
- Error handling pattern consistent (`cause=e` + `from e`, keyword-only context) ✅
- Async pattern consistent (all I/O async, single `evolve_sync()` wrapper) ✅

**Structure Alignment:**

- Directory structure supports all 6 FR capability areas ✅
- Hot/cold annotations match expected change patterns ✅
- Test structure mirrors source structure ✅
- CI pipeline covers all enforcement mechanisms ✅

### Requirements Coverage Validation ✅

**Functional Requirements (41 FRs across 6 areas):**

| Capability | FR Count | Architectural Support | Coverage |
|-----------|----------|----------------------|----------|
| Single-agent evolution | ~12 | `AsyncGEPAEngine` + `ADKAdapter` + `evolve()` + Patterns 1/3 | ✅ Full |
| Multi-agent pipeline | ~7 | `MultiAgentAdapter` + `evolve_group()` + ADR-012 qualified names | ✅ Full |
| Workflow structure | ~5 | `evolve_workflow()` → `evolve_group()` delegation + `adapters/workflow/` | ✅ Full |
| Multi-surface components | ~9 | `ComponentHandler` Protocol + Registry + 3 shipped handlers + Pattern 8 | ✅ Full |
| Enterprise observability | ~5 | Pattern 4 (structlog events) + `evolution_id` + ADR-008 | ✅ Full |
| Extension protocols | ~3 | Decision 2 (new standalone Protocols) + Pattern 2 + CI enforcement | ✅ Full |

**Non-Functional Requirements (16 NFRs across 5 categories):**

| Category | Key NFR | Architectural Support | Coverage |
|----------|---------|----------------------|----------|
| Performance | Engine overhead <1% | In-memory ParetoState, `asyncio.gather()` + `Semaphore` | ✅ |
| Performance | <100MB heap | Frontier tracks indices, not full candidate texts | ✅ |
| Integration | Zero ADK outside adapter layer | `scripts/check_boundaries.sh` + CI | ✅ |
| Reliability | 99%+ completion | `StopReason` enum + partial result on interrupt (see Gap 1 resolution) | ✅ |
| Maintainability | 85%+ coverage | CI `--cov-fail-under=85` | ✅ |
| Maintainability | Contract tests for every Protocol | CI structural check via `check_protocol_coverage.py` | ✅ |
| Compatibility | ADK >=1.22.0 | ADK version matrix in CI | ✅ |
| Compatibility | Python >=3.12,<3.13 | `pyproject.toml` enforced | ✅ |

### Implementation Readiness Validation ✅

| Check | Status |
|-------|--------|
| All critical decisions documented with rationale | ✅ |
| All Protocols listed with methods | ✅ |
| 9 implementation patterns with code templates | ✅ |
| Complete project structure with annotations | ✅ |
| CI enforcement mechanisms are concrete | ✅ |
| Public API surface curated with documentation rule | ✅ |

### Gap Analysis Results

**Critical Gaps: None** (Gap 1 promoted and resolved below)

**Resolved Gaps:**

**Gap 1 (resolved): Graceful termination with StopReason.**

Added `StopReason` enum to `domain/types.py`:

```python
class StopReason(str, Enum):
    """Why an evolution run terminated."""
    COMPLETED = "completed"
    MAX_ITERATIONS = "max_iterations"
    STOPPER_TRIGGERED = "stopper_triggered"
    KEYBOARD_INTERRUPT = "keyboard_interrupt"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
```

Added `stop_reason: StopReason` field to `EvolutionResult` and `MultiAgentEvolutionResult`. Engine wraps the evolution loop in `try/except (KeyboardInterrupt, asyncio.CancelledError)` and constructs a partial result with full `iteration_history` up to the interruption point. This satisfies the 99%+ completion NFR — interrupted runs return usable results instead of raising.

Impact on existing decisions:
- Decision 1 (Protocol): `EvolutionResultProtocol` includes `stop_reason: StopReason`
- Decision 4 (Serialization): `to_dict()` serializes `stop_reason` as string value; `from_dict()` deserializes
- Pattern 9 (Fixture migration): Existing test fixtures remain valid (`stop_reason` defaults to `StopReason.COMPLETED`)

**Growth-Phase Gaps (deferred):**

**Gap 2: Result comparison utility.** `to_dict()` enables comparison in user code. First-party `compare_results()` utility deferred to Growth phase. Serialization format designed comparison-friendly from v1: `iteration_history` serialized as list of dicts with consistent keys, scores as floats (not formatted strings).

**Gap 3: Examples directory population.** Structure defined, scripts not yet created. Implementation story needed.

**Gap 4: `docs/contributing/architecture.md` pointer file.** Structure defined, content not yet created. Implementation story needed.

### Compatibility Watch Items

**PROTOCOL_REGISTRY auto-discovery:** The `_is_runtime_checkable` attribute used to detect `@runtime_checkable` Protocols is a CPython implementation detail, not part of the `typing` public API. Safe for Python 3.12 (the only supported version). Must be verified if the Python version constraint is loosened in the future.

**Boundary check script:** MVP ships grep-based `scripts/check_boundaries.sh` (catches ~95% of violations). Growth-phase upgrade to AST-based `scripts/check_boundaries.py` (Python `ast.parse()`) to correctly handle `TYPE_CHECKING`-guarded imports. The grep approach may produce false positives on legitimate type-only imports.

### Contract Test Time Budget

Pre-commit runs `pytest tests/contracts/ -x --no-header`. Budget: **<5 seconds total**. If contract tests grow beyond this budget, split into:
- **Fast subset** (pre-commit): `isinstance` checks + method signature verification
- **Full subset** (CI only): happy path + error contract tests

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (95 rules in project-context.md)
- [x] Scale and complexity assessed (medium-high, ~25 modules, 5 layers)
- [x] Technical constraints identified (Python 3.12, ADK, hexagonal boundaries)
- [x] Cross-cutting concerns mapped (10 concerns + 3 Growth considerations)

**✅ Technical Foundation**
- [x] Runtime dependencies documented with versions
- [x] Development toolchain specified with double-gate docstring pipeline
- [x] Project structure defined (existing + target-state with temperature map)
- [x] Testing infrastructure detailed (3-layer + factories + fixtures split)
- [x] CI pipeline specified (boundaries, coverage, type checking, protocol coverage)

**✅ Architectural Decisions**
- [x] 6 established decisions documented (ADRs + implementation)
- [x] 6 new decisions made with rationale and trade-off analysis
- [x] 3 ADR numbers reserved (ADR-013, ADR-014, ADR-015)
- [x] Implementation sequence and cross-dependencies mapped
- [x] StopReason enum added for graceful termination semantics

**✅ Implementation Patterns**
- [x] 9 extension recipes defined with code templates
- [x] Anti-patterns documented for each recipe
- [x] Enforcement guidelines with CI automation
- [x] Log level guide and event naming convention

**✅ Project Structure**
- [x] Complete directory tree with hot/cold annotations
- [x] Architectural boundaries with CI enforcement script
- [x] Requirements-to-structure mapping (6 capability areas)
- [x] Integration points and data flow diagrams
- [x] Routing table, implementation sequence, re-export template

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Hard Prerequisite:** Structural changes (selector split, adapter reorganization, CI infrastructure) must complete *before* parallel feature work begins. These are serial; feature work is parallel after.

**Key Strengths:**
- Brownfield advantage — core engine, 3 surfaces, progressive API, 10 ADRs already shipped
- Comprehensive enforcement — CI boundary checks, protocol coverage, 85% floor, contract tests
- Extension-friendly — 9 recipes with templates for Growth-phase consistency
- Graceful termination — StopReason enum gives uniform termination semantics
- Clear boundaries — hexagonal layers with mechanical enforcement

**Areas for Future Enhancement:**
- AST-based boundary check (replaces grep-based, handles TYPE_CHECKING imports)
- Result comparison utility (Growth-phase convenience)
- Examples directory population
- Contributing architecture pointer

### Implementation Handoff

**AI Agent Guidelines:**
1. Read `project-context.md` (95 rules) before any implementation
2. Read this architecture document for decisions and patterns
3. Follow Patterns 1-9 for all extension work
4. Respect hexagonal boundaries — CI will catch violations
5. Create contract tests (minimum 4) for every new Protocol implementation
6. Run `ruff format && ruff check --fix && docvet check && ty check src tests` before marking tasks complete

**Implementation Priority Sequence:**

| Priority | Item | Type | User-Visible? |
|----------|------|------|--------------|
| 1 | Selector Protocol split (`ports/selector.py` → 3 files) | Structural | No |
| 2 | Adapter sub-package reorganization (→ ADR-014) | Structural | No |
| 3 | `py.typed` + `scripts/` + CI boundary check | Infrastructure | No |
| 4 | `create_critic()` factory in `adapters/scoring/` | Feature | **Yes** — `critic="structured_output"` |
| 5 | `StopReason` enum + `stop_reason` field on result types | Feature | **Yes** — graceful termination semantics |
| 6 | `EvolutionResultProtocol` in `ports/` (→ ADR-013) | Foundational | No |
| 7 | `schema_version` + `to_dict()`/`from_dict()` (→ ADR-015) | Foundational | **Yes** — result persistence |

**Architecture document reference:** Add to `project-context.md`: *"See `_bmad-output/planning-artifacts/architecture.md` for architectural decisions, implementation patterns, and project structure."*
