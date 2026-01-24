# API Contracts: App/Runner Pattern

**Feature**: 227-app-runner-pattern
**Date**: 2026-01-24

## Updated Function Signatures

### evolve_workflow()

**Location**: `src/gepa_adk/api.py`

```python
async def evolve_workflow(
    workflow: SequentialAgent | LoopAgent | ParallelAgent,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    primary: str | None = None,
    max_depth: int = 5,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,
    round_robin: bool = False,
    components: dict[str, list[str]] | None = None,
    session_service: BaseSessionService | None = None,  # Existing (#226)
    app: App | None = None,                              # NEW
    runner: Runner | None = None,                        # NEW
) -> MultiAgentEvolutionResult:
    """Evolve LlmAgents within a workflow agent structure.

    [... existing docstring ...]

    Args:
        [... existing args ...]
        session_service: Optional ADK session service for state management.
            If None (default), creates an InMemorySessionService internally.
            Pass a custom service to persist sessions. Lower precedence than
            runner parameter.
        app: Optional ADK App instance. Provides application configuration
            (name, plugins, caching). When provided without runner, uses
            session_service parameter or creates InMemorySessionService.
            Lower precedence than runner parameter.
        runner: Optional ADK Runner instance. Provides pre-configured services
            (session, artifact, memory). Takes highest precedence over app
            and session_service parameters. When provided, evolution uses
            runner.session_service and runner.artifact_service.

    [... existing returns, raises, examples ...]

    Examples:
        Using pre-configured Runner:

        ```python
        from google.adk.runners import Runner
        from google.adk.sessions import SqliteSessionService
        from google.adk.artifacts import FileArtifactService

        # Configure runner with custom services
        session_service = SqliteSessionService(db_path="sessions.db")
        artifact_service = FileArtifactService(base_path="./artifacts")

        runner = Runner(
            app_name="my_evolution",
            agent=pipeline,  # Can differ from workflow
            session_service=session_service,
            artifact_service=artifact_service,
        )

        # Evolution uses runner's services
        result = await evolve_workflow(
            workflow=pipeline,
            trainset=trainset,
            runner=runner,
        )
        ```

        Using App for configuration:

        ```python
        from google.adk.apps.app import App
        from google.adk.sessions import DatabaseSessionService

        app = App(
            name="evolution_app",
            root_agent=pipeline,
            plugins=[MonitoringPlugin()],
        )

        # App provides config; session_service provides persistence
        result = await evolve_workflow(
            workflow=pipeline,
            trainset=trainset,
            app=app,
            session_service=DatabaseSessionService(...),
        )
        ```
    """
```

### evolve_group()

**Location**: `src/gepa_adk/api.py`

```python
async def evolve_group(
    agents: dict[str, LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    components: dict[str, list[str]] | None = None,
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
    state_guard: StateGuard | None = None,
    component_selector: ComponentSelectorProtocol | str | None = None,
    reflection_agent: LlmAgent | None = None,
    trajectory_config: TrajectoryConfig | None = None,
    workflow: SequentialAgent | LoopAgent | ParallelAgent | None = None,
    session_service: BaseSessionService | None = None,  # Existing (#226)
    app: App | None = None,                              # NEW
    runner: Runner | None = None,                        # NEW
) -> MultiAgentEvolutionResult:
    """Evolve multiple agents together with per-agent component configuration.

    [... existing docstring with new parameters ...]
    """
```

## Internal Helper Function

**Location**: `src/gepa_adk/api.py` (new private function)

```python
def _resolve_evolution_services(
    runner: Runner | None,
    app: App | None,
    session_service: BaseSessionService | None,
) -> tuple[BaseSessionService, BaseArtifactService | None, str | None]:
    """Resolve services from runner/app/session_service with precedence.

    Precedence: runner > app > session_service > InMemorySessionService default.

    Args:
        runner: Optional pre-configured ADK Runner.
        app: Optional ADK App for configuration.
        session_service: Optional explicit session service.

    Returns:
        Tuple of (resolved_session_service, artifact_service, app_name).
        artifact_service may be None if not available from runner.
        app_name may be None if only session_service provided.

    Note:
        Logs warning if both runner and app are provided.
    """
```

## Type Imports

**Location**: `src/gepa_adk/api.py`

```python
# Add to existing imports
from google.adk.apps.app import App
from google.adk.runners import Runner
from google.adk.artifacts import BaseArtifactService  # If not already imported
```

## Backward Compatibility

| Existing Call | Behavior After Change |
|---------------|----------------------|
| `evolve_workflow(workflow, trainset)` | Unchanged (InMemorySessionService) |
| `evolve_workflow(workflow, trainset, session_service=svc)` | Unchanged (uses svc) |
| `evolve_workflow(workflow, trainset, runner=runner)` | NEW: Uses runner's services |
| `evolve_workflow(workflow, trainset, app=app)` | NEW: Uses app config, default session |
| `evolve_workflow(workflow, trainset, runner=r, app=a)` | NEW: Warning, uses runner |
