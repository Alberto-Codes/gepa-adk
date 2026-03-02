<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0
- Modified principles: V. Observability & Documentation Standards → V. Observability & Code Documentation
- Added sections: VI. Documentation Synchronization (NEW)
  - MkDocs static site integration
  - Static pages table with update triggers
  - Auto-generated vs manual distinction
  - Build verification requirements
- Removed sections: N/A
- Templates requiring updates:
  - plan-template.md: ✅ Constitution Check section present (no changes needed)
  - spec-template.md: ✅ Requirements/testing alignment compatible (no changes needed)
  - tasks-template.md: ✅ Updated with docs/examples tasks per story + mkdocs build verification
- Follow-up TODOs: None
-->

# gepa-adk Constitution

## Core Principles

### I. Hexagonal Architecture (Ports & Adapters)

All code MUST follow the hexagonal architecture pattern with strict layer boundaries:

- **domain/**: Pure Python domain models and exceptions (NO external imports except stdlib)
- **ports/**: Protocol-based interfaces (NO external imports)
- **adapters/**: External library integrations (ADK, LiteLLM imports allowed HERE ONLY)
- **engine/**: Orchestration logic (depends on ports, receives adapters via injection)
- **utils/**: Shared utilities (minimal external dependencies)

**Layer Import Rules**:
| Layer | Can Import From | Cannot Import From |
|-------|-----------------|-------------------|
| domain/ | Standard library only | ports/, adapters/, external libs |
| ports/ | domain/ | adapters/, external libs |
| adapters/ | ports/, domain/, external libs | — |
| engine/ | ports/, domain/ | adapters/ (receives via injection) |

**Rationale**: External libraries (Google ADK, LiteLLM) change frequently. Isolating them behind ports ensures core evolution logic remains stable and testable without real dependencies.

**Reference**: [ADR-000: Hexagonal Architecture](docs/adr/ADR-000-hexagonal-architecture.md)

### II. Async-First Design

All I/O-bound operations MUST be async (`async def`):

- Core APIs are async; sync wrappers provided only at top-level public API
- No internal sync/async bridging—async flows all the way down
- Concurrent batch evaluation via `asyncio.Semaphore` for controlled parallelism
- Protocol methods MUST be coroutines

**Rationale**: ADK is async-native. Async-first enables concurrent evaluation (3-5x performance) and proper resource utilization.

**Reference**: [ADR-001: Async-First Architecture](docs/adr/ADR-001-async-first-architecture.md)

### III. Protocol-Based Interfaces

All port interfaces MUST use `typing.Protocol` (PEP 544) for structural subtyping:

- Use `@runtime_checkable` when isinstance() checks are needed
- No ABC inheritance unless lifecycle management (context managers) is required
- Simple async method signatures enable duck typing with type safety

**Rationale**: Protocols provide flexibility without inheritance complexity, enabling test doubles and alternative implementations without boilerplate.

**Reference**: [ADR-002: Protocol for Interfaces](docs/adr/ADR-002-protocol-for-interfaces.md)

### IV. Three-Layer Testing (NON-NEGOTIABLE)

Every feature MUST include tests across three layers:

| Layer | Location | Purpose | Execution |
|-------|----------|---------|-----------|
| **Contract** | tests/contracts/ | Protocol compliance verification | Every commit |
| **Unit** | tests/unit/ | Business logic with mock adapters | Every save (watch mode) |
| **Integration** | tests/integration/ | Real ADK/LLM calls (@pytest.mark.slow) | CI only |

**Test-Driven Development**: Tests MUST be written before implementation. Red-Green-Refactor cycle is mandatory.

**Rationale**: Contract tests ensure adapters implement ports correctly. Unit tests enable fast feedback. Integration tests verify real-world behavior.

**Reference**: [ADR-005: Three-Layer Testing Strategy](docs/adr/ADR-005-three-layer-testing.md)

### V. Observability & Code Documentation

All code MUST meet observability and documentation requirements:

**Structured Logging**:
- Use `structlog` with context binding for all log output
- Emit structured events to stdout; infrastructure handles routing
- Include evolution context (evolution_id, agent_name, iteration) in all logs

**Docstring Quality**:
- Google-style docstrings exclusively
- 95%+ coverage (enforced by docvet)
- Args, Returns, Raises sections MUST match actual code
- Examples section for public APIs

**Exception Handling**:
- All exceptions inherit from `EvolutionError` base class
- Include `cause` attribute for exception chaining
- Provide context dict for debugging

**References**:
- [ADR-008: Structured Logging](docs/adr/ADR-008-structured-logging.md)
- [ADR-009: Exception Hierarchy](docs/adr/ADR-009-exception-hierarchy.md)
- [ADR-010: Docstring Quality](docs/adr/ADR-010-docstring-quality.md)

### VI. Documentation Synchronization

User-facing features MUST include documentation updates alongside implementation:

**MkDocs Static Site** (`docs/` → built via `mkdocs.yml`):
- Site structure defined in `mkdocs.yml` nav section
- Built with `uv run mkdocs build`; served locally with `uv run mkdocs serve`
- Published to GitHub Pages at https://alberto-codes.github.io/gepa-adk/

**Static Pages Requiring Manual Updates**:
| Page | Location | Update When |
|------|----------|-------------|
| Homepage | `docs/index.md` | Major features, project status changes |
| Getting Started | `docs/getting-started.md` | New config options, setup changes |
| Single-Agent Guide | `docs/guides/single-agent.md` | Single-agent API changes |
| Multi-Agent Guide | `docs/guides/multi-agent.md` | Multi-agent API changes |
| Critic Agents | `docs/guides/critic-agents.md` | Critic/scorer changes |
| Workflows | `docs/guides/workflows.md` | Workflow evolution changes |
| ADRs | `docs/adr/` | New architectural decisions |

**Auto-Generated (No Manual Updates)**:
- `docs/reference/` — API reference generated from docstrings via mkdocstrings
- Navigation in reference section — generated by `scripts/gen_ref_pages.py`

**Working Examples** (`examples/`):
- Features that change user-facing behavior MUST update at least one example
- New major features SHOULD include a dedicated example file
- Examples MUST be runnable and tested in CI (or manually verified)

**Build Verification**:
- `uv run mkdocs build` MUST pass without warnings before PR merge
- Feature branch docs changes should be previewed with `uv run mkdocs serve`

**Speckit Integration**:
- `/speckit.tasks` MUST generate documentation tasks for user-facing features
- Documentation tasks are part of the user story, not a separate "polish" phase
- Feature is not complete until docs and examples reflect the implementation

**Scope Determination**:
| Change Type | docs/ Update | examples/ Update |
|-------------|--------------|------------------|
| New public API | Required | Required |
| New config option | Required (guides) | Recommended |
| Bug fix | Not required | Not required |
| Internal refactor | Not required | Not required |
| Breaking change | Required + migration | Required |

**Rationale**: Documentation that trails implementation becomes outdated and misleading. By requiring docs updates as part of the feature (not after), users always have accurate guidance. The mkdocs + mkdocstrings pipeline auto-generates API reference from code docstrings, so only guides and examples need manual attention.

## ADR Governance

Architecture Decision Records (ADRs) in `docs/adr/` serve as the authoritative source for technical decisions:

- **ADRs are living documents**: They grow as the project evolves and apply contextually depending on the feature being implemented
- **Spec compliance**: Each specification MUST reference relevant ADRs and verify alignment
- **New decisions**: When a specification requires a decision not covered by existing ADRs, create a new ADR before implementation
- **ADR index**: See [docs/adr/README.md](docs/adr/README.md) for the complete list and applicability matrix

**Current ADRs**:
| ADR | Title | Applies To |
|-----|-------|------------|
| ADR-000 | Hexagonal Architecture | All code structure |
| ADR-001 | Async-First Architecture | All I/O operations |
| ADR-002 | Protocol for Interfaces | All port definitions |
| ADR-005 | Three-Layer Testing | All test code |
| ADR-006 | External Library Integration | adapters/ layer |
| ADR-008 | Structured Logging | All logging |
| ADR-009 | Exception Hierarchy | All error handling |
| ADR-010 | Docstring Quality | All docstrings |

## Development Workflow

### Code Quality Gates

All PRs MUST pass:

```bash
uv run ruff check --fix          # Linting (auto-fix)
uv run ruff format               # Formatting (100 char lines)
uv run ty check                  # Type checking
uv run pytest -n auto            # All tests pass
```

### Branch Strategy

- Feature branches: `feat/###-feature-name` (from `develop`)
- Spec-driven: Each feature has corresponding `specs/###-feature-name/` documentation
- Merge flow: feature → develop → main

### Dependency Management

- Production deps in `[project.dependencies]`
- Dev deps in `[dependency-groups.dev]`
- Use `uv add` exclusively (no manual pyproject.toml edits)
- Always commit `uv.lock` for reproducibility

## Governance

This constitution supersedes all other practices. Amendments require:

1. **Documentation**: Proposed change with rationale
2. **ADR**: New or updated ADR if architectural impact
3. **Review**: Team approval via PR
4. **Migration**: Plan for existing code compliance

**Compliance Verification**:
- All PRs MUST verify alignment with applicable principles
- Constitution Check section in plan.md gates Phase 0 research
- Complexity deviations MUST be justified in writing

**Guidance Files**:
- Runtime development guidance: `.github/copilot-instructions.md`
- Python conventions: `.github/instructions/python.instructions.md`
- Testing conventions: `.github/instructions/pytest.instructions.md`

**Version**: 1.1.0 | **Ratified**: 2026-01-10 | **Last Amended**: 2026-01-17
