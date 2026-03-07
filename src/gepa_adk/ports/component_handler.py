"""Protocol definition for component handlers.

This module defines the ComponentHandler protocol for serializing, applying,
and restoring agent components during evolution. Each handler manages one
component type (e.g., instruction, output_schema).

Attributes:
    ComponentHandler (protocol): Protocol for component serialization/application.

Examples:
    Check if a handler implements the protocol:

    ```python
    from gepa_adk.ports.component_handler import ComponentHandler


    class MyHandler:
        def serialize(self, agent):
            return str(agent.my_component)

        def apply(self, agent, value):
            original = agent.my_component
            agent.my_component = value
            return original

        def restore(self, agent, original):
            agent.my_component = original


    handler = MyHandler()
    assert isinstance(handler, ComponentHandler)
    ```

See Also:
    - [`component_handlers`][gepa_adk.adapters.components.component_handlers]:
        Built-in handler implementations.
    - [`adk_adapter`][gepa_adk.adapters.evolution.adk_adapter]:
        Usage in ADKAdapter._apply_candidate().

Note:
    This protocol follows the hexagonal architecture pattern - it is defined
    in ports/ with no external dependencies. Implementations go in adapters/
    to maintain clean layer separation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent

__all__ = ["ComponentHandler"]


@runtime_checkable
class ComponentHandler(Protocol):
    """Protocol for component serialization and application.

    Handles the serialize/apply/restore cycle for one component type during
    evolution. Implementations must be stateless and thread-safe.

    The protocol defines three operations:
    1. **serialize**: Extract current component value as string
    2. **apply**: Set new value, return original for restoration
    3. **restore**: Reinstate original value after evaluation

    Examples:
        Implement a custom handler:

        ```python
        class TemperatureHandler:
            def serialize(self, agent: LlmAgent) -> str:
                config = getattr(agent, "generate_content_config", None)
                if config and hasattr(config, "temperature"):
                    return str(config.temperature)
                return "1.0"

            def apply(self, agent: LlmAgent, value: str) -> Any:
                config = getattr(agent, "generate_content_config", None)
                original = config.temperature if config else 1.0
                if config:
                    config.temperature = float(value)
                return original

            def restore(self, agent: LlmAgent, original: Any) -> None:
                config = getattr(agent, "generate_content_config", None)
                if config:
                    config.temperature = original
        ```

    See Also:
        - [`InstructionHandler`]\
[gepa_adk.adapters.components.component_handlers.InstructionHandler]:
            Handler for agent instruction.
        - [`OutputSchemaHandler`]\
[gepa_adk.adapters.components.component_handlers.OutputSchemaHandler]:
            Handler for agent output schema.

    Note:
        All methods are synchronous - no I/O operations should be performed.
        Apply() should log warnings and keep the original value rather than
        raising exceptions on invalid inputs for error safety.
    """

    def serialize(self, agent: "LlmAgent") -> str:
        """Extract component value from agent as string for evolution.

        Args:
            agent: The LlmAgent instance to extract component from.

        Returns:
            String representation of the component value.
            Returns empty string if component is not set.

        Examples:
            ```python
            handler = InstructionHandler()
            text = handler.serialize(agent)
            # text == "You are a helpful assistant."
            ```

        Note:
            Operations must never raise exceptions for missing values.
            Return empty string or sensible default instead.
        """
        ...

    def apply(self, agent: "LlmAgent", value: str) -> Any:
        """Apply evolved value to agent, return original for restore.

        Args:
            agent: The LlmAgent instance to modify.
            value: The new component value as string.

        Returns:
            The original component value (type depends on component).
            This value will be passed to restore() later.

        Examples:
            ```python
            handler = InstructionHandler()
            original = handler.apply(agent, "New instruction")
            # agent.instruction is now "New instruction"
            # original contains previous instruction value
            ```

        Note:
            On application failure (e.g., invalid schema), log warning
            and return original without modifying agent. Never raise
            exceptions - graceful degradation is required.
        """
        ...

    def restore(self, agent: "LlmAgent", original: Any) -> None:
        """Restore original value after evaluation.

        Args:
            agent: The LlmAgent instance to restore.
            original: The original value returned by apply().

        Examples:
            ```python
            handler = InstructionHandler()
            original = handler.apply(agent, "Temp instruction")
            # ... run evaluation ...
            handler.restore(agent, original)
            # agent.instruction is back to original value
            ```

        Note:
            Original value restoration always succeeds - never raises exceptions.
            None values reset to component default.
        """
        ...
