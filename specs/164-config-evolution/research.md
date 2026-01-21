# Research: Generate Content Config Evolution

**Feature**: 164-config-evolution
**Date**: 2026-01-20

## Research Summary

This document consolidates research findings for implementing `generate_content_config` as an evolvable component in GEPA.

## 1. GenerateContentConfig Structure

### Decision
Use YAML serialization for GenerateContentConfig with selective parameter extraction.

### Rationale
- GenerateContentConfig from `google.genai.types` is a Pydantic v2 model
- Has `model_dump()` for serialization and direct dict instantiation for deserialization
- YAML is human-readable and LLM-friendly, matching spec requirements
- Round-trip tested: YAML serialize → parse → reconstruct works correctly

### Alternatives Considered
| Alternative | Rejected Because |
|-------------|------------------|
| JSON serialization | Less readable, no comment support for parameter descriptions |
| Custom string format | Non-standard, harder to parse, error-prone |
| Python source code (like OutputSchemaHandler) | Overly complex for simple parameter dict |

### Key Findings
GenerateContentConfig has 25+ parameters, but evolution should focus on core LLM parameters:

**Primary evolution targets** (core generation parameters):
- `temperature`: float (0.0-2.0) - Controls randomness
- `top_p`: float (0.0-1.0) - Nucleus sampling threshold
- `top_k`: float (positive) - Top-k sampling
- `max_output_tokens`: int (positive) - Output length limit

**Secondary evolution targets** (tuning parameters):
- `presence_penalty`: float (-2.0 to 2.0) - Repetition penalty
- `frequency_penalty`: float (-2.0 to 2.0) - Token frequency penalty
- `seed`: int - Deterministic generation

**Not evolved** (complex/sensitive):
- `safety_settings` - Security-critical, separate consideration needed
- `tools`, `tool_config` - Agent tools, managed separately
- `response_schema`, `response_json_schema` - Coupled with output_schema handler
- `system_instruction` - Already evolved via instruction handler
- `http_options`, `cached_content` - Infrastructure settings

## 2. ComponentHandler Protocol Pattern

### Decision
Implement `GenerateContentConfigHandler` following the established InstructionHandler/OutputSchemaHandler pattern.

### Rationale
- Proven pattern already in codebase (`component_handlers.py:222-418`)
- Protocol is `@runtime_checkable` with three methods: serialize, apply, restore
- Stateless handlers with state in agent object
- Graceful error handling: log warnings, don't raise exceptions in apply()

### Key Implementation Points
1. **serialize()**: Extract config, filter to evolvable params, return YAML string
2. **apply()**: Parse YAML, validate constraints, update agent, return original for restore
3. **restore()**: Simply set agent.generate_content_config back to original
4. **Registration**: Add to module-level registration in `component_handlers.py`

### Error Handling Strategy
Follow OutputSchemaHandler pattern:
```python
try:
    new_config = deserialize_config(value)
    validate_config(new_config)  # Constraint checks
    agent.generate_content_config = new_config
except ConfigValidationError as e:
    logger.warning("config_handler.apply.failed", error=str(e))
    # Keep original - don't modify agent
return original
```

## 3. Validation Constraints

### Decision
Implement validation with known Gemini API constraints as defaults, allowing unknown parameters to pass (for model-specific support).

### Rationale
- Hard constraints prevent runtime errors from invalid API calls
- Warning-only for unknown params supports future model additions
- Per-spec edge case: "Validation warns about unsupported parameters but does not fail"

### Constraint Specification
| Parameter | Constraint | Source |
|-----------|------------|--------|
| `temperature` | 0.0 ≤ x ≤ 2.0 | Gemini API docs |
| `top_p` | 0.0 ≤ x ≤ 1.0 | Gemini API docs |
| `top_k` | x > 0 (positive) | Gemini API docs |
| `max_output_tokens` | x > 0 (positive int) | Gemini API docs |
| `presence_penalty` | -2.0 ≤ x ≤ 2.0 | Gemini API docs |
| `frequency_penalty` | -2.0 ≤ x ≤ 2.0 | Gemini API docs |

### Validation Function Design
```python
def validate_generate_config(config_dict: dict[str, Any]) -> list[str]:
    """Validate config dict, return list of validation errors."""
    errors = []

    if "temperature" in config_dict:
        t = config_dict["temperature"]
        if not (0.0 <= t <= 2.0):
            errors.append(f"temperature must be 0.0-2.0, got {t}")

    # ... other validations ...

    return errors  # Empty list = valid
```

## 4. Serialization Format

### Decision
Use YAML with parameter descriptions as comments.

### Rationale
- FR-009 requires "parameter descriptions/comments in serialized output"
- YAML supports inline comments naturally
- More LLM-friendly than JSON for reasoning about parameters

### Format Example
```yaml
# LLM Generation Parameters
# temperature: Controls randomness (0.0=deterministic, 2.0=creative)
temperature: 0.7
# top_p: Nucleus sampling threshold (0.0-1.0)
top_p: 0.9
# top_k: Top-k sampling (higher=more diverse)
top_k: 40.0
# max_output_tokens: Maximum response length
max_output_tokens: 1024
```

### Serialization Implementation
```python
PARAM_DESCRIPTIONS = {
    "temperature": "Controls randomness (0.0=deterministic, 2.0=creative)",
    "top_p": "Nucleus sampling threshold (0.0-1.0)",
    "top_k": "Top-k sampling (higher=more diverse)",
    "max_output_tokens": "Maximum response length",
    "presence_penalty": "Penalizes repeated topics (-2.0 to 2.0)",
    "frequency_penalty": "Penalizes repeated tokens (-2.0 to 2.0)",
}

def serialize_generate_config(config: GenerateContentConfig) -> str:
    """Serialize config to YAML with parameter descriptions."""
    data = config.model_dump(exclude_none=True)

    # Filter to evolvable parameters only
    evolvable = {k: v for k, v in data.items() if k in PARAM_DESCRIPTIONS}

    lines = ["# LLM Generation Parameters"]
    for key, value in evolvable.items():
        desc = PARAM_DESCRIPTIONS.get(key, "")
        if desc:
            lines.append(f"# {key}: {desc}")
        lines.append(f"{key}: {value}")

    return "\n".join(lines)
```

## 5. Reflection Agent Integration

### Decision
Create `create_config_reflection_agent` factory and register with `component_registry`.

### Rationale
- Follows pattern from `reflection_agents.py` with registry-based selection
- Config evolution benefits from domain-specific instruction
- No validation tool needed (YAML parsing provides validation)

### Reflection Instruction Template
```python
CONFIG_REFLECTION_INSTRUCTION = """## Current Configuration
{component_text}

## Trials
{trials}

## Instructions
Propose an improved LLM generation configuration based on the trials above.

Guidelines:
- temperature: Lower (0.0-0.5) for deterministic tasks, higher (0.7-1.5) for creative tasks
- top_p: Usually 0.8-0.95 works well; lower for more focused output
- top_k: 20-50 typical; lower for more focused, higher for diverse
- max_output_tokens: Set based on expected response length

Return ONLY the YAML configuration, preserving the comment format.
Do not wrap in markdown code fences."""
```

## 6. File Organization

### Decision
Create new `config_utils.py` in utils/ for serialization/deserialization/validation.

### Rationale
- Follows pattern of `schema_utils.py` for output_schema handling
- Keeps handler thin (delegates to utils)
- Utilities can be tested independently

### File Structure
```
src/gepa_adk/
├── domain/types.py           # Add COMPONENT_GENERATE_CONFIG
├── utils/config_utils.py     # NEW: serialize/deserialize/validate
└── adapters/component_handlers.py  # Add GenerateContentConfigHandler
```

## 7. Partial Config Merging

### Decision
Support partial configs that merge with existing values.

### Rationale
- Per spec edge case: "unspecified parameters retain their current values"
- Enables focused evolution on specific parameters
- Prevents loss of existing config values

### Merge Strategy
```python
def deserialize_generate_config(
    yaml_text: str,
    existing: GenerateContentConfig | None = None,
) -> GenerateContentConfig:
    """Deserialize YAML to config, merging with existing if provided."""
    parsed = yaml.safe_load(yaml_text)

    if existing is not None:
        # Start with existing values, overlay parsed
        base = existing.model_dump(exclude_none=True)
        base.update(parsed)
        parsed = base

    return GenerateContentConfig(**parsed)
```

## 8. None/Default Config Handling

### Decision
Return empty string from serialize when config is None; apply() creates new config from scratch.

### Rationale
- Per spec edge case: "returns a default empty config representation or indicates no config exists"
- Consistent with InstructionHandler pattern (returns "" for None)
- Empty YAML is valid and can be evolved from

### Implementation
```python
def serialize(self, agent: LlmAgent) -> str:
    config = getattr(agent, "generate_content_config", None)
    if config is None:
        return ""
    return serialize_generate_config(config)
```

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Serialization format | YAML with comments |
| Validation approach | Hard fail on constraint violations, warn on unknowns |
| Error handling | Graceful degradation, keep original on failure |
| Partial configs | Merge with existing values |
| None handling | Return empty string, allow evolution from scratch |
| File organization | New config_utils.py in utils/ |
| Reflection agent | Custom factory with config-focused instruction |
| Evolvable parameters | temperature, top_p, top_k, max_output_tokens, presence/frequency_penalty |

## Dependencies Confirmed

- `google.genai.types.GenerateContentConfig` - Pydantic v2 model with model_dump()
- `yaml` - Python stdlib (PyYAML in project deps)
- `structlog` - Already in use for logging

## Next Steps

1. **Phase 1**: Create data-model.md, contracts/, quickstart.md
2. **Implementation**: Follow project structure in plan.md
