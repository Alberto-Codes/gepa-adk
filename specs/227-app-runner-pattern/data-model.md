# Data Model: ADK App/Runner Pattern Integration

**Feature**: 227-app-runner-pattern
**Date**: 2026-01-24

## Overview

This feature adds optional parameters to existing API functions. No new domain models are created. The data flow involves extracting services from ADK's `App` and `Runner` types.

## External Types (from google-adk)

### App (google.adk.apps.app.App)

Pydantic model representing an ADK application container.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Application identifier (valid Python identifier, not "user") |
| `root_agent` | `BaseAgent` | Root agent in the application |
| `plugins` | `list[BasePlugin]` | Application-wide plugins |
| `context_cache_config` | `Optional[ContextCacheConfig]` | Context caching configuration |
| `resumability_config` | `Optional[ResumabilityConfig]` | Pause/resume configuration |
| `events_compaction_config` | `Optional[EventsCompactionConfig]` | Event compaction configuration |

**Validation**: App name must be a valid Python identifier and cannot be "user".

### Runner (google.adk.runners.Runner)

Execution controller for ADK agents.

| Attribute | Type | Description |
|-----------|------|-------------|
| `app_name` | `str` | Application name |
| `agent` | `BaseAgent` | Root agent to run |
| `session_service` | `BaseSessionService` | Session management service (required) |
| `artifact_service` | `Optional[BaseArtifactService]` | Artifact storage service |
| `memory_service` | `Optional[BaseMemoryService]` | Long-term memory service |
| `plugin_manager` | `PluginManager` | Plugin management |
| `context_cache_config` | `Optional[ContextCacheConfig]` | From App if provided |
| `resumability_config` | `Optional[ResumabilityConfig]` | From App if provided |

**Construction**: Either `app` OR (`app_name` + `agent`) must be provided, not both.

### InMemoryRunner (google.adk.runners.InMemoryRunner)

Convenience subclass of Runner with in-memory services pre-configured.

| Default Service | Type |
|-----------------|------|
| `session_service` | `InMemorySessionService` |
| `artifact_service` | `InMemoryArtifactService` |
| `memory_service` | `InMemoryMemoryService` |

## Existing Types (gepa-adk)

### AgentExecutor (gepa_adk.adapters.agent_executor.AgentExecutor)

Already accepts `session_service` in constructor. No changes needed to the class itself.

```python
class AgentExecutor:
    def __init__(
        self,
        session_service: BaseSessionService | None = None,
        app_name: str = "gepa_executor",
    ) -> None:
```

## Service Resolution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     User-Provided Configuration                  │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐               │
│  │  runner  │  │   app    │  │ session_service │               │
│  └────┬─────┘  └────┬─────┘  └───────┬─────────┘               │
│       │             │                │                          │
└───────┼─────────────┼────────────────┼──────────────────────────┘
        │             │                │
        ▼             ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│              _resolve_services() in api.py                       │
│                                                                  │
│   Priority: runner > app > session_service > InMemoryDefault    │
│                                                                  │
│   if runner:                                                     │
│       return runner.session_service, runner.artifact_service    │
│   elif app:                                                      │
│       # App doesn't hold services; use session_service param    │
│       return session_service or InMemorySessionService(), None  │
│   elif session_service:                                          │
│       return session_service, None                              │
│   else:                                                          │
│       return InMemorySessionService(), None                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AgentExecutor                                │
│                                                                  │
│   Uses resolved session_service for all agent executions        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Parameter Precedence

| Priority | Source | session_service | artifact_service | Notes |
|----------|--------|-----------------|------------------|-------|
| 1 (highest) | `runner` | `runner.session_service` | `runner.artifact_service` | Full service extraction |
| 2 | `app` + `session_service` | `session_service` param | None | App provides config, not services |
| 3 | `session_service` only | `session_service` param | None | Current behavior (#226) |
| 4 (lowest) | Nothing provided | `InMemorySessionService()` | None | Default behavior |

## Validation Rules

### FR-010: Configuration Validation

| Scenario | Action |
|----------|--------|
| `runner` and `app` both provided | Log warning, use `runner` |
| `runner` with invalid services | Let ADK raise its errors |
| `app.root_agent` differs from workflow | Log info (intentional override) |

### FR-011: Error Messages

| Condition | Message |
|-----------|---------|
| Both runner and app | "Both runner and app provided; using runner (runner takes precedence)" |
| App with incompatible name | ADK's ValidationError propagates |

## No New Domain Models

This feature does not introduce new domain models. It extends existing API signatures with optional parameters that accept external ADK types.
