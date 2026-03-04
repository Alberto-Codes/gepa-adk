"""Utilities for GenerateContentConfig serialization, deserialization, and validation.

This module provides functions for converting GenerateContentConfig objects
to and from YAML format, with support for partial config merging and
parameter validation.

Attributes:
    EVOLVABLE_PARAMS (dict): Parameter descriptions for evolvable config fields.
    serialize_generate_config (function): Convert config to YAML with descriptions.
    deserialize_generate_config (function): Parse YAML to config, with merge support.
    validate_generate_config (function): Validate config dict against constraints.

Examples:
    Serialize and deserialize a config:

    ```python
    from google.genai.types import GenerateContentConfig
    from gepa_adk.adapters.config_adapter import (
        serialize_generate_config,
        deserialize_generate_config,
        validate_generate_config,
    )

    config = GenerateContentConfig(temperature=0.7, top_p=0.9)
    yaml_text = serialize_generate_config(config)

    # Parse with merge
    new_config = deserialize_generate_config("temperature: 0.5", existing=config)
    # new_config.temperature == 0.5, new_config.top_p == 0.9 (preserved)

    # Validate before applying
    errors = validate_generate_config({"temperature": 3.0})
    # errors == ["temperature must be 0.0-2.0, got 3.0"]
    ```

See Also:
    - [`ConfigHdlr`][gepa_adk.adapters.components.component_handlers.GenerateContentConfigHandler]:
      Handler using these utilities.
    - [`ConfigValidationError`][gepa_adk.domain.exceptions.ConfigValidationError]:
      Error type for invalid configs.

Note:
    This module is in the adapters/ layer and may import external library types
    (google.genai.types) directly following hexagonal architecture.
"""

from __future__ import annotations

from typing import Any

import structlog
import yaml
from google.genai.types import GenerateContentConfig

from gepa_adk.domain.exceptions import ConfigValidationError

logger = structlog.get_logger(__name__)

# Parameter descriptions for YAML comments
EVOLVABLE_PARAMS: dict[str, str] = {
    "temperature": "Controls randomness (0.0=deterministic, 2.0=creative)",
    "top_p": "Nucleus sampling threshold (0.0-1.0)",
    "top_k": "Top-k sampling (higher=more diverse)",
    "max_output_tokens": "Maximum response length",
    "presence_penalty": "Penalizes repeated topics (-2.0 to 2.0)",
    "frequency_penalty": "Penalizes repeated tokens (-2.0 to 2.0)",
}

# Validation constraints for each parameter
_VALIDATION_RULES: dict[str, tuple[float | None, float | None, str]] = {
    # (min, max, error_template)
    # min/max are used for range validation; strictly positive params use None
    # and are handled specially in validate_generate_config()
    "temperature": (0.0, 2.0, "temperature must be 0.0-2.0, got {value}"),
    "top_p": (0.0, 1.0, "top_p must be 0.0-1.0, got {value}"),
    "top_k": (
        None,
        None,
        "top_k must be positive, got {value}",
    ),  # > 0, handled specially
    "max_output_tokens": (
        None,
        None,
        "max_output_tokens must be positive, got {value}",
    ),  # > 0
    "presence_penalty": (-2.0, 2.0, "presence_penalty must be -2.0-2.0, got {value}"),
    "frequency_penalty": (-2.0, 2.0, "frequency_penalty must be -2.0-2.0, got {value}"),
}


def serialize_generate_config(config: GenerateContentConfig | None) -> str:
    """Convert GenerateContentConfig to YAML string with parameter descriptions.

    Serializes only the evolvable parameters (temperature, top_p, top_k,
    max_output_tokens, presence_penalty, frequency_penalty) with YAML
    comments describing each parameter.

    Args:
        config: The GenerateContentConfig instance to serialize.
            Returns empty string if None.

    Returns:
        YAML string with parameter descriptions as comments.
        Empty string if config is None or has no evolvable parameters set.

    Examples:
        ```python
        config = GenerateContentConfig(temperature=0.7, top_p=0.9)
        yaml_text = serialize_generate_config(config)
        # yaml_text contains:
        # # temperature: Controls randomness (0.0=deterministic, 2.0=creative)
        # temperature: 0.7
        # # top_p: Nucleus sampling threshold (0.0-1.0)
        # top_p: 0.9
        ```

    Note:
        Output is parseable by yaml.safe_load() and includes only evolvable
        parameters that have non-None values.
    """
    if config is None:
        return ""

    # Extract evolvable parameters using model_dump if available (Pydantic v2)
    try:
        config_dict = config.model_dump(exclude_none=True)
    except AttributeError:
        # Fallback for non-Pydantic objects
        config_dict = {
            k: getattr(config, k, None)
            for k in EVOLVABLE_PARAMS
            if getattr(config, k, None) is not None
        }

    # Filter to only evolvable parameters with non-None values
    evolvable_dict = {
        k: v for k, v in config_dict.items() if k in EVOLVABLE_PARAMS and v is not None
    }

    if not evolvable_dict:
        return ""

    # Build YAML with comments
    lines = ["# LLM Generation Parameters"]
    for param, description in EVOLVABLE_PARAMS.items():
        if param in evolvable_dict:
            lines.append(f"# {param}: {description}")
            lines.append(f"{param}: {evolvable_dict[param]}")

    result = "\n".join(lines)
    logger.debug(
        "config_utils.serialize",
        param_count=len(evolvable_dict),
        params=list(evolvable_dict.keys()),
    )
    return result


def deserialize_generate_config(
    yaml_text: str,
    existing: GenerateContentConfig | None = None,
) -> GenerateContentConfig:
    """Parse YAML text into GenerateContentConfig, optionally merging with existing.

    Parses the YAML text and creates a new GenerateContentConfig. If an existing
    config is provided, unspecified parameters retain existing values (merge).

    Args:
        yaml_text: YAML string to parse. May be empty.
        existing: Optional existing config to merge with. If provided,
            unspecified parameters retain existing values.

    Returns:
        New GenerateContentConfig instance.

    Raises:
        ConfigValidationError: If yaml_text is malformed YAML.

    Examples:
        ```python
        # Parse standalone
        config = deserialize_generate_config("temperature: 0.5")
        assert config.temperature == 0.5

        # Merge with existing
        existing = GenerateContentConfig(temperature=0.7, top_p=0.9)
        merged = deserialize_generate_config("temperature: 0.5", existing)
        assert merged.temperature == 0.5
        assert merged.top_p == 0.9  # Preserved from existing
        ```

    Note:
        Does NOT validate parameter constraints - use validate_generate_config()
        separately. This allows inspection of invalid values before rejection.
    """
    # Handle empty input
    if not yaml_text or not yaml_text.strip():
        if existing is not None:
            return existing
        return GenerateContentConfig()

    # Parse YAML
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ConfigValidationError(
            f"Invalid YAML syntax: {e}",
            errors=[str(e)],
        ) from e

    # Handle non-dict YAML (e.g., scalar value)
    if not isinstance(parsed, dict):
        raise ConfigValidationError(
            f"Expected YAML dict, got {type(parsed).__name__}",
            errors=[f"YAML must be a mapping, got {type(parsed).__name__}"],
        )

    # Build merged config dict
    merged_dict: dict[str, Any] = {}

    # Start with existing values if provided
    if existing is not None:
        try:
            existing_dict = existing.model_dump(exclude_none=True)
        except AttributeError:
            existing_dict = {
                k: getattr(existing, k, None)
                for k in EVOLVABLE_PARAMS
                if getattr(existing, k, None) is not None
            }
        # Only include evolvable params from existing
        merged_dict = {k: v for k, v in existing_dict.items() if k in EVOLVABLE_PARAMS}

    # Override with parsed values (evolvable params only)
    for key, value in parsed.items():
        if key in EVOLVABLE_PARAMS:
            merged_dict[key] = value

    logger.debug(
        "config_utils.deserialize",
        param_count=len(merged_dict),
        params=list(merged_dict.keys()),
        had_existing=existing is not None,
    )

    return GenerateContentConfig(**merged_dict)


def validate_generate_config(config_dict: dict[str, Any]) -> list[str]:
    """Validate config dict against known parameter constraints.

    Checks each parameter value against its defined constraints:
    - temperature: 0.0 to 2.0
    - top_p: 0.0 to 1.0
    - top_k: > 0
    - max_output_tokens: > 0
    - presence_penalty: -2.0 to 2.0
    - frequency_penalty: -2.0 to 2.0

    Unknown parameters trigger a warning log but do NOT cause errors
    (they may be model-specific parameters).

    Args:
        config_dict: Dictionary of parameter name to value.

    Returns:
        List of validation error messages. Empty list means valid.

    Examples:
        ```python
        # Valid config
        errors = validate_generate_config({"temperature": 0.7, "top_p": 0.9})
        assert errors == []

        # Invalid config
        errors = validate_generate_config({"temperature": 3.0})
        assert len(errors) == 1
        assert "temperature" in errors[0]

        # Unknown param - no error, just warning
        errors = validate_generate_config({"unknown_param": 42})
        assert errors == []  # Warning logged, but no error
        ```

    Note:
        Only validates known evolvable parameters. Unknown parameters are
        logged as warnings but accepted (may be model-specific).
    """
    errors: list[str] = []

    for key, value in config_dict.items():
        if key not in EVOLVABLE_PARAMS:
            # Unknown parameter - log warning but don't reject
            logger.warning(
                "config_utils.validate.unknown_param",
                param=key,
                value=value,
            )
            continue

        # Skip None values
        if value is None:
            continue

        # Get validation rule
        rule = _VALIDATION_RULES.get(key)
        if rule is None:
            continue

        min_val, max_val, error_template = rule

        # Type check - must be numeric
        if not isinstance(value, (int, float)):
            errors.append(f"{key} must be a number, got {type(value).__name__}")
            continue

        # Range validation
        # For strictly positive params (top_k, max_output_tokens), check > 0 not >= 0
        if key in ("top_k", "max_output_tokens"):
            if value <= 0:
                errors.append(error_template.format(value=value))
        elif min_val is not None and value < min_val:
            errors.append(error_template.format(value=value))
        elif max_val is not None and value > max_val:
            errors.append(error_template.format(value=value))

    if errors:
        logger.debug(
            "config_utils.validate.failed",
            error_count=len(errors),
            errors=errors,
        )
    else:
        logger.debug(
            "config_utils.validate.success",
            param_count=len(config_dict),
        )

    return errors


__all__ = [
    "EVOLVABLE_PARAMS",
    "serialize_generate_config",
    "deserialize_generate_config",
    "validate_generate_config",
]
