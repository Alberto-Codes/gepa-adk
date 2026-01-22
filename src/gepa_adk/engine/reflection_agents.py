"""Component-aware reflection agent factories and registry.

This module provides factory functions that create reflection agents configured
for specific component types. Each factory returns an ADK LlmAgent with appropriate
instructions and validation tools.

The component registry enables automatic selection of the right reflection agent
based on the component name being evolved, with support for custom validators.

Attributes:
    SCHEMA_REFLECTION_INSTRUCTION (str): Instruction template for schema
        reflection agents with validation guidance.
    ComponentReflectionRegistry (type): Registry class for mapping component
        names to reflection agent factories.
    create_schema_reflection_agent (Callable): Factory function that creates
        schema reflection agents with validation tools.
    create_text_reflection_agent (Callable): Factory function that creates
        text reflection agents without tools.
    get_reflection_agent (Callable): Convenience function for auto-selecting
        reflection agents based on component name.
    component_registry (ComponentReflectionRegistry): Default global registry
        instance with built-in component mappings.

Examples:
    Create a schema reflection agent:

    ```python
    from gepa_adk.engine.reflection_agents import create_schema_reflection_agent

    agent = create_schema_reflection_agent(model="gemini-2.0-flash")
    # Agent has validate_output_schema tool and schema-focused instruction
    ```

    Auto-select agent based on component name:

    ```python
    from gepa_adk.engine.reflection_agents import get_reflection_agent

    # Returns schema agent with validation tool
    agent = get_reflection_agent("output_schema", "gemini-2.0-flash")

    # Returns text agent without tools
    agent = get_reflection_agent("instruction", "gemini-2.0-flash")
    ```

    Register custom validator:

    ```python
    from gepa_adk.engine.reflection_agents import component_registry


    def my_custom_factory(model: str):
        return LlmAgent(name="custom", model=model, tools=[...])


    component_registry.register("my_component", my_custom_factory)
    ```

See Also:
    - [`create_adk_reflection_fn`][gepa_adk.engine.adk_reflection.create_adk_reflection_fn]:
      Creates reflection callable.
    - [`validate_output_schema`][gepa_adk.utils.schema_tools.validate_output_schema]:
      Schema validation tool.
"""

__all__ = [
    "SCHEMA_REFLECTION_INSTRUCTION",
    "CONFIG_REFLECTION_INSTRUCTION",
    "ComponentReflectionRegistry",
    "create_schema_reflection_agent",
    "create_config_reflection_agent",
    "create_text_reflection_agent",
    "get_reflection_agent",
    "component_registry",
]

from typing import Callable

import structlog
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from gepa_adk.domain.types import COMPONENT_GENERATE_CONFIG, COMPONENT_OUTPUT_SCHEMA
from gepa_adk.engine.adk_reflection import REFLECTION_INSTRUCTION
from gepa_adk.utils.schema_tools import validate_output_schema

logger = structlog.get_logger(__name__)

# Type alias for reflection agent factory functions
ReflectionAgentFactory = Callable[[str], LlmAgent]
"""Factory function type that creates a reflection agent.

A factory function takes a model name string and returns a configured LlmAgent
with appropriate instruction and tools for reflection.

Example:
    ```python
    def my_factory(model: str) -> LlmAgent:
        return LlmAgent(name="reflector", model=model, ...)
    ```
"""

# Schema-specific reflection instruction
SCHEMA_REFLECTION_INSTRUCTION = """## Component Text to Improve
{component_text}

## Trials
{trials}

## Instructions
Propose an improved version of the Pydantic schema based on the trials above.

IMPORTANT: Before returning your final answer, you MUST use the validate_output_schema
tool to verify your proposed schema is syntactically valid. If validation fails, fix
the errors and validate again until the schema is valid.

Return ONLY the improved Pydantic class definition (starting with "class"), nothing else.
Do not wrap in markdown code fences."""
"""Reflection instruction for output_schema components.

This instruction explicitly guides the LLM to use the validation tool before
returning, enabling self-correction of syntax errors. Follows ADK's pattern
for tool-guided structured output (similar to SetModelResponseTool).

The instruction uses ADK template placeholders (`{component_text}`, `{trials}`)
for session state substitution.
"""

# Config-specific reflection instruction
CONFIG_REFLECTION_INSTRUCTION = """## Current LLM Generation Config (YAML)
{component_text}

## Trials
{trials}

## Instructions
Propose improved LLM generation configuration parameters based on the trial results above.

### Parameter Guidelines

| Parameter | Range | When to Adjust |
|-----------|-------|----------------|
| `temperature` | 0.0 - 2.0 | Lower (0.0-0.3) for deterministic, higher (0.7-1.5) for creative |
| `top_p` | 0.0 - 1.0 | Lower (0.5-0.8) for focused, higher (0.9-1.0) for diverse output |
| `top_k` | > 0 | Lower (10-30) constrains vocab, higher (50-100) allows diversity |
| `max_output_tokens` | > 0 | Adjust based on expected response length |
| `presence_penalty` | -2.0 - 2.0 | Positive values discourage repeated topics |
| `frequency_penalty` | -2.0 - 2.0 | Positive values discourage repeated tokens |

### Analysis Steps
1. Review trial scores and identify patterns (high-scoring configs vs low-scoring)
2. Consider the task type (creative, analytical, conversational)
3. Propose incremental adjustments to promising parameters
4. Keep parameters within valid ranges

Return ONLY valid YAML configuration (parameter: value pairs), nothing else.
Do not wrap in markdown code fences."""
"""Reflection instruction for generate_content_config components.

This instruction guides the LLM to analyze trial results and propose optimal
generation parameters. It includes parameter descriptions and valid ranges
to help the reflection agent make informed decisions.

The instruction uses ADK template placeholders (`{component_text}`, `{trials}`)
for session state substitution.
"""


def create_text_reflection_agent(model: str) -> LlmAgent:
    """Create a reflection agent for text components.

    Creates an LlmAgent configured for free-form text reflection with no
    validation tools. Suitable for instructions, descriptions, and other
    text components that don't require structured validation.

    Args:
        model: Model name/identifier (e.g., "gemini-2.0-flash").

    Returns:
        Configured LlmAgent with text reflection instruction and no tools.

    Examples:
        Create agent for instruction reflection:

        ```python
        from gepa_adk.engine.reflection_agents import create_text_reflection_agent

        agent = create_text_reflection_agent(model="gemini-2.0-flash")

        # Agent has:
        # - name="text_reflector"
        # - instruction with {component_text} and {trials} placeholders
        # - output_key="proposed_component_text"
        # - No tools
        ```

    See Also:
        - [`REFLECTION_INSTRUCTION`][gepa_adk.engine.adk_reflection.REFLECTION_INSTRUCTION]:
          Default instruction template.
    """
    logger.debug(
        "reflection_agent.create",
        agent_type="text",
        model=model,
    )

    return LlmAgent(
        name="text_reflector",
        model=model,
        instruction=REFLECTION_INSTRUCTION,
        output_key="proposed_component_text",
    )


def create_schema_reflection_agent(model: str) -> LlmAgent:
    """Create a reflection agent for output_schema components.

    Creates an LlmAgent configured with:
    - Schema-focused reflection instruction
    - validate_output_schema tool for self-validation
    - Explicit instruction to use validation tool before returning

    This agent can validate proposed Pydantic schemas before returning them,
    reducing wasted evolution iterations on invalid syntax.

    Args:
        model: Model name/identifier (e.g., "gemini-2.0-flash").

    Returns:
        Configured LlmAgent with schema validation tool.

    Examples:
        Create agent for schema reflection:

        ```python
        from gepa_adk.engine.reflection_agents import create_schema_reflection_agent

        agent = create_schema_reflection_agent(model="gemini-2.0-flash")

        # Agent has:
        # - name="schema_reflector"
        # - tools=[FunctionTool(validate_output_schema)]
        # - instruction with validation guidance
        # - output_key="proposed_component_text"
        ```

    See Also:
        - [`SCHEMA_REFLECTION_INSTRUCTION`]:
          Schema instruction template.
        - [`validate_output_schema`]:
          Validation tool function.

    Note:
        The agent uses `output_key` for text output extraction, not `output_schema`.
        This avoids ADK's limitation where tools and output_schema cannot be used
        together. The agent returns plain text (the Pydantic class definition).
    """
    logger.debug(
        "reflection_agent.create",
        agent_type="schema",
        model=model,
    )

    return LlmAgent(
        name="schema_reflector",
        model=model,
        instruction=SCHEMA_REFLECTION_INSTRUCTION,
        tools=[FunctionTool(validate_output_schema)],
        output_key="proposed_component_text",
    )


def create_config_reflection_agent(model: str) -> LlmAgent:
    """Create a reflection agent for generate_content_config components.

    Creates an LlmAgent configured for LLM generation configuration reflection.
    The agent receives parameter guidelines and valid ranges to help propose
    optimal configurations based on trial results.

    Args:
        model: Model name/identifier (e.g., "gemini-2.0-flash").

    Returns:
        Configured LlmAgent with config reflection instruction.

    Examples:
        Create agent for config reflection:

        ```python
        from gepa_adk.engine.reflection_agents import create_config_reflection_agent

        agent = create_config_reflection_agent(model="gemini-2.0-flash")

        # Agent has:
        # - name="config_reflector"
        # - instruction with parameter guidelines
        # - output_key="proposed_component_text"
        # - No tools (validation happens in handler)
        ```

    See Also:
        - [`CONFIG_REFLECTION_INSTRUCTION`]:
          Config instruction template.

    Note:
        The agent does not use validation tools because config validation
        is built into the GenerateContentConfigHandler.apply() method.
        Invalid configs are gracefully rejected there.
    """
    logger.debug(
        "reflection_agent.create",
        agent_type="config",
        model=model,
    )

    return LlmAgent(
        name="config_reflector",
        model=model,
        instruction=CONFIG_REFLECTION_INSTRUCTION,
        output_key="proposed_component_text",
    )


class ComponentReflectionRegistry:
    """Registry mapping component names to reflection agent factories.

    Enables automatic selection of the appropriate reflection agent based on
    component type, with support for custom validator registration.

    The registry uses exact string matching for component names. Unknown components
    fall back to the default text reflection agent.

    Examples:
        Register custom factory:

        ```python
        from gepa_adk.engine.reflection_agents import ComponentReflectionRegistry
        from google.adk.agents import LlmAgent

        registry = ComponentReflectionRegistry()


        def custom_factory(model: str) -> LlmAgent:
            return LlmAgent(
                name="custom_reflector",
                model=model,
                instruction="Custom: {component_text}",
            )


        registry.register("my_component", custom_factory)
        agent = registry.get_agent("my_component", "gemini-2.0-flash")
        ```

    See Also:
        - [`get_reflection_agent`]: Convenience function using default registry.
    """

    def __init__(self) -> None:
        """Initialize empty registry with default text factory."""
        self._factories: dict[str, ReflectionAgentFactory] = {}
        self._default_factory: ReflectionAgentFactory = create_text_reflection_agent

    def register(
        self,
        component_name: str,
        factory: ReflectionAgentFactory,
    ) -> None:
        """Register a factory for a component name.

        Args:
            component_name: Component name to register (e.g., "output_schema").
                Uses exact match - no pattern matching for MVP.
            factory: Factory function that takes model name and returns LlmAgent.

        Examples:
            Register schema factory:

            ```python
            registry.register("output_schema", create_schema_reflection_agent)
            ```
        """
        logger.info(
            "reflection_registry.register",
            component_name=component_name,
            factory=getattr(factory, "__name__", str(factory)),
        )
        self._factories[component_name] = factory

    def get_factory(self, component_name: str) -> ReflectionAgentFactory:
        """Get factory for a component name.

        Args:
            component_name: Component name to look up.

        Returns:
            Registered factory if found, otherwise default text factory.

        Examples:
            Get factory:

            ```python
            factory = registry.get_factory("output_schema")
            agent = factory("gemini-2.0-flash")
            ```
        """
        factory = self._factories.get(component_name, self._default_factory)

        logger.debug(
            "reflection_registry.get_factory",
            component_name=component_name,
            factory=getattr(factory, "__name__", str(factory)),
            is_default=factory == self._default_factory,
        )

        return factory

    def get_agent(self, component_name: str, model: str) -> LlmAgent:
        """Create a reflection agent for a component.

        Convenience method that gets the factory and invokes it.

        Args:
            component_name: Component name.
            model: Model name/identifier.

        Returns:
            Configured LlmAgent for the component type.

        Examples:
            Get agent directly:

            ```python
            agent = registry.get_agent("output_schema", "gemini-2.0-flash")
            ```
        """
        factory = self.get_factory(component_name)
        return factory(model)


# Global default registry instance
component_registry = ComponentReflectionRegistry()
"""Default component reflection registry.

Pre-configured with:
- `output_schema` → `create_schema_reflection_agent`
- `generate_content_config` → `create_config_reflection_agent`
- Default fallback → `create_text_reflection_agent`

Use this registry or create your own for custom configuration.
"""

# Register built-in factories
component_registry.register(COMPONENT_OUTPUT_SCHEMA, create_schema_reflection_agent)
component_registry.register(COMPONENT_GENERATE_CONFIG, create_config_reflection_agent)


def get_reflection_agent(component_name: str, model: str) -> LlmAgent:
    """Get appropriate reflection agent for a component.

    Convenience function that uses the global registry to create an agent
    based on component name. Falls back to text reflection for unknown components.

    Args:
        component_name: Component being evolved (e.g., "output_schema").
        model: Model name/identifier.

    Returns:
        Configured LlmAgent for the component type.

    Examples:
        Auto-select agent:

        ```python
        from gepa_adk.engine.reflection_agents import get_reflection_agent

        # Returns schema agent with validation tool
        schema_agent = get_reflection_agent("output_schema", "gemini-2.0-flash")

        # Returns text agent without tools
        text_agent = get_reflection_agent("instruction", "gemini-2.0-flash")

        # Unknown components get text agent (fallback)
        fallback_agent = get_reflection_agent("custom", "gemini-2.0-flash")
        ```

    See Also:
        - [`component_registry`]: Default registry.
    """
    return component_registry.get_agent(component_name, model)
