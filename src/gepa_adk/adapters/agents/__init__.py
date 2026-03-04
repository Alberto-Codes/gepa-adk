"""Agent factory sub-package for ADK reflection agents.

Provides factory functions and a registry for creating component-aware
reflection agents. Each factory returns an ADK LlmAgent configured with
appropriate instructions and validation tools for a specific component type.

Attributes:
    create_text_reflection_agent (Callable): Factory for text reflection agents.
    create_schema_reflection_agent (Callable): Factory for schema reflection agents.
    create_config_reflection_agent (Callable): Factory for config reflection agents.
    get_reflection_agent (Callable): Auto-selects agent based on component name.
    component_registry (ComponentReflectionRegistry): Default global registry.

Examples:
    ```python
    from gepa_adk.adapters.agents import get_reflection_agent

    agent = get_reflection_agent("output_schema", "gemini-2.5-flash")
    ```

See Also:
    - [`reflection_agents`][gepa_adk.adapters.agents.reflection_agents]:
      Full module documentation.
"""

from gepa_adk.adapters.agents.reflection_agents import (
    ComponentReflectionRegistry,
    component_registry,
    create_config_reflection_agent,
    create_schema_reflection_agent,
    create_text_reflection_agent,
    get_reflection_agent,
)

__all__ = [
    "ComponentReflectionRegistry",
    "component_registry",
    "create_config_reflection_agent",
    "create_schema_reflection_agent",
    "create_text_reflection_agent",
    "get_reflection_agent",
]
