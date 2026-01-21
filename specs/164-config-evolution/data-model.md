# Data Model: Generate Content Config Evolution

**Feature**: 164-config-evolution
**Date**: 2026-01-20

## Overview

This document defines the data entities, types, and validation rules for the `generate_content_config` evolution feature.

## Entities

### 1. GenerateContentConfigHandler

Component handler for managing `generate_content_config` evolution on LlmAgent.

**Attributes**: Stateless (no instance attributes)

**Operations**:

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `serialize(agent)` | LlmAgent | str (YAML) | Extract config as YAML text |
| `apply(agent, value)` | LlmAgent, str | GenerateContentConfig or None | Apply YAML config, return original |
| `restore(agent, original)` | LlmAgent, Any | None | Restore original config |

**Relationships**:
- Implements `ComponentHandler` protocol from ports/
- Delegates to `config_utils` functions for serialization/validation
- Registered in `ComponentHandlerRegistry` with key `COMPONENT_GENERATE_CONFIG`

---

### 2. EvolvableConfigParams

Subset of GenerateContentConfig parameters that are subject to evolution.

| Parameter | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `temperature` | float | 0.0 ≤ x ≤ 2.0 | Controls output randomness |
| `top_p` | float | 0.0 ≤ x ≤ 1.0 | Nucleus sampling threshold |
| `top_k` | float | x > 0 | Top-k sampling |
| `max_output_tokens` | int | x > 0 | Maximum response length |
| `presence_penalty` | float | -2.0 ≤ x ≤ 2.0 | Penalizes repeated topics |
| `frequency_penalty` | float | -2.0 ≤ x ≤ 2.0 | Penalizes repeated tokens |

**Notes**:
- All parameters are optional (can evolve subset)
- Parameters outside this set are preserved but not evolved
- Validation failures reject the entire proposed config

---

### 3. ConfigValidationError

Exception raised when config validation fails.

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | str | Human-readable error message |
| `errors` | list[str] | List of individual validation errors |

**Inherits**: `EvolutionError` (domain exception base)

---

### 4. Component Type Constant

**Name**: `COMPONENT_GENERATE_CONFIG`
**Value**: `"generate_content_config"`
**Location**: `domain/types.py`
**Purpose**: Registry key for handler lookup and component identification

---

## Type Aliases

### ConfigDict

```python
ConfigDict: TypeAlias = dict[str, float | int | None]
```

Dictionary representation of evolvable config parameters.

---

## Validation Rules

### Parameter Constraints

```
temperature:
  - Type: float
  - Range: [0.0, 2.0] inclusive
  - Required: No

top_p:
  - Type: float
  - Range: [0.0, 1.0] inclusive
  - Required: No

top_k:
  - Type: float
  - Range: (0, ∞)
  - Required: No

max_output_tokens:
  - Type: int
  - Range: (0, ∞)
  - Required: No

presence_penalty:
  - Type: float
  - Range: [-2.0, 2.0] inclusive
  - Required: No

frequency_penalty:
  - Type: float
  - Range: [-2.0, 2.0] inclusive
  - Required: No
```

### Validation Behavior

| Scenario | Behavior |
|----------|----------|
| Constraint violation | Return errors, reject config |
| Unknown parameter | Log warning, include in config |
| Malformed YAML | Raise ConfigValidationError |
| Empty string input | Return empty config or None |
| Partial config | Merge with existing values |

---

## State Transitions

### Handler Apply/Restore Cycle

```
State: agent.generate_content_config

[Original]
    │
    ▼ apply(agent, yaml_value)
[Modified] ──→ returns original for restore
    │
    ▼ restore(agent, original)
[Original]
```

### Config Evolution Flow

```
[Agent Config] ──serialize()──→ [YAML Text] ──→ [Reflection Agent]
                                                      │
                                                      ▼
[Agent Config] ←──apply()───── [Proposed YAML] ←──[Proposed Text]
                                     │
                                     ▼
                              [Validation]
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                    [Valid]               [Invalid]
                          │                     │
                          ▼                     ▼
                 [Apply to Agent]      [Keep Original]
```

---

## Serialization Format

### YAML Schema

```yaml
# LLM Generation Parameters
# temperature: Controls randomness (0.0=deterministic, 2.0=creative)
temperature: <float>
# top_p: Nucleus sampling threshold (0.0-1.0)
top_p: <float>
# top_k: Top-k sampling (higher=more diverse)
top_k: <float>
# max_output_tokens: Maximum response length
max_output_tokens: <int>
# presence_penalty: Penalizes repeated topics (-2.0 to 2.0)
presence_penalty: <float>
# frequency_penalty: Penalizes repeated tokens (-2.0 to 2.0)
frequency_penalty: <float>
```

### Example Serialized Config

```yaml
# LLM Generation Parameters
# temperature: Controls randomness (0.0=deterministic, 2.0=creative)
temperature: 0.7
# top_p: Nucleus sampling threshold (0.0-1.0)
top_p: 0.9
# max_output_tokens: Maximum response length
max_output_tokens: 1024
```

---

## Integration Points

### ComponentHandlerRegistry

```python
# Registration at module load time
component_handlers.register(COMPONENT_GENERATE_CONFIG, GenerateContentConfigHandler())
```

### ComponentReflectionRegistry

```python
# Registration for reflection agent selection
component_registry.register(COMPONENT_GENERATE_CONFIG, create_config_reflection_agent)
```

### Usage in ADKAdapter

```python
# Applied automatically via registry dispatch
originals = self._apply_candidate({"generate_content_config": yaml_text})
# ... evaluation ...
self._restore_agent(originals)
```
