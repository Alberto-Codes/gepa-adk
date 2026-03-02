"""Evolvable surface handlers for component mutation.

Currently contains the ComponentHandlerRegistry and built-in handlers for
instruction, output_schema, and generate_content_config components.

Anticipated growth: custom handler registration, handler composition,
component validation middleware.

Attributes:
    ComponentHandlerRegistry: Registry for component handlers.
    InstructionHandler: Handler for agent.instruction component.
    OutputSchemaHandler: Handler for agent.output_schema component.
    GenerateContentConfigHandler: Handler for LLM generation config.
    component_handlers: Default registry instance.
    get_handler: Convenience function for getting handlers.
    register_handler: Convenience function for registering handlers.

Examples:
    Retrieve a handler for a specific component:

    ```python
    from gepa_adk.adapters.components import get_handler

    handler = get_handler("instruction")
    ```

    Register a custom handler:

    ```python
    from gepa_adk.adapters.components import register_handler

    register_handler("my_component", MyCustomHandler())
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.ports.component_handler`][gepa_adk.ports.component_handler]: ComponentHandler
        protocol that handlers implement.
    - [`gepa_adk.adapters.evolution`][gepa_adk.adapters.evolution]: Adapters that use component
        handlers during evolution.

Note:
    This package centralizes component handler registration for evolution surfaces.
"""

from gepa_adk.adapters.components.component_handlers import (
    ComponentHandlerRegistry,
    GenerateContentConfigHandler,
    InstructionHandler,
    OutputSchemaHandler,
    component_handlers,
    get_handler,
    register_handler,
)

__all__ = [
    "ComponentHandlerRegistry",
    "InstructionHandler",
    "OutputSchemaHandler",
    "GenerateContentConfigHandler",
    "component_handlers",
    "get_handler",
    "register_handler",
]
