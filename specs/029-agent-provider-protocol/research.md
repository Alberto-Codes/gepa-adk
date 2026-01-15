# Research: AgentProvider Protocol

**Date**: 2026-01-15
**Feature**: 029-agent-provider-protocol

## Overview

Research findings for implementing the AgentProvider protocol for optional agent loading and persistence in gepa-adk.

## Research Tasks

### 1. Google ADK Agent Configuration Pattern

**Question**: How does Google ADK handle agent configuration and loading from YAML?

**Findings**:

Google ADK provides a `from_config()` function in `google.adk.agents.config_agent_utils` that:

1. **YAML Loading**: Uses `yaml.safe_load()` to parse YAML files
2. **Pydantic Validation**: Uses `AgentConfig.model_validate()` for schema validation
3. **Discriminated Union**: Uses `agent_class` field to determine agent type (LlmAgent, LoopAgent, etc.)
4. **Dynamic Resolution**: Resolves agent classes via `_resolve_agent_class()` using fully-qualified names

**Key Configuration Fields** (from `LlmAgentConfig`):
- `name`: Required agent identifier
- `instruction`: Required dynamic instruction text
- `model`: Optional model name (e.g., "gemini-2.0-flash")
- `tools`: Optional list of tool configurations
- `sub_agents`: Optional list of sub-agent references
- `description`: Optional agent description

**Decision**: The AgentProvider protocol will return `google.adk.agents.LlmAgent` instances (or BaseAgent), aligning with ADK's type system. The `instruction` field is the primary evolable component.

**Rationale**: Reusing ADK's existing agent types ensures compatibility with the ADK ecosystem and avoids creating parallel abstractions.

**Alternatives Considered**:
- Custom agent wrapper type: Rejected - adds unnecessary abstraction layer
- Dict-based configuration: Rejected - loses type safety and ADK compatibility

### 2. Existing Protocol Patterns in gepa-adk

**Question**: What patterns do existing protocols in `ports/` follow?

**Findings**:

Examined existing protocols:
- `AsyncGEPAAdapter` in `ports/adapter.py`
- `Scorer` in `ports/scorer.py`
- `ProposerProtocol` in `ports/proposer.py`
- `CandidateSelectorProtocol`, `ComponentSelectorProtocol` in `ports/selector.py`

**Common Patterns**:
1. Use `typing.Protocol` with `@runtime_checkable` decorator
2. Google-style docstrings with Examples, Args, Returns, Note sections
3. Minimal interface - only essential methods
4. Type hints for all parameters and return values
5. No external imports (stdlib + domain types only)

**Decision**: Follow existing protocol patterns exactly:
- `@runtime_checkable` decorator for isinstance() checks
- Google-style docstrings
- Pure protocol with no implementation details
- Import from `gepa_adk.domain` for any shared types

**Rationale**: Consistency with existing codebase ensures maintainability and meets ADR-002 requirements.

**Alternatives Considered**:
- ABC-based interface: Rejected per ADR-002 (use Protocol unless lifecycle management needed)
- Async methods: Considered but rejected - persistence is typically sync, and caller can wrap in async if needed

### 3. Error Handling for Non-Existent Agents

**Question**: How should the protocol handle requests for non-existent agents?

**Findings**:

- ADK's `from_config()` raises `FileNotFoundError` for missing config files
- ADK's `_resolve_agent_class()` raises `ValueError` for invalid agent classes
- Existing gepa-adk exceptions inherit from base `EvolutionError` per ADR-009

**Decision**: Define error behavior in protocol docstrings but don't define exception types in ports/ layer. Implementations choose their own exception types.

**Rationale**:
- Keeps ports/ layer pure (no exception class definitions)
- Allows implementations flexibility in error handling
- Protocol documents expected behavior, not specific types

**Alternatives Considered**:
- Define `AgentNotFoundError` in domain/: Possible but not strictly necessary for protocol
- Return Optional[Agent]: Rejected - explicit errors are clearer than None checks

### 4. Sync vs Async Protocol Methods

**Question**: Should AgentProvider methods be async?

**Findings**:

- Constitution Principle II requires async for I/O-bound operations
- However, the AgentProvider is primarily a configuration layer, not I/O layer
- File/database I/O happens in implementations, not the protocol
- Existing protocols like `Scorer` include both sync and async variants

**Decision**: Define sync methods in the protocol. Implementations that need async can:
1. Use async internally and block in the sync method
2. Provide an async wrapper in their implementation

**Rationale**:
- Simplest possible interface for implementers
- Many use cases (in-memory, file-based) don't need async
- Callers who need async can wrap easily with `asyncio.to_thread()`

**Alternatives Considered**:
- Async-only: Rejected - unnecessarily complex for simple use cases
- Both sync and async (like Scorer): Rejected - overkill for config layer

### 5. Return Type for get_agent()

**Question**: What type should `get_agent()` return?

**Findings**:

- ADK's `from_config()` returns `BaseAgent`
- `LlmAgent` is the most common type, with `instruction` as the evolable field
- gepa-adk evolution system operates on instruction strings, not full agents

**Decision**: Return `LlmAgent` type from `get_agent()`. This is the most specific useful type while remaining compatible with ADK.

**Rationale**:
- `LlmAgent` has the `instruction` field that evolution modifies
- More specific than `BaseAgent` while remaining useful
- Users can cast to other types if needed

**Alternatives Considered**:
- Return `BaseAgent`: Too generic, loses `instruction` field access
- Return `dict[str, str]`: Loses agent capabilities, would need reconstruction
- Generic type parameter: Overcomplicated for the use case

## Summary of Decisions

| Decision | Choice | Key Reason |
|----------|--------|------------|
| Return type | `LlmAgent` | Has `instruction` field for evolution |
| Method style | Sync | Simplest for implementers |
| Error handling | Document in docstrings | Keep ports/ layer pure |
| Protocol pattern | `@runtime_checkable Protocol` | Matches existing ports |
| External deps | None in ports/ | ADR-000 compliance |

## Open Questions (Resolved)

1. **Q**: Should we support agent hierarchies (sub-agents)?
   **A**: No - out of scope. Provider returns single agents, hierarchy is implementation concern.

2. **Q**: Should `save_instruction` create new agents?
   **A**: No - it only updates existing agents. Creating agents is implementation-specific.

3. **Q**: Should we expose YAML config path in the protocol?
   **A**: No - implementation detail. Protocol is storage-agnostic.
