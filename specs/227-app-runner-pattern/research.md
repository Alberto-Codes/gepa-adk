# Research: ADK App/Runner Pattern Integration

**Feature**: 227-app-runner-pattern
**Date**: 2026-01-24

## 1. ADK App Class API Surface

### Decision
Use ADK's `App` class as a configuration container for `Runner`. App provides `name`, `root_agent`, `plugins`, `context_cache_config`, `resumability_config`, and `events_compaction_config`.

### Rationale
The App class is a Pydantic BaseModel that encapsulates:
- `name: str` - Application identifier
- `root_agent: BaseAgent` - Root agent (we'll use our workflow agent)
- `plugins: list[BasePlugin]` - Application-wide plugins
- `context_cache_config: Optional[ContextCacheConfig]` - Context caching
- `resumability_config: Optional[ResumabilityConfig]` - Pause/resume support
- `events_compaction_config: Optional[EventsCompactionConfig]` - Event compaction

**Important**: App does NOT directly hold session_service, artifact_service, or memory_service. These are passed to Runner separately.

### Alternatives Considered
- **Create wrapper class**: Rejected - adds complexity without benefit
- **Extract individual properties**: Current approach - extract what we need

## 2. ADK Runner Class API Surface

### Decision
Accept `Runner` instance directly and extract its services: `session_service`, `artifact_service`, `memory_service`, `plugin_manager`.

### Rationale
Runner constructor accepts:
```python
Runner(
    app: Optional[App] = None,           # OR app_name + agent
    app_name: Optional[str] = None,
    agent: Optional[BaseAgent] = None,
    plugins: Optional[List[BasePlugin]] = None,  # Deprecated
    artifact_service: Optional[BaseArtifactService] = None,
    session_service: BaseSessionService,  # REQUIRED
    memory_service: Optional[BaseMemoryService] = None,
    credential_service: Optional[BaseCredentialService] = None,
)
```

Runner exposes these as public attributes:
- `runner.session_service` - BaseSessionService (always set)
- `runner.artifact_service` - Optional[BaseArtifactService]
- `runner.memory_service` - Optional[BaseMemoryService]
- `runner.plugin_manager` - PluginManager (from plugins)
- `runner.app_name` - str
- `runner.agent` - BaseAgent

### Alternatives Considered
- **Use InMemoryRunner**: Simpler but doesn't allow custom services
- **Create Runner internally from App**: Would work but loses flexibility

## 3. Service Extraction Strategy

### Decision
Implement service extraction with clear precedence: `runner` > `app` > `session_service` > default.

### Rationale
When a user provides multiple configuration sources, we need deterministic precedence:

1. **runner provided**: Use `runner.session_service`, `runner.artifact_service`, `runner.memory_service`
2. **app provided (no runner)**: Create a Runner from App to get standard ADK behavior
3. **session_service provided (no runner/app)**: Use it directly (current behavior)
4. **nothing provided**: Create InMemorySessionService (current default)

### Implementation Pattern
```python
def _resolve_services(
    runner: Runner | None,
    app: App | None,
    session_service: BaseSessionService | None,
) -> tuple[BaseSessionService, BaseArtifactService | None]:
    """Extract services with precedence: runner > app > session_service > default."""
    if runner is not None:
        return runner.session_service, runner.artifact_service

    if app is not None:
        # Note: App doesn't hold services directly
        # User must provide session_service with app, or we create default
        return session_service or InMemorySessionService(), None

    return session_service or InMemorySessionService(), None
```

### Alternatives Considered
- **Reject conflicting parameters**: Too strict, blocks valid use cases
- **Merge configurations**: Too complex, unclear semantics

## 4. Plugin Integration

### Decision
Extract plugins from Runner's `plugin_manager` but do NOT integrate them into evolution execution. Plugins are Runner-level middleware that run during `runner.run_async()`. Since AgentExecutor creates its own Runner internally, user plugins won't automatically apply.

### Rationale
ADK plugins are registered via `PluginManager` and execute during Runner's `run_async()`:
- `before_run_callback` - Before agent execution
- `on_event_callback` - For each event
- `after_run_callback` - After execution completes

Current AgentExecutor creates a fresh Runner for each execution:
```python
runner = Runner(
    agent=effective_agent,
    app_name=self._app_name,
    session_service=self._session_service,
)
```

To support user plugins, AgentExecutor would need to accept plugins parameter and pass them to its internal Runner. This is a larger change.

### Current Scope
For this feature, we focus on **service extraction** (session_service, artifact_service). Plugin passthrough is deferred to a future enhancement.

### Alternatives Considered
- **Full plugin integration**: Requires AgentExecutor changes, deferred
- **Ignore plugins**: Current approach for MVP, document limitation

## 5. Backward Compatibility Strategy

### Decision
All new parameters are optional with `None` defaults. Existing code works unchanged.

### Rationale
Current signatures:
```python
async def evolve_workflow(
    workflow: ...,
    trainset: ...,
    ...
    session_service: BaseSessionService | None = None,  # Added in #226
) -> MultiAgentEvolutionResult:
```

New signatures:
```python
async def evolve_workflow(
    workflow: ...,
    trainset: ...,
    ...
    session_service: BaseSessionService | None = None,
    app: App | None = None,        # NEW
    runner: Runner | None = None,  # NEW
) -> MultiAgentEvolutionResult:
```

Behavior:
- If nothing provided → InMemorySessionService (unchanged)
- If session_service provided → Use it (unchanged)
- If app provided → Extract name, use provided session_service or create default
- If runner provided → Extract services from runner

### Alternatives Considered
- **Remove session_service in favor of runner**: Breaking change, rejected
- **Require runner for all usage**: Too disruptive, rejected

## 6. Validation and Error Handling

### Decision
Validate at API entry point with clear error messages:
- If both `runner` and `app` provided: Log warning, use runner (documented precedence)
- If `runner` has incompatible configuration: Let ADK raise its own errors
- If `app.root_agent` differs from workflow: Log warning (user may be intentional)

### Rationale
Following fail-fast principle from spec (FR-010, FR-011), validation happens before evolution starts. However, we avoid being too restrictive - users may have valid reasons for unusual configurations.

### Error Messages
```python
if runner is not None and app is not None:
    logger.warning(
        "Both runner and app provided; using runner (runner takes precedence)",
        runner_app_name=runner.app_name,
        app_name=app.name,
    )
```

### Alternatives Considered
- **Raise error on conflict**: Too strict, valid use cases exist
- **Merge runner and app**: Ambiguous semantics, rejected

## 7. Type Hints and Imports

### Decision
Import `App` from `google.adk.apps.app` and `Runner` from `google.adk.runners` in `api.py`.

### Rationale
These are public ADK types. Import at module level for type hints:
```python
from google.adk.apps.app import App
from google.adk.runners import Runner
```

Note: `Runner` is already imported in `agent_executor.py`. Adding `App` import there is optional since we may just pass extracted services.

### Alternatives Considered
- **Runtime imports only**: Loses type checking benefits
- **Protocol wrappers**: Unnecessary complexity

## Summary

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| App usage | Config container for name/plugins | App doesn't hold services directly |
| Runner usage | Extract services directly | Runner exposes session_service, artifact_service as attributes |
| Precedence | runner > app > session_service > default | Clear, predictable behavior |
| Plugins | Defer full integration | Requires AgentExecutor changes, MVP focuses on services |
| Compatibility | All new params optional | Existing code unchanged |
| Validation | Warn on conflicts, don't error | Allow valid edge cases |
