# Quickstart: ADK App/Runner Pattern Integration

**Feature**: 227-app-runner-pattern
**Date**: 2026-01-24

## Overview

This feature enables you to pass pre-configured ADK `App` or `Runner` instances to gepa-adk's evolution APIs. This allows evolution to use your existing infrastructure (session services, artifact services, plugins) instead of creating defaults.

## Prerequisites

- gepa-adk >= 0.4.0 (after this feature is released)
- google-adk >= 1.22.0

## Basic Usage

### Option 1: Pass a Pre-configured Runner (Recommended)

Use this when you already have a Runner with custom services configured.

```python
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.artifacts import GcsArtifactService
from gepa_adk import evolve_workflow

# Your existing production setup
session_service = DatabaseSessionService(
    connection_string="postgresql://...",
)
artifact_service = GcsArtifactService(
    bucket_name="my-artifacts",
)

# Create workflow
generator = LlmAgent(name="generator", model="gemini-2.5-flash", instruction="...")
reviewer = LlmAgent(name="reviewer", model="gemini-2.5-flash", instruction="...")
pipeline = SequentialAgent(name="pipeline", sub_agents=[generator, reviewer])

# Configure runner with your services
runner = Runner(
    app_name="my_evolution",
    agent=pipeline,
    session_service=session_service,
    artifact_service=artifact_service,
)

# Evolution uses your runner's services
result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
    runner=runner,
)

# Sessions are persisted in your database
# Artifacts are stored in your GCS bucket
```

### Option 2: Pass an App with Session Service

Use this when you have an App configuration but want to specify session storage separately.

```python
from google.adk.apps.app import App
from google.adk.sessions import SqliteSessionService
from gepa_adk import evolve_workflow

# Create app with configuration
app = App(
    name="evolution_app",
    root_agent=pipeline,
    plugins=[LoggingPlugin(), MetricsPlugin()],
)

# Provide session service separately
session_service = SqliteSessionService(db_path="evolution_sessions.db")

result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
    app=app,
    session_service=session_service,
)
```

### Option 3: Use InMemoryRunner for Development

For local development and testing, use InMemoryRunner which pre-configures in-memory services.

```python
from google.adk.runners import InMemoryRunner
from gepa_adk import evolve_workflow

# InMemoryRunner provides in-memory session, artifact, and memory services
runner = InMemoryRunner(agent=pipeline)

result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
    runner=runner,
)
```

## Parameter Precedence

When multiple configuration sources are provided:

1. **runner** (highest priority) - Uses runner's services
2. **app** - Provides configuration; uses session_service param or creates default
3. **session_service** - Direct session service
4. **default** (lowest) - Creates InMemorySessionService

```python
# Example: runner takes precedence
result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
    runner=runner,           # Used (highest priority)
    app=app,                 # Ignored (warning logged)
    session_service=svc,     # Ignored
)
```

## Backward Compatibility

Existing code continues to work unchanged:

```python
# This still works exactly as before
result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
)

# This also still works
result = await evolve_workflow(
    workflow=pipeline,
    trainset=training_data,
    session_service=my_session_service,
)
```

## Limitations

### Plugin Passthrough (Deferred)

Currently, plugins from App or Runner are **not automatically applied** during evolution. This is because AgentExecutor creates its own internal Runner for each execution.

To use plugins, configure them on the agents themselves or wait for a future enhancement.

### Artifact Service Usage

When providing a runner with artifact_service, artifacts generated during evolution (if any) will use your artifact service. However, gepa-adk's core evolution loop does not currently generate artifacts, so this is primarily for future compatibility.

## Troubleshooting

### Warning: "Both runner and app provided"

This warning indicates you passed both parameters. The runner will be used. If you intended this, the warning is informational. To silence it, pass only runner.

### TypeError: App validation failed

ADK's App class validates that the name is a valid Python identifier and not "user". Ensure your app name meets these requirements:

```python
# Good
app = App(name="evolution_app", ...)
app = App(name="my_pipeline_v2", ...)

# Bad - will raise ValidationError
app = App(name="my-app", ...)    # Hyphens not allowed
app = App(name="user", ...)       # Reserved name
app = App(name="123app", ...)     # Can't start with number
```

## Next Steps

- See [ADK Integration Guide](../../docs/guides/workflows.md) for comprehensive examples
- Review [API Reference](../../docs/reference/api.md) for full parameter documentation
