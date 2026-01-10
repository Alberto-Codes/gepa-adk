# gepa-adk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Active Technologies
- Python 3.12+ + stdlib only (dataclasses, typing) - per ADR-000 domain layer purity (002-domain-models)
- N/A (domain models are in-memory) (002-domain-models)
- Python 3.12 + None (stdlib only for engine layer per ADR-000) (006-async-gepa-engine)
- N/A (in-memory state during run; no persistence in v1) (006-async-gepa-engine)

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
- 006-async-gepa-engine: Added Python 3.12 + None (stdlib only for engine layer per ADR-000)
- 002-domain-models: Added Python 3.12+ + stdlib only (dataclasses, typing) - per ADR-000 domain layer purity
- 002-domain-models: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
