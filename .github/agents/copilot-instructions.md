# gepa-adk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Active Technologies
- Python 3.12+ + stdlib only (dataclasses, typing) - per ADR-000 domain layer purity (002-domain-models)
- N/A (domain models are in-memory) (002-domain-models)
- Python 3.12 + None (stdlib only for engine layer per ADR-000) (006-async-gepa-engine)
- N/A (in-memory state during run; no persistence in v1) (006-async-gepa-engine)
- Python 3.12 + LiteLLM (for async LLM calls via `acompletion`) (007-async-mutation-proposer)
- N/A (stateless proposer) (007-async-mutation-proposer)
- Python 3.12+ + litellm 1.80.13 (for async LLM calls) (007-async-mutation-proposer)
- In-memory sessions (InMemorySessionService by default) (008-adk-adapter)
- Python 3.12 + google-adk (1.22.0), pydantic (2.12.5), structlog (25.5.0) (011-trajectory-capture)
- N/A (in-memory trajectory extraction) (011-trajectory-capture)

- Python 3.12+ + None (stdlib only for domain layer) (002-domain-models)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12+: Follow standard conventions

## Recent Changes
- 011-trajectory-capture: Added Python 3.12 + google-adk (1.22.0), pydantic (2.12.5), structlog (25.5.0)
- 008-adk-adapter: Added Python 3.12
- 007-async-mutation-proposer: Added Python 3.12+ + litellm 1.80.13 (for async LLM calls)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
