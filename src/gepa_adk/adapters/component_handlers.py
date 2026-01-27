"""Component handler implementations and registry.

This module provides the ComponentHandlerRegistry for managing component
handlers, built-in handlers for instruction and output_schema, and
convenience functions for accessing the default registry.

Attributes:
    ComponentHandlerRegistry (class): Registry for component handlers.
    InstructionHandler (class): Handler for agent.instruction component.
    OutputSchemaHandler (class): Handler for agent.output_schema component.
    component_handlers (ComponentHandlerRegistry): Default registry instance.
    get_handler (function): Get handler from default registry.
    register_handler (function): Register handler in default registry.

Examples:
    Use built-in handlers:

    ```python
    from gepa_adk.adapters import get_handler

    handler = get_handler("instruction")
    original = handler.apply(agent, "New instruction")
    # ... evaluate ...
    handler.restore(agent, original)
    ```

    Register a custom handler:

    ```python
    from gepa_adk.adapters import register_handler


    class MyHandler:
        def serialize(self, agent):
            return str(agent.my_attr)

        def apply(self, agent, value):
            original = agent.my_attr
            agent.my_attr = value
            return original

        def restore(self, agent, original):
            agent.my_attr = original


    register_handler("my_component", MyHandler())
    ```

See Also:
    - [`gepa_adk.ports.component_handler`]: ComponentHandler protocol.
    - [`gepa_adk.adapters.adk_adapter`]: Usage in ADKAdapter._apply_candidate().

Note:
    This module follows hexagonal architecture - it imports the protocol
    from ports/ and implements concrete handlers in adapters/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from gepa_adk.domain.exceptions import ConfigValidationError, SchemaValidationError
from gepa_adk.domain.types import (
    COMPONENT_GENERATE_CONFIG,
    COMPONENT_INSTRUCTION,
    COMPONENT_MODEL,
    COMPONENT_OUTPUT_SCHEMA,
    ModelConstraints,
    SchemaConstraints,
)
from gepa_adk.ports.component_handler import ComponentHandler
from gepa_adk.utils.config_utils import (
    deserialize_generate_config,
    serialize_generate_config,
    validate_generate_config,
)
from gepa_adk.utils.schema_utils import (
    deserialize_schema,
    serialize_pydantic_schema,
    validate_schema_against_constraints,
)

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

__all__ = [
    "ComponentHandlerRegistry",
    "InstructionHandler",
    "OutputSchemaHandler",
    "GenerateContentConfigHandler",
    "ModelHandler",
    "component_handlers",
    "get_handler",
    "register_handler",
]

logger = structlog.get_logger(__name__)


class ComponentHandlerRegistry:
    """Registry for component handlers with O(1) lookup.

    Stores component handlers keyed by component name, providing
    registration, lookup, and existence checking operations.

    Attributes:
        _handlers: Internal dict mapping component names to handlers.

    Examples:
        Create and use a registry:

        ```python
        registry = ComponentHandlerRegistry()
        registry.register("instruction", InstructionHandler())
        handler = registry.get("instruction")
        ```

    See Also:
        - [`get_handler()`][gepa_adk.adapters.component_handlers.get_handler]:
            Convenience function for default registry.

    Note:
        A default registry instance is available as `component_handlers`
        module variable, with convenience functions `get_handler()` and
        `register_handler()`.
    """

    def __init__(self) -> None:
        """Initialize empty registry.

        Examples:
            ```python
            registry = ComponentHandlerRegistry()
            assert not registry.has("instruction")
            ```

        Note:
            Creates an empty internal dict for handler storage.
        """
        self._handlers: dict[str, ComponentHandler] = {}

    def register(self, name: str, handler: ComponentHandler) -> None:
        """Register a handler for a component name.

        Args:
            name: Component name (e.g., "instruction", "output_schema").
                Must be a non-empty string.
            handler: Handler implementing ComponentHandler protocol.

        Raises:
            ValueError: If name is empty or None.
            TypeError: If handler doesn't implement ComponentHandler protocol.

        Examples:
            ```python
            registry.register("instruction", InstructionHandler())
            registry.register("output_schema", OutputSchemaHandler())
            ```

        Note:
            Overwrites existing handler if name already registered.
            Logs a debug message on replacement.
        """
        if not name:
            raise ValueError("Component name must be a non-empty string")

        if not isinstance(handler, ComponentHandler):
            raise TypeError(
                f"Handler does not implement ComponentHandler protocol: {type(handler)}"
            )

        if name in self._handlers:
            logger.debug(
                "component_handler.register.replace",
                name=name,
                old_handler=type(self._handlers[name]).__name__,
                new_handler=type(handler).__name__,
            )

        self._handlers[name] = handler
        logger.debug(
            "component_handler.register.success",
            name=name,
            handler=type(handler).__name__,
        )

    def get(self, name: str) -> ComponentHandler:
        """Retrieve handler for component name.

        Args:
            name: Component name to look up.

        Returns:
            The registered ComponentHandler.

        Raises:
            ValueError: If name is empty or None.
            KeyError: If no handler registered for name.

        Examples:
            ```python
            handler = registry.get("instruction")
            original = handler.apply(agent, "New value")
            ```
        """
        if not name:
            raise ValueError("Component name must be a non-empty string")

        if name not in self._handlers:
            raise KeyError(f"No handler registered for component: {name}")

        return self._handlers[name]

    def has(self, name: str) -> bool:
        """Check if handler exists for component name.

        Args:
            name: Component name to check.

        Returns:
            True if handler registered, False otherwise.

        Examples:
            ```python
            if registry.has("instruction"):
                handler = registry.get("instruction")
            ```

        Note:
            Outputs False for empty/None names (no ValueError).
            This allows safe checking without exception handling.
        """
        if not name:
            return False
        return name in self._handlers

    def names(self) -> list[str]:
        """Return sorted list of registered handler names.

        Returns:
            Sorted list of component names with registered handlers.

        Examples:
            ```python
            available = registry.names()
            # ["generate_content_config", "instruction", "output_schema"]
            ```

        Note:
            Useful for error messages and validation feedback.
        """
        return sorted(self._handlers.keys())


class InstructionHandler:
    """Handler for agent.instruction component.

    Manages serialization, application, and restoration of the
    agent's instruction (system prompt) during evolution.

    Examples:
        ```python
        handler = InstructionHandler()
        original = handler.serialize(agent)  # "Be helpful"
        handler.apply(agent, "Be concise")
        # ... evaluate ...
        handler.restore(agent, original)  # Back to "Be helpful"
        ```

    Note:
        All state is stored in the agent object - handler is stateless.
        No instance attributes are maintained.
    """

    def serialize(self, agent: "LlmAgent") -> str:
        """Extract instruction from agent as string.

        Args:
            agent: The LlmAgent instance.

        Returns:
            The agent's instruction as string.
            Returns empty string if instruction is None.

        Examples:
            ```python
            text = handler.serialize(agent)
            # text == "You are a helpful assistant."
            ```
        """
        instruction = agent.instruction
        if instruction is None:
            return ""
        return str(instruction)

    def apply(self, agent: "LlmAgent", value: str) -> str:
        """Apply new instruction to agent, return original.

        Args:
            agent: The LlmAgent instance to modify.
            value: The new instruction string.

        Returns:
            The original instruction value.

        Examples:
            ```python
            original = handler.apply(agent, "New instruction")
            # agent.instruction is now "New instruction"
            ```
        """
        original = self.serialize(agent)
        agent.instruction = value
        logger.debug(
            "instruction_handler.apply",
            original_preview=original[:50] if original else "",
            new_preview=value[:50] if value else "",
        )
        return original

    def restore(self, agent: "LlmAgent", original: str) -> None:
        """Restore original instruction to agent.

        Args:
            agent: The LlmAgent instance to restore.
            original: The original instruction value.

        Examples:
            ```python
            handler.restore(agent, original)
            # agent.instruction is back to original
            ```
        """
        agent.instruction = original
        logger.debug(
            "instruction_handler.restore",
            instruction_preview=original[:50] if original else "",
        )


class GenerateContentConfigHandler:
    """Handler for agent.generate_content_config component.

    Manages serialization, application, and restoration of the
    agent's LLM generation configuration during evolution.

    Examples:
        ```python
        handler = GenerateContentConfigHandler()
        original = handler.serialize(agent)  # YAML string
        handler.apply(agent, "temperature: 0.5")
        # ... evaluate ...
        handler.restore(agent, original_config)
        ```

    Note:
        All state is stored in the agent object - handler is stateless.
        On invalid config, logs warning and keeps original.
    """

    def serialize(self, agent: "LlmAgent") -> str:
        """Extract generate_content_config from agent as YAML.

        Args:
            agent: The LlmAgent instance.

        Returns:
            YAML string with parameter descriptions as comments.
            Returns empty string if generate_content_config is None.

        Examples:
            ```python
            yaml_str = handler.serialize(agent)
            # yaml_str contains YAML with temperature, top_p, etc.
            ```
        """
        config = getattr(agent, "generate_content_config", None)
        return serialize_generate_config(config)

    def apply(self, agent: "LlmAgent", value: str) -> Any:
        """Apply new generate_content_config to agent, return original.

        Args:
            agent: The LlmAgent instance to modify.
            value: YAML string defining the new config parameters.

        Returns:
            The original GenerateContentConfig (or None).

        Examples:
            ```python
            original = handler.apply(agent, "temperature: 0.5")
            # agent.generate_content_config.temperature is now 0.5
            ```

        Note:
            If deserialization or validation fails, logs warning and
            keeps original config. Never raises exceptions.
        """
        original = getattr(agent, "generate_content_config", None)

        try:
            new_config = deserialize_generate_config(value, original)

            # Validate the parsed config
            config_dict = {}
            for param in [
                "temperature",
                "top_p",
                "top_k",
                "max_output_tokens",
                "presence_penalty",
                "frequency_penalty",
            ]:
                param_value = getattr(new_config, param, None)
                if param_value is not None:
                    config_dict[param] = param_value

            errors = validate_generate_config(config_dict)
            if errors:
                logger.warning(
                    "generate_content_config_handler.apply.validation_failed",
                    errors=errors,
                    config_preview=value[:100] if value else "",
                )
                # Keep original - don't modify agent
                return original

            agent.generate_content_config = new_config
            logger.debug(
                "generate_content_config_handler.apply",
                original_temp=getattr(original, "temperature", None)
                if original
                else None,
                new_temp=getattr(new_config, "temperature", None),
            )
        except ConfigValidationError as e:
            logger.warning(
                "generate_content_config_handler.apply.failed",
                error=str(e),
                config_preview=value[:100] if value else "",
            )
            # Keep original - don't modify agent

        return original

    def restore(self, agent: "LlmAgent", original: Any) -> None:
        """Restore original generate_content_config to agent.

        Args:
            agent: The LlmAgent instance to restore.
            original: The original GenerateContentConfig (or None).

        Examples:
            ```python
            handler.restore(agent, original_config)
            # agent.generate_content_config is back to original
            ```
        """
        agent.generate_content_config = original
        logger.debug(
            "generate_content_config_handler.restore",
            has_config=original is not None,
        )


class OutputSchemaHandler:
    """Handler for agent.output_schema component.

    Manages serialization, application, and restoration of the
    agent's output schema (Pydantic model) during evolution.

    Attributes:
        _constraints: Optional SchemaConstraints for field preservation.

    Examples:
        ```python
        handler = OutputSchemaHandler()
        handler.set_constraints(SchemaConstraints(required_fields=("score",)))
        original_schema = handler.apply(agent, new_schema_text)
        # ... evaluate ...
        handler.restore(agent, original_schema)
        ```

    Note:
        Applies serialize_pydantic_schema and deserialize_schema utilities.
        On invalid schema text, keeps original and logs warning.
        When constraints are set, validates proposed schemas before applying.
    """

    def __init__(self) -> None:
        """Initialize handler with no constraints.

        Examples:
            ```python
            handler = OutputSchemaHandler()
            assert handler._constraints is None
            ```
        """
        self._constraints: SchemaConstraints | None = None

    def set_constraints(self, constraints: SchemaConstraints | None) -> None:
        """Set schema constraints for field preservation.

        Args:
            constraints: SchemaConstraints specifying required fields and
                type preservation rules. Pass None to clear constraints.

        Examples:
            ```python
            handler.set_constraints(SchemaConstraints(required_fields=("score",)))
            handler.set_constraints(None)  # Clear constraints
            ```

        Note:
            Once set, constraints are checked during apply() - proposed schemas
            that violate constraints will be rejected and the original kept.
        """
        self._constraints = constraints
        logger.debug(
            "output_schema_handler.set_constraints",
            has_constraints=constraints is not None,
            required_fields=constraints.required_fields if constraints else None,
        )

    def serialize(self, agent: "LlmAgent") -> str:
        """Extract output schema from agent as Python source.

        Args:
            agent: The LlmAgent instance.

        Returns:
            Python source code defining the schema class.
            Returns empty string if output_schema is None.

        Examples:
            ```python
            schema_text = handler.serialize(agent)
            # schema_text contains Python class definition
            ```
        """
        output_schema = getattr(agent, "output_schema", None)
        if output_schema is None:
            return ""
        try:
            return serialize_pydantic_schema(output_schema)
        except (TypeError, OSError) as e:
            logger.warning(
                "output_schema_handler.serialize.failed",
                error=str(e),
                schema_type=type(output_schema).__name__,
            )
            return ""

    def apply(self, agent: "LlmAgent", value: str) -> Any:
        """Apply new output schema to agent, return original.

        Args:
            agent: The LlmAgent instance to modify.
            value: Python source code defining the new schema.

        Returns:
            The original output_schema (class or None).

        Examples:
            ```python
            original = handler.apply(
                agent,
                '''
            class NewSchema(BaseModel):
                result: str
            ''',
            )
            ```

        Note:
            If deserialization fails, logs warning and keeps original.
            If constraints are set and violated, keeps original.
            Never raises exceptions - graceful degradation.
        """
        original = getattr(agent, "output_schema", None)

        try:
            new_schema = deserialize_schema(value)

            # Validate against constraints if set
            if self._constraints is not None:
                is_valid, violations = validate_schema_against_constraints(
                    new_schema, original, self._constraints
                )
                if not is_valid:
                    logger.warning(
                        "output_schema_handler.apply.constraint_violation",
                        violations=violations,
                        schema_preview=value[:100] if value else "",
                    )
                    # Keep original - constraint violation
                    return original

            agent.output_schema = new_schema
            logger.debug(
                "output_schema_handler.apply",
                original_name=original.__name__ if original else None,
                new_name=new_schema.__name__,
            )
        except SchemaValidationError as e:
            logger.warning(
                "output_schema_handler.apply.failed",
                error=str(e),
                schema_preview=value[:100] if value else "",
            )
            # Keep original - don't modify agent

        return original

    def restore(self, agent: "LlmAgent", original: Any) -> None:
        """Restore original output schema to agent.

        Args:
            agent: The LlmAgent instance to restore.
            original: The original output_schema (class or None).

        Examples:
            ```python
            handler.restore(agent, original_schema)
            # agent.output_schema is back to original
            ```
        """
        agent.output_schema = original
        logger.debug(
            "output_schema_handler.restore",
            schema_name=original.__name__ if original else None,
        )


class ModelHandler:
    """Handler for agent.model component.

    Manages serialization, application, and restoration of the agent's
    model during evolution. Supports both string models and wrapped
    model objects (e.g., LiteLlm), preserving wrapper configuration.

    Attributes:
        _constraints: Optional ModelConstraints for allowed model validation.

    Examples:
        Basic usage with string model:

        ```python
        handler = ModelHandler()
        original = handler.apply(agent, "gpt-4o")
        # ... evaluate ...
        handler.restore(agent, original)
        ```

        With constraints:

        ```python
        handler = ModelHandler()
        handler.set_constraints(
            ModelConstraints(
                allowed_models=("gemini-2.0-flash", "gpt-4o"),
            )
        )
        handler.apply(agent, "gpt-4o")  # Accepted
        handler.apply(agent, "invalid")  # Rejected, returns None
        ```

    Note:
        Applies duck-typing to detect wrapped models. Any object with
        a `.model` attribute that is a string is treated as a wrapper.
        On constraint violation, logs warning and preserves original.
    """

    def __init__(self) -> None:
        """Initialize handler with no constraints.

        Examples:
            ```python
            handler = ModelHandler()
            assert handler._constraints is None
            ```
        """
        self._constraints: ModelConstraints | None = None

    def set_constraints(self, constraints: ModelConstraints | None) -> None:
        """Set model constraints for allowed model validation.

        Args:
            constraints: ModelConstraints specifying allowed model names.
                Pass None to clear constraints (accept any model).

        Examples:
            ```python
            handler.set_constraints(
                ModelConstraints(
                    allowed_models=("gemini-2.0-flash", "gpt-4o"),
                )
            )
            handler.set_constraints(None)  # Clear constraints
            ```

        Note:
            Once set, constraints are checked during apply() - proposed
            models not in the allowed list will be rejected.
        """
        self._constraints = constraints
        logger.debug(
            "model_handler.set_constraints",
            has_constraints=constraints is not None,
            allowed_models=constraints.allowed_models if constraints else None,
        )

    def serialize(self, agent: "LlmAgent") -> str:
        """Extract model name from agent as string.

        Supports both string models and wrapped model objects by
        duck-typing on the `.model` attribute.

        Args:
            agent: The LlmAgent instance.

        Returns:
            The model name as string. Returns empty string if model
            is None or empty.

        Examples:
            String model:

            ```python
            agent = LlmAgent(model="gemini-2.0-flash", ...)
            handler.serialize(agent)  # "gemini-2.0-flash"
            ```

            Wrapped model:

            ```python
            agent = LlmAgent(model=LiteLlm(model="ollama/llama3"), ...)
            handler.serialize(agent)  # "ollama/llama3"
            ```

        Note:
            Order of detection: first checks for wrapper with .model
            attribute, then falls back to direct string conversion.
        """
        model = agent.model
        if model is None:
            return ""

        # Duck-type: if object has .model attribute that is a string, use it
        if hasattr(model, "model") and isinstance(model.model, str):
            return model.model

        # Otherwise treat as string
        return str(model) if model else ""

    def apply(self, agent: "LlmAgent", value: str) -> tuple[str, str] | None:
        """Apply new model to agent, return restore info.

        For string models, replaces agent.model directly.
        For wrapped models, mutates wrapper.model in-place to
        preserve wrapper configuration (headers, auth, etc.).

        Args:
            agent: The LlmAgent instance to modify.
            value: The new model name string.

        Returns:
            Tuple of (model_type, original_name) for restore, where
            model_type is "string" or "wrapper". Returns None if
            constraints reject the model (no change made).

        Examples:
            String model:

            ```python
            original = handler.apply(agent, "gpt-4o")
            # original == ("string", "gemini-2.0-flash")
            ```

            Wrapped model (preserves config):

            ```python
            original = handler.apply(agent, "ollama/mistral")
            # original == ("wrapper", "ollama/llama3")
            # agent.model._additional_args preserved
            ```

        Note:
            On constraint violation, logs warning and returns None.
            Caller should check return value before proceeding.
        """
        # Validate against constraints if set
        if self._constraints is not None:
            if value not in self._constraints.allowed_models:
                logger.warning(
                    "model_handler.apply.constraint_violation",
                    proposed_model=value,
                    allowed_models=self._constraints.allowed_models,
                )
                return None

        model = agent.model

        # Duck-type: if object has .model attribute that is a string, mutate in-place
        if hasattr(model, "model") and isinstance(model.model, str):
            original_name = model.model
            model.model = value  # type: ignore[union-attr]
            logger.debug(
                "model_handler.apply",
                model_type="wrapper",
                original=original_name,
                new=value,
            )
            return ("wrapper", original_name)

        # String model: replace directly
        original_name = str(model) if model else ""
        agent.model = value
        logger.debug(
            "model_handler.apply",
            model_type="string",
            original=original_name,
            new=value,
        )
        return ("string", original_name)

    def restore(self, agent: "LlmAgent", original: tuple[str, str] | None) -> None:
        """Restore original model to agent.

        Args:
            agent: The LlmAgent instance to restore.
            original: The restore info from apply(), or None if no
                change was made (constraint violation).

        Examples:
            ```python
            original = handler.apply(agent, "gpt-4o")
            # ... evaluate ...
            handler.restore(agent, original)
            # agent.model is back to original
            ```

        Note:
            Supports both string and wrapper model types based on
            the restore info tuple.
        """
        if original is None:
            # No change was made (constraint violation), nothing to restore
            return

        model_type, original_name = original

        if model_type == "wrapper":
            # Restore wrapper's model attribute
            model = agent.model
            if hasattr(model, "model"):
                model.model = original_name  # type: ignore[union-attr]
                logger.debug(
                    "model_handler.restore",
                    model_type="wrapper",
                    restored=original_name,
                )
        else:
            # Restore string model
            agent.model = original_name
            logger.debug(
                "model_handler.restore",
                model_type="string",
                restored=original_name,
            )


# =============================================================================
# Default Registry Instance and Convenience Functions
# =============================================================================

#: Default registry instance for global handler access
component_handlers = ComponentHandlerRegistry()


def get_handler(name: str) -> ComponentHandler:
    """Get handler from default registry.

    Args:
        name: Component name to look up.

    Returns:
        The registered ComponentHandler.

    Raises:
        ValueError: If name is empty or None.
        KeyError: If no handler registered for name.

    Examples:
        ```python
        handler = get_handler("instruction")
        original = handler.apply(agent, "New instruction")
        ```

    See Also:
        - [`ComponentHandlerRegistry.get()`]: Underlying registry method.

    Note:
        Shortcut for component_handlers.get(name).
    """
    return component_handlers.get(name)


def register_handler(name: str, handler: ComponentHandler) -> None:
    """Register handler in default registry.

    Args:
        name: Component name to register.
        handler: Handler implementing ComponentHandler protocol.

    Raises:
        ValueError: If name is empty or None.
        TypeError: If handler doesn't implement ComponentHandler protocol.

    Examples:
        ```python
        register_handler("my_component", MyHandler())
        handler = get_handler("my_component")
        ```

    See Also:
        - [`ComponentHandlerRegistry.register()`]: Underlying registry method.

    Note:
        Shortcut for component_handlers.register(name, handler).
    """
    component_handlers.register(name, handler)


# =============================================================================
# Register Default Handlers
# =============================================================================

# Register built-in handlers for standard components
component_handlers.register(COMPONENT_INSTRUCTION, InstructionHandler())
component_handlers.register(COMPONENT_OUTPUT_SCHEMA, OutputSchemaHandler())
component_handlers.register(COMPONENT_GENERATE_CONFIG, GenerateContentConfigHandler())
component_handlers.register(COMPONENT_MODEL, ModelHandler())
