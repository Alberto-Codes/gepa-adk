# gepa-adk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Active Technologies
- N/A (protocol definition only) (005-scorer-protocol)
- Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (010-adk-reflection-agent)
- N/A (in-memory session state via ADK's InMemorySessionService) (010-adk-reflection-agent)

- Python 3.12 + None (stdlib only for ports layer per ADR-000) (004-async-gepa-adapter)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.12: Follow standard conventions

## Recent Changes
- 010-adk-reflection-agent: Added Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0
- 005-scorer-protocol: Added Python 3.12 + None (stdlib only for ports layer per ADR-000)

- 004-async-gepa-adapter: Added Python 3.12 + None (stdlib only for ports layer per ADR-000)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
