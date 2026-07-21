---
globs: ["*.py"]
---

# Python Conventions (gepa-adk)

## Semantic Rules (not enforced by ruff/ty)

- **Every file** starts with `from __future__ import annotations` — no exceptions
- **No mutable defaults**: Never use `[]` or `{}` as function default arguments
- **No bare exceptions**: Always catch specific exception types, include context in error messages
- **No `assert` in production code**: `assert` is for tests only. Production code must use proper error handling
- **f-strings for formatting**, `%`-formatting for logger calls only
- **Comments explain WHY**, not WHAT — assume reader knows Python

## Logging
- `logger = structlog.get_logger(__name__)` at module level — never `logging.getLogger()`
- Event names: dot-notation for structured (`config.reflection_prompt.empty`), plain English for operational

## Dataclasses
- Standard: `@dataclass(slots=True, kw_only=True)`
- Immutable records: add `frozen=True`
- Mutable defaults: always `field(default_factory=...)`

## Async
- Do NOT create sync wrappers outside `api.py`
- Concurrency: `asyncio.gather()` + `asyncio.Semaphore` for throttling

## Where New Code Goes
- Pure data models → `domain/`
- Interface definition → `ports/` (one Protocol per file)
- Implementation using external libs → `adapters/`
- Orchestration logic → `engine/`
- Shared helpers → `utils/`
- New stopper → `adapters/stoppers/`

## Dependency Injection
- New scorers → `adapters/` implementing `Scorer` Protocol; returns `tuple[float, dict[str, Any]]`
- New stoppers → `adapters/stoppers/` implementing `StopperProtocol`
- Contract test required in `tests/contracts/` for every new Protocol implementation

## Docstrings (Google-style)
- Section order: Summary → `Args:` → `Returns:` → `Raises:` → `Yields:`
- Module docstrings: Summary + `Attributes:` listing `__all__` contents

## Module Size Guidance

When a source module exceeds ~500 lines or contains 3+ distinct concerns, consider extracting into a sub-package:

- Pattern: `domain/strategy.py` -> `domain/strategy/` with `__init__.py` re-exporting public API
- Internal modules for distinct concerns
- Same principle applies to test files — split by concern into dedicated files
- Apply when natural (during a story that touches the module), not as forced refactoring

## Type Checking
- ty uses `# ty: ignore[rule]` — NOT `# type: ignore`
- For test files, use `pyproject.toml` `[tool.ty.overrides]` instead of inline suppressions
