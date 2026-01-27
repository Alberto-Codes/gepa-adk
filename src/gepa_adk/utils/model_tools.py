"""ADK tool wrappers for model selection validation.

This module provides ADK-compatible tool functions for validating model
choices during model evolution. The tools return dict results compatible
with ADK's FunctionTool pattern, enabling LLM agents to validate their
model selection before returning.

Attributes:
    create_validate_model_choice (Callable): Factory function that creates
        a validation tool with allowed_models baked in. Returns a function
        suitable for use with ADK's FunctionTool.

Examples:
    Use validate_model_choice as an ADK tool:

    ```python
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from gepa_adk.utils.model_tools import create_validate_model_choice

    validate_fn = create_validate_model_choice(
        allowed_models=("gpt-4o", "claude-3-sonnet", "gemini-2.5-flash")
    )

    agent = LlmAgent(
        name="model_reflector",
        model="gemini-2.5-flash",
        instruction="Select a model. Validate before returning.",
        tools=[FunctionTool(validate_fn)],
    )
    ```

See Also:
    - [`gepa_adk.engine.reflection_agents`]: Reflection agent factories.
    - [`gepa_adk.utils.schema_tools`]: Similar pattern for schema validation.

Note:
    This module follows the TACOS acrostic pattern for source files.
"""

__all__ = ["create_validate_model_choice"]

from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


def create_validate_model_choice(
    allowed_models: tuple[str, ...],
) -> Callable[[str], dict[str, Any]]:
    """Create a model validation tool with allowed_models baked in.

    Factory function that returns a validation tool function suitable for
    use with ADK's FunctionTool. The returned function validates model
    choices against the allowed list.

    Args:
        allowed_models: Tuple of valid model name strings.

    Returns:
        A validation function that takes a model_name and returns a dict
        with validation results.

    Examples:
        Create and use validation tool:

        ```python
        from gepa_adk.utils.model_tools import create_validate_model_choice

        validate_fn = create_validate_model_choice(
            allowed_models=("gpt-4o", "gemini-2.5-flash")
        )

        # Valid model
        result = validate_fn("gpt-4o")
        # {"valid": True, "model_name": "gpt-4o"}

        # Invalid model
        result = validate_fn("invalid-model")
        # {"valid": False, "error": "...", "allowed_models": [...]}
        ```

    Note:
        The returned function has a descriptive docstring that helps LLMs
        understand how to use it correctly.
    """

    def validate_model_choice(model_name: str) -> dict[str, Any]:
        """Validate a model choice against the allowed models list.

        Call this tool to check if your selected model is valid before
        returning it. If invalid, the response will show the allowed
        models so you can select a valid one.

        Args:
            model_name: The exact model name string to validate.

        Returns:
            dict with validation result:
            - If valid: {"valid": True, "model_name": str}
            - If invalid: {"valid": False, "error": str, "allowed_models": list}
        """
        # Strip whitespace that might be included
        model_name = model_name.strip()

        logger.debug(
            "model_tools.validate",
            model_name=model_name,
            allowed_count=len(allowed_models),
        )

        if model_name in allowed_models:
            logger.debug(
                "model_tools.validate.valid",
                model_name=model_name,
            )
            return {
                "valid": True,
                "model_name": model_name,
            }
        else:
            logger.debug(
                "model_tools.validate.invalid",
                model_name=model_name,
                allowed_models=allowed_models,
            )
            return {
                "valid": False,
                "error": f"'{model_name}' is not in the allowed models list.",
                "allowed_models": list(allowed_models),
            }

    return validate_model_choice
