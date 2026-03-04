---
project_name: 'gepa-adk'
user_name: 'Alberto-Codes'
date: '2026-03-01'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality', 'workflow_rules', 'critical_rules']
status: 'complete'
rule_count: 95
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Core Runtime
- **Python**: 3.12 (strict `>=3.12,<3.13`) — use modern syntax: `X | Y` not `Optional[X]`, `list[X]` not `List[X]`
- **google-adk**: >= 1.20.0 — types come from `google.adk.agents` and `google.genai.types` (Content, Part, GenerateContentConfig)
- **litellm**: >= 1.80.13 — LLM proxy for multi-provider support
- **structlog**: >= 25.5.0 — the ONLY external library allowed in `domain/` layer
- **nest-asyncio**: >= 1.6.0 — enables `asyncio.run()` in sync wrappers

### Toolchain
- **Package manager**: `uv` — never `pip install` or `poetry`; use `uv run` to invoke tools
- **Linter/Formatter**: `ruff` — line-length 88 (formatter), 100 (linter); Google docstring convention; double quotes
- **Type checker**: `ty` (Astral) — NOT mypy; test files have relaxed rules
- **Docstring coverage**: `interrogate` at 95% — excludes tests/scripts, ignores __init__/magic/private

### Testing Toolchain
- **pytest** with `asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio` to async tests
- **Coverage**: 85% fail-under enforced in CI (`--cov-fail-under=85`)
- **Warnings as errors**: `filterwarnings = ["error"]` — new imports causing warnings will break CI
- **Default exclusion**: `addopts = "-m 'not api'"` — tests marked `api` don't run by default

## Critical Implementation Rules

### Python Language Rules

#### Modern Syntax (ruff-enforced)
- `str | None` not `Optional[str]`; `list[X]` not `List[X]`; `dict[K, V]` not `Dict[K, V]`
- `match`/`case` available and used in codebase
- `from __future__ import annotations` — match the convention of the file being edited

#### Logging
- Always: `logger = structlog.get_logger(__name__)` at module level
- Never: `logging.getLogger()` or logger creation inside methods
- Event names: dot-notation for structured (`config.reflection_prompt.empty`), plain English for operational (`"Evolution started"`)

#### Dataclasses
- Standard: `@dataclass(slots=True, kw_only=True)`
- Immutable records: add `frozen=True` (IterationRecord, EvolutionResult, EvaluationBatch)
- Mutable defaults: always `field(default_factory=...)`
- Frozen + __post_init__ mutation: use `object.__setattr__(self, field, value)`

#### Import Layer Boundaries
```
domain/   → stdlib only (exception: structlog)
ports/    → domain + stdlib
adapters/ → ports + domain + external libs
engine/   → ports + domain + structlog (may import adapter defaults)
utils/    → stdlib + structlog
```
- Lazy imports inside function bodies for optional/circular deps
- `TYPE_CHECKING` guard for type-only imports

#### Async
- All core APIs are `async def` — sync wrapper via `asyncio.run()` exists ONLY in `api.py`
- Do NOT create new sync wrappers elsewhere
- Concurrency: `asyncio.gather()` + `asyncio.Semaphore` for throttling

#### Module Exports
- Every source and fixture module defines `__all__` at file bottom — no exceptions

#### Testing Python Patterns
- `pytestmark = pytest.mark.unit` (or `contract`/`integration`) at module top — not per-function
- Tests grouped in classes: `TestConstructor`, `TestUserStory1` — not flat functions
- Shared fixtures in `conftest.py` at directory level or `tests/fixtures/` modules

### Framework Rules (Google ADK + Hexagonal Architecture)

#### Protocol-Based Interfaces (Ports)
- All ports use `typing.Protocol` with `@runtime_checkable` — never `abc.ABC`
- Protocol bodies use `...` (Ellipsis) — not `pass` or `raise NotImplementedError`
- Implementations do NOT inherit from Protocols (structural subtyping):
  ```python
  # ports/scorer.py
  @runtime_checkable
  class Scorer(Protocol):
      async def async_score(self, ...) -> tuple[float, dict[str, Any]]: ...

  # adapters/critic_scorer.py — NO inheritance
  class CriticScorer:
      async def async_score(self, ...) -> tuple[float, dict[str, Any]]:
          ...  # actual implementation
  ```
- Exception: test mocks MAY inherit from Protocols for convenience
- Port modules contain only the Protocol class + `__all__` — helper types belong in `domain/types.py`

#### Exception Hierarchy
- All exceptions inherit from `EvolutionError`
- `__init__` uses `*` to force keyword-only args after message:
  ```python
  def __init__(self, message: str, *, cause: Exception | None = None, **context: object) -> None:
  ```
- BOTH `cause=e` AND `from e` required when raising:
  ```python
  raise EvaluationError("failed", cause=e, agent_name=name) from e
  ```
- Every exception overrides `__str__` to include context fields

#### ADK Agent Types
- `LlmAgent` — primary building block (wraps an LLM call)
- `SequentialAgent`, `LoopAgent`, `ParallelAgent` — workflow orchestrators
- `BaseAgent` — for custom non-LLM agents
- Session: `InMemorySessionService` default, or injected `BaseSessionService`
- Types: `Content`, `Part` from `google.genai.types`; `GenerateContentConfig` for model config

#### Multi-Agent Component Addressing
- Dot-separated qualified names: `"generator.instruction"` not `"generator_instruction"`
- Use `QualifiedComponentName` or `ComponentSpec(agent="x", component="y").qualified`

#### Dependency Injection & Wiring
- Engine (`AsyncGEPAEngine`) receives adapters via constructor — not global imports
- New adapters are wired through factory functions or passed to engine constructor
- New stoppers → new file in `adapters/stoppers/` implementing `StopperProtocol`
- New scorers → new file in `adapters/` implementing `Scorer` Protocol; returns `tuple[float, dict[str, Any]]` (score 0.0–1.0 + metadata dict)
- Contract test required in `tests/contracts/` for every new Protocol implementation

### Testing Rules

#### Three-Layer Test Strategy
- `tests/unit/` — fast, isolated, no external services
- `tests/contracts/` — Protocol compliance (every Protocol implementation gets one)
- `tests/integration/` — real ADK/LLM interactions

#### Test File Structure
- One `pytestmark` at module top: `pytestmark = pytest.mark.unit`
- Tests organized in classes mapping to public API: `TestConstructor`, `TestEvolveMethod`
- Test functions: `test_` prefix + descriptive snake_case
- No flat test functions — always inside a class

#### Markers
- `unit`, `contract`, `integration` — layer markers (module-level `pytestmark`)
- `slow` — tests > 10s
- `api` — real external API calls (**excluded by default** — always mark API-calling tests)
- `requires_ollama`, `requires_gemini` — auto-skipped if service unavailable

#### Async Testing
- `asyncio_mode = "auto"` — do NOT add `@pytest.mark.asyncio`
- Each test gets its own event loop (`asyncio_default_fixture_loop_scope = "function"`)

#### Mock Infrastructure (`tests/fixtures/adapters.py`)
- **Use `create_mock_adapter` factory for all new tests** — not direct `MockAdapter()` instantiation
- `AdapterConfig` dataclass configures behavior; `OutputMode` enum controls output generation
- Call tracking available via `ConfigurableMockAdapter` for assertion on call counts/args

#### Conftest Hierarchy (fixtures at narrowest scope)
- `tests/conftest.py` — root: `MockScorer`, `MockExecutor`, `trainset_samples`, `valset_samples`, `deterministic_scores`
- `tests/unit/engine/conftest.py` — engine: `mock_adapter`, `sample_config`, `sample_candidate`, `sample_batch`
- `tests/unit/adapters/conftest.py` — adapter-specific fixtures
- Check existing fixtures before creating new ones — reuse over reinvention

#### Contract Test Pattern
```python
class TestScorerProtocol:
    def test_scorer_protocol_is_runtime_checkable(self):
        scorer = FixedScorer()
        assert isinstance(scorer, Scorer)

    def test_protocol_methods_are_async(self):
        import inspect
        assert inspect.iscoroutinefunction(Scorer.async_score)
```
- Minimum: `isinstance` check + method signature verification per Protocol

#### Warnings & CI
- `filterwarnings = ["error"]` — new warnings break CI
- Suppress third-party warnings in `pyproject.toml` centrally — not per-test `@pytest.mark.filterwarnings`
- New modules need tests covering happy path + primary error paths (85% coverage floor)

### Code Quality & Style Rules

#### Docstrings (Google-style — three-tool pipeline)
- **interrogate** (95%) → presence: does a docstring exist?
- **ruff D** (Google convention) → style: is it formatted correctly?
- **docvet** → completeness + accuracy: does it match the code?
- NOT required on: `__init__`, magic methods, private methods (interrogate excludes these)
- Section order: Summary → `Args:` → `Returns:` → `Raises:` → `Yields:` → optional `Examples:`, `Note:`, `Warning:`
- `Examples:` use fenced code blocks — not `>>>` doctest format
- Module docstrings: Summary + `Attributes:` listing `__all__` contents mandatory
- If a function raises, it MUST have a `Raises:` section (docvet enforces this)
- If a function yields, it MUST have a `Yields:` section
- Run `docvet check` after modifying functions/classes — fix all findings before committing

#### Type Checking (ty)
- Run `ty check src tests` — enforced in CI on PR ready_for_review
- Test files have relaxed rules: `unresolved-attribute`, `invalid-argument-type`, `not-subscriptable`, `unsupported-operator` ignored
- ty uses `# ty: ignore[rule]` syntax for inline suppressions — NOT `# type: ignore` (mypy syntax)
- ty DOES recognize `# type: ignore` but the project standard is `# ty: ignore[rule]` with a justification comment
- Prefer fixing the type issue over adding ignores; use `# ty: ignore[rule]` only when genuinely unfixable (e.g., ADK typing gaps, runtime dispatch patterns)
- For test files, use `pyproject.toml` `[tool.ty.overrides]` instead of inline suppressions

#### Naming Conventions
- Package import: `from gepa_adk.domain.models import ...` (underscore, not hyphen)
- Files: `snake_case.py`
- Classes: `PascalCase` — `ADKAdapter`, `CriticScorer`, `AsyncGEPAEngine`
- Functions/methods: `snake_case` — `async_score`, `propose_new_texts`
- Constants: `UPPER_SNAKE_CASE` — `DEFAULT_COMPONENT_NAME`, `SESSION_STATE_KEYS`
- Private: single underscore prefix — `_session_service`, `_logger`
- Type aliases: `PascalCase` — `Score`, `ComponentName`, `FrontierKey`
- Strings: double quotes always (`"text"` not `'text'`)

#### File Organization — Where New Code Goes
- Pure data models, no external deps → `domain/`
- Interface definition → `ports/` (one Protocol per file)
- Implementation using external libraries → `adapters/`
- Orchestration logic → `engine/`
- Shared helpers → `utils/`
- New stopper → `adapters/stoppers/` (only adapter subdirectory)
- `__all__` at file BOTTOM, after all definitions

#### Ruff Handles Formatting
- `ruff format` + `ruff check --fix` before committing — don't fight the formatter
- Line length: 88 (formatter), 100 (linter) — let ruff decide line breaks
- Import sorting: automatic via isort rules (`agent_workflow_suite` as first-party — legacy name)
- `tests/*.py`: `assert` allowed (S101 suppressed)

### Development Workflow Rules

#### Branch Naming
- `feat/description` — features
- `fix/description` — bug fixes
- `docs/description` — documentation
- `refactor/description` — refactoring
- `test/description` — test additions
- `chore/description` — maintenance

#### Commit Messages (Conventional Commits)
- Format: `type(scope): description`
- Types: `feat | fix | docs | refactor | test | chore | perf`
- Scope: noun describing codebase section — NOT spec/issue numbers
- Breaking changes: add `!` after scope — `feat(engine)!: remove legacy API`
- Do NOT use `#N` for BMAD story IDs — GitHub auto-links them incorrectly; use plain text `Story 23.4`

#### Pull Requests
- Always `--draft` — ready PRs trigger automated review
- Target `develop` branch (not `main`)
- Title follows conventional commits format
- Use `.github/PULL_REQUEST_TEMPLATE.md` structure exactly

#### CI Pipeline
- `tests.yml` — pytest with `--cov-fail-under=85` on push to develop/main and all PRs
- `type-check.yml` — `ty check src tests` on PR ready_for_review
- `docs.yml` — MkDocs build on PRs touching docs/src/mkdocs.yml
- `codeql.yml` — security analysis on push and weekly
- `release-please.yml` — automated release PR management on push to develop

#### Pre-Commit Checklist
1. `ruff format` + `ruff check --fix`
2. `docvet check`
3. `pytest` (at minimum unit tests)
4. `ty check src tests`

### Critical Don't-Miss Rules

#### Most-Violated Patterns (reinforced)
- Exception raising requires BOTH: `raise SomeError("msg", cause=e) from e` — agents forget `from e` or use positional args
- Frozen dataclass `__post_init__`: use `object.__setattr__(self, field, value)` — `self.field = value` raises `FrozenInstanceError`
- `__all__` must be updated when adding new public names to existing modules — agents add classes but forget to export them

#### Architectural Gotchas
- Engine importing from adapters (`RoundRobinComponentSelector`, `FullEvaluationPolicy`) — pragmatic defaults, NOT permission to freely cross the boundary
- `TYPE_CHECKING` imports are for type annotations ONLY — if you use the type at runtime (`isinstance`, default values), it must be a real import
- Circular imports → fix with lazy import inside function body, not by restructuring
- ADRs in `docs/adr/` are the source of truth — check before proposing architectural changes (especially ADR-000 hexagonal, ADR-001 async-first)

#### Naming Traps
- Import path: `gepa_adk` (underscore) — project name `gepa-adk` (hyphen) is NOT the import
- ruff isort config: `agent_workflow_suite` is a legacy first-party name — don't be confused by it

#### CI Traps
- Any test making network calls MUST have `@pytest.mark.api` — otherwise it runs in CI without credentials and fails/hangs
- Integration tests needing Ollama/Gemini must use `requires_ollama`/`requires_gemini` markers — services aren't available in CI
- Adding a new source file without a corresponding test file can drop coverage below 85% and fail CI
- When adding new files to a layer, update the layer's `__init__.py` if it re-exports

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Check `docs/adr/` for architectural decision context

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack or patterns change
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-03-01

