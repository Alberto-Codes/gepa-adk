# gepa-adk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Active Technologies
- N/A (protocol definition only) (005-scorer-protocol)
- Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (010-adk-reflection-agent)
- N/A (in-memory session state via ADK's InMemorySessionService) (010-adk-reflection-agent)
- Python 3.12 + `re` (stdlib only - no new dependencies) (015-state-guard-tokens)
- N/A (string manipulation utility) (015-state-guard-tokens)
- Python 3.12 + google-adk 1.22.0 (SequentialAgent, LoopAgent, ParallelAgent, LlmAgent, BaseAgent) (017-workflow-evolution)
- N/A (in-memory evolution) (017-workflow-evolution)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0, dataclasses (stdlib) (019-critic-metadata-passthrough)
- N/A (in-memory data flow) (019-critic-metadata-passthrough)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0 (existing); no new dependencies (022-pareto-frontier)
- N/A (in-memory evolution state) (022-pareto-frontier)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0 (existing - no new deps) (024-component-selector)
- N/A (in-memory evolution state via ParetoState) (028-merge-proposer)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0, typing (stdlib) (029-agent-provider-protocol)
- N/A (protocol definition only - implementations choose storage) (029-agent-provider-protocol)
- Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (existing - no new deps) (031-wire-reflection-model)
- N/A (in-memory configuration passthrough) (031-wire-reflection-model)
- N/A (in-memory event processing) (033-event-output-extraction)
- Python 3.12 + google-adk >= 1.22.0, litellm >= 1.80.13, structlog >= 25.5.0 (034-adk-ollama-reflection)
- Python 3.12 (MkDocs plugin ecosystem) + mkdocs-ezglossary-plugin>=2.1.0, Material for MkDocs (existing) (036-glossary-integration)
- N/A (static site generation) (036-glossary-integration)
- Python 3.12 + structlog>=25.5.0 (existing), stdlib `sys` and `codecs` (001-cross-platform-encoding)
- N/A (logging infrastructure only) (001-cross-platform-encoding)
- Python 3.12 + google-adk >= 1.22.0 (Runner, Session, Event), structlog >= 25.5.0 (124-unified-agent-executor)
- Python 3.12 + google-adk >= 1.22.0, dataclasses (stdlib) (126-evolved-components)
- N/A (in-memory domain models) (126-evolved-components)
- Python 3.12 + google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps) (141-critic-feedback-schema)
- N/A (in-memory normalization) (141-critic-feedback-schema)
- Python 3.12 + google-adk >= 1.22.0, pydantic >= 2.0, structlog >= 25.5.0 (142-component-aware-reflection)
- N/A (in-memory registry) (162-component-handlers)
- N/A (in-memory component handling) (163-component-handler-migration)
- Python 3.12 + google-adk >= 1.22.0 (GenerateContentConfig from google.genai.types), PyYAML (stdlib yaml), structlog >= 25.5.0 (164-config-evolution)
- N/A (in-memory candidate/component state) (166-multi-agent-routing)
- Python 3.12 + structlog>=25.5.0 (existing - no new deps), pathlib (stdlib) (197-optional-stoppers)
- N/A (in-memory stopper state) (197-optional-stoppers)

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
- 197-optional-stoppers: Added Python 3.12 + structlog>=25.5.0 (existing - no new deps), pathlib (stdlib)
- 196-stopper-engine-integration: Added Python 3.12 + google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps)
- 166-multi-agent-routing: Added Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
