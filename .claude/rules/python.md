---
globs: ["*.py"]
---

# Python Conventions (gepa-adk)

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

## Type Checking
- ty uses `# ty: ignore[rule]` — NOT `# type: ignore`
- For test files, use `pyproject.toml` `[tool.ty.overrides]` instead of inline suppressions
