# Data Model: Wire ADK Reflection Agent into evolve() API

**Feature Branch**: `021-adk-reflection-evolve`
**Date**: 2026-01-14

## Overview

This feature does not introduce new data entities. It wires existing components together. This document describes the entities involved in the integration.

## Existing Entities Used

### ReflectionFn (Type Alias)

**Location**: `src/gepa_adk/engine/proposer.py:39`

```python
ReflectionFn = Callable[[str, list[dict[str, Any]]], Awaitable[str]]
```

**Purpose**: Callable signature for reflection functions that generate improved instructions.

**Pattern Origin**: Analogous to GEPA's `LanguageModel` protocol (`gepa/proposer/reflective_mutation/base.py:27-28`). See [research.md](research.md#gepa-dev-dependency---inspiration) for details.

**Parameters**:
- `current_instruction` (str): The instruction text to improve
- `feedback` (list[dict[str, Any]]): List of evaluation feedback dictionaries

**Returns**: str - Improved instruction text

### Session State Keys (Constants)

**Location**: `src/gepa_adk/engine/proposer.py:44-52`

| Key | Type | Description |
|-----|------|-------------|
| `current_instruction` | str | The agent instruction being improved |
| `execution_feedback` | str | JSON-serialized list of feedback dictionaries |

### LlmAgent (External)

**Source**: `google.adk.agents.LlmAgent`

**Purpose**: ADK agent class used for both:
1. The target agent being evolved
2. The optional reflection agent for generating proposals

**Key Attributes Used**:
- `name` (str): Agent identifier for logging
- `instruction` (str): System instruction (target of evolution)
- `model` (str): LLM model identifier

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         evolve() API                            │
│  reflection_agent: LlmAgent | None                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ADKAdapter                               │
│  reflection_agent → create_adk_reflection_fn() → adk_reflection │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               AsyncReflectiveMutationProposer                   │
│  adk_reflection_fn: ReflectionFn | None                         │
│  Uses ADK reflection OR LiteLLM fallback                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Session State (per reflection)                │
│  - current_instruction: str                                     │
│  - execution_feedback: str (JSON)                               │
└─────────────────────────────────────────────────────────────────┘
```

## State Transitions

This feature does not introduce new state machines. The existing evolution loop states remain unchanged:

1. **EVALUATING**: Agent runs on trainset examples
2. **PROPOSING**: Reflection generates new instruction (now via ADK agent if configured)
3. **VALIDATING**: StateGuard checks token preservation
4. **COMPLETED**: Best instruction selected

## Validation Rules

No new validation rules introduced. Existing validations apply:

| Entity | Validation | Location |
|--------|------------|----------|
| `reflection_agent` | Must be LlmAgent if provided | ADKAdapter.__init__() |
| `current_instruction` | Expected string; no explicit validation | create_adk_reflection_fn() |
| `feedback` | Expected list of dictionaries; no explicit validation | create_adk_reflection_fn() |
| reflection output | Must be non-empty string | AsyncReflectiveMutationProposer.propose() |

## Data Flow

```
Input:
  reflection_agent (LlmAgent) → ADKAdapter
      ↓
  create_adk_reflection_fn(reflection_agent)
      ↓
  adk_reflection_fn (ReflectionFn)
      ↓
  AsyncReflectiveMutationProposer(adk_reflection_fn=adk_reflection_fn)

During Evolution:
  current_instruction + feedback
      ↓
  adk_reflection_fn(current_instruction, feedback)
      ↓
  Session initialized with state:
    - current_instruction = current_instruction
    - execution_feedback = json.dumps(feedback)
      ↓
  ADK Runner executes reflection_agent
      ↓
  improved_instruction (str)
```

## No Schema Changes

- No database schema changes
- No new Pydantic models
- No new protocol definitions
- No changes to EvolutionResult or EvolutionConfig
