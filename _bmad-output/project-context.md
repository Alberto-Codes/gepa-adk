---
project_name: 'gepa-adk'
user_name: 'Alberto-Codes'
date: '2026-03-05'
status: 'complete'
optimized_for_llm: true
---

# Project Context for AI Agents

## Technology Stack

- **Python**: 3.12 (strict `>=3.12,<3.13`)
- **google-adk**: >= 1.20.0 — types from `google.adk.agents` and `google.genai.types`
- **litellm**: >= 1.80.13 — LLM proxy for multi-provider support
- **structlog**: >= 25.5.0 — the ONLY external library allowed in `domain/` layer
- **Package manager**: `uv` — never `pip install` or `poetry`

## Hexagonal Architecture (ADR-000)

```
domain/   → stdlib only (exception: structlog)
ports/    → domain + stdlib
adapters/ → ports + domain + external libs
engine/   → ports + domain + structlog (may import adapter defaults)
utils/    → stdlib + structlog
```

- All ports use `typing.Protocol` with `@runtime_checkable` — never `abc.ABC`
- Implementations do NOT inherit from Protocols (structural subtyping)
- Engine receives adapters via constructor — not global imports
- ADRs in `docs/adr/` are the source of truth for architectural decisions

## ADK Patterns

- `LlmAgent` — primary building block; `SequentialAgent`, `LoopAgent`, `ParallelAgent` — orchestrators
- Session: `InMemorySessionService` default, or injected `BaseSessionService`
- Types: `Content`, `Part` from `google.genai.types`; `GenerateContentConfig` for model config
- Multi-agent component addressing: dot-separated qualified names (`"generator.instruction"`)
- All core APIs are `async def` — sync wrapper exists ONLY in `api.py`

## Critical Don't-Miss Rules

- Exception raising: BOTH `cause=e` AND `from e` required — `raise SomeError("msg", cause=e) from e`
- Exception `__init__` uses `*` for keyword-only args after message
- Frozen dataclass `__post_init__`: use `object.__setattr__(self, field, value)`
- `__all__` at file BOTTOM in every source module — no exceptions
- `TYPE_CHECKING` imports are for type annotations ONLY — runtime usage needs real imports
- Import path: `gepa_adk` (underscore) — project name `gepa-adk` (hyphen) is NOT the import
- `#N` syntax reserved for GitHub issues/PRs — never use for BMAD story IDs

## Quality Gates

All quality gates enforced by pre-commit hooks and CI. Just commit and fix what fails.

Last Updated: 2026-03-05
