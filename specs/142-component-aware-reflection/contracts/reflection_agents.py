"""API contracts for component-aware reflection agents.

This file defines the public interface contracts for the reflection agent
factories and registry. It serves as a reference for implementation and
testing.

Feature: 142-component-aware-reflection
"""

from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

# =============================================================================
# Type Aliases
# =============================================================================

# Factory type: takes model name, returns configured agent
# Note: LlmAgent is from google.adk.agents, not imported here to avoid
# coupling contracts to external library
ReflectionAgentFactory = Callable[[str], Any]  # Any = LlmAgent
"""Factory that creates a configured reflection agent for a component type.

Args:
    model: The model name/identifier (e.g., "gemini-2.5-flash").

Returns:
    Configured LlmAgent with appropriate instruction and tools.
"""

# Extended reflection function signature
ReflectionFn = Callable[[str, list[dict[str, Any]], str], Awaitable[str]]
"""Async callable for reflection operations.

Args:
    component_text: Current text of the component being evolved.
    trials: List of performance trials with feedback.
    component_name: Name of the component (e.g., "output_schema").

Returns:
    Proposed improved component text.
"""


# =============================================================================
# Component Name Constants
# =============================================================================

COMPONENT_OUTPUT_SCHEMA: str = "output_schema"
"""Component name for Pydantic output schema definitions."""

COMPONENT_INSTRUCTION: str = "instruction"
"""Component name for agent instructions (default component)."""


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class ComponentReflectionRegistryProtocol(Protocol):
    """Protocol for component-to-reflection-agent registry.

    Maps component names to factory functions that create appropriately
    configured reflection agents.
    """

    def register(
        self,
        component_name: str,
        factory: ReflectionAgentFactory,
    ) -> None:
        """Register a factory for a component name.

        Args:
            component_name: The component name to register (e.g., "output_schema").
            factory: Factory function that creates agents for this component type.
        """
        ...

    def get_factory(
        self,
        component_name: str,
    ) -> ReflectionAgentFactory:
        """Get the factory for a component name.

        Args:
            component_name: The component name to look up.

        Returns:
            The registered factory, or default factory if not found.
        """
        ...

    def get_agent(
        self,
        component_name: str,
        model: str,
    ) -> Any:  # Returns LlmAgent
        """Create a reflection agent for a component.

        Convenience method that calls get_factory and invokes it.

        Args:
            component_name: The component name.
            model: The model name/identifier.

        Returns:
            Configured LlmAgent for the component type.
        """
        ...


# =============================================================================
# Tool Result Schema
# =============================================================================


class SchemaValidationToolResult:
    """Result schema for the validate_output_schema tool.

    This documents the expected return structure from the validation tool.
    The actual implementation returns a dict matching this structure.

    Attributes:
        valid: Whether the schema is syntactically valid.
        class_name: Name of the validated class (if valid).
        field_count: Number of fields in the schema (if valid).
        field_names: List of field names (if valid).
        errors: List of error messages (if invalid).
        stage: Validation stage where failure occurred (if invalid).
        line_number: Line number of the error (if applicable).
    """

    # Valid result example:
    # {
    #     "valid": True,
    #     "class_name": "MySchema",
    #     "field_count": 3,
    #     "field_names": ["name", "value", "count"],
    # }

    # Invalid result example:
    # {
    #     "valid": False,
    #     "errors": ["SyntaxError: unexpected indent at line 5"],
    #     "stage": "syntax",
    #     "line_number": 5,
    # }


# =============================================================================
# Factory Function Signatures
# =============================================================================


def create_text_reflection_agent(model: str) -> Any:
    """Create a reflection agent for text components.

    Creates an LlmAgent configured for free-form text reflection with no
    validation tools. Suitable for instructions, descriptions, and other
    text components.

    Args:
        model: The model name/identifier (e.g., "gemini-2.5-flash").

    Returns:
        Configured LlmAgent with text reflection instruction.
    """
    ...


def create_schema_reflection_agent(model: str) -> Any:
    """Create a reflection agent for output_schema components.

    Creates an LlmAgent configured with:
    - Schema-focused reflection instruction
    - validate_output_schema tool for self-validation
    - Instruction to use validation tool before returning

    Args:
        model: The model name/identifier (e.g., "gemini-2.5-flash").

    Returns:
        Configured LlmAgent with schema validation tool.
    """
    ...


def get_reflection_agent(component_name: str, model: str) -> Any:
    """Get the appropriate reflection agent for a component.

    Uses the global registry to look up the factory for the component name
    and creates an agent. Falls back to text reflection for unknown components.

    Args:
        component_name: The component being evolved (e.g., "output_schema").
        model: The model name/identifier.

    Returns:
        Configured LlmAgent for the component type.
    """
    ...


# =============================================================================
# Tool Function Signature
# =============================================================================


def validate_output_schema(schema_text: str) -> dict[str, Any]:
    """Validate a Pydantic schema definition.

    This function is wrapped as an ADK FunctionTool and provided to the
    schema reflection agent.

    Args:
        schema_text: Python code defining a Pydantic BaseModel class.
            May include markdown code fences which will be stripped.

    Returns:
        dict with validation result:
        - If valid: {"valid": True, "class_name": str, "field_count": int, "field_names": list}
        - If invalid: {"valid": False, "errors": list, "stage": str, "line_number": int|None}

    Examples:
        >>> result = validate_output_schema("class Foo(BaseModel): x: int")
        >>> result["valid"]
        True
        >>> result["class_name"]
        "Foo"
    """
    return {"valid": True, "class_name": "", "field_count": 0}
