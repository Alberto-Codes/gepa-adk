# Data Model: Wire Reflection Model Config to Proposer

**Feature**: 031-wire-reflection-model
**Date**: 2026-01-17

## Overview

This feature does not introduce new entities. It wires an existing configuration field (`EvolutionConfig.reflection_model`) through the adapter layer to an existing component (`AsyncReflectiveMutationProposer`).

## Existing Entities (No Changes)

### EvolutionConfig

**Location**: `src/gepa_adk/domain/models.py`
**Purpose**: Configuration parameters for evolution runs

| Field | Type | Default | Validation | Description |
|-------|------|---------|------------|-------------|
| `reflection_model` | `str` | `"gemini-2.5-flash"` | Non-empty string | LiteLLM model identifier for reflection/mutation operations |

**Existing validation** (lines 122-128):
```python
if not self.reflection_model:
    raise ConfigurationError(
        "reflection_model must be a non-empty string",
        field="reflection_model",
        value=self.reflection_model,
        constraint="non-empty string",
    )
```

### AsyncReflectiveMutationProposer

**Location**: `src/gepa_adk/engine/proposer.py`
**Purpose**: Generates mutation proposals using LLM reflection

| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `model` | `str` | `"ollama/gpt-oss:20b"` | Non-empty string | LiteLLM model identifier for LLM calls |

**After wiring**: The proposer's `model` parameter will receive the value from `EvolutionConfig.reflection_model` instead of using its hardcoded default.

## Data Flow

```
┌─────────────────────────────────┐
│     EvolutionConfig             │
│  reflection_model: str          │
│  (default: "gemini-2.5-flash")  │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│     api.evolve() / evolve_group │
│  Extracts config.reflection_model│
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  ADKAdapter / MultiAgentAdapter │
│  reflection_model: str param    │
│  (NEW parameter)                │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ AsyncReflectiveMutationProposer │
│  model: str                     │
│  (uses configured value)        │
└─────────────────────────────────┘
```

## Parameter Additions

### ADKAdapter.__init__()

**New parameter**:
```python
reflection_model: str = "gemini-2.5-flash"
```

**Usage**: Passed to `AsyncReflectiveMutationProposer(model=reflection_model)` when creating default proposer

### MultiAgentAdapter.__init__()

**New parameter**:
```python
reflection_model: str = "gemini-2.5-flash"
```

**Usage**: Passed to `AsyncReflectiveMutationProposer(model=reflection_model)` when creating default proposer

## State Transitions

N/A - This feature does not involve state transitions. The `reflection_model` is a static configuration value set at initialization and used throughout the evolution run.

## Relationships

```
EvolutionConfig  ──(1:1)──▶  evolve()/evolve_group()
                                    │
                                    ▼
                            ADKAdapter/MultiAgentAdapter
                                    │
                                    ▼
                       AsyncReflectiveMutationProposer
                                    │
                                    ▼
                              LiteLLM API
```

- One `EvolutionConfig` per evolution run
- One adapter per evolution run
- One proposer per adapter (created at adapter init)
- Proposer makes multiple LLM calls using the configured model
