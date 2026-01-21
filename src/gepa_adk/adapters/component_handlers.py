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
    from ports/ and implements it in adapters/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from gepa_adk.domain.exceptions import SchemaValidationError
from gepa_adk.domain.types import COMPONENT_INSTRUCTION, COMPONENT_OUTPUT_SCHEMA
from gepa_adk.ports.component_handler import ComponentHandler
from gepa_adk.utils.schema_utils import deserialize_schema, serialize_pydantic_schema

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

__all__ = [
    "ComponentHandlerRegistry",
    "InstructionHandler",
    "OutputSchemaHandler",
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
        The default registry instance is available as `component_handlers`
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
            Replaces existing handler if name already registered.
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
            Returns False for empty/None names (no ValueError).
            This allows safe checking without exception handling.
        """
        if not name:
            return False
        return name in self._handlers


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
        Stateless handler - no instance attributes.
        All state is stored in the agent object.
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


class OutputSchemaHandler:
    """Handler for agent.output_schema component.

    Manages serialization, application, and restoration of the
    agent's output schema (Pydantic model) during evolution.

    Examples:
        ```python
        handler = OutputSchemaHandler()
        original_schema = handler.apply(agent, new_schema_text)
        # ... evaluate ...
        handler.restore(agent, original_schema)
        ```

    Note:
        Uses serialize_pydantic_schema and deserialize_schema utilities.
        On invalid schema text, keeps original and logs warning.
    """

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
            Never raises exceptions - graceful degradation.
        """
        original = getattr(agent, "output_schema", None)

        try:
            new_schema = deserialize_schema(value)
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
    """
    component_handlers.register(name, handler)


# =============================================================================
# Register Default Handlers
# =============================================================================

# Register built-in handlers for standard components
component_handlers.register(COMPONENT_INSTRUCTION, InstructionHandler())
component_handlers.register(COMPONENT_OUTPUT_SCHEMA, OutputSchemaHandler())
