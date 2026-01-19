"""Example: Output Schema Evolution.

This example demonstrates evolving a Pydantic output schema as a component,
showing the full workflow: serialization, validation, and deserialization.

The schema_utils module provides utilities to:
1. Serialize a Pydantic BaseModel to Python source text
2. Validate schema text for syntax, structure, and security
3. Deserialize validated schema text back to a usable class

Prerequisites:
    - Python 3.12+
    - gepa-adk installed

Usage:
    python examples/schema_evolution_example.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from gepa_adk.utils.schema_utils import (
    SCHEMA_NAMESPACE,
    SchemaValidationResult,
    deserialize_schema,
    serialize_pydantic_schema,
    validate_schema_text,
)

# =============================================================================
# Example Schemas
# =============================================================================


class TaskOutput(BaseModel):
    """Output schema for task completion."""

    result: str = Field(description="The task result")
    reasoning: str = Field(description="Explanation of approach")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")


class EvaluationOutput(BaseModel):
    """Output schema for evaluation tasks."""

    score: float = Field(ge=0.0, le=1.0, description="Quality score")
    feedback: str = Field(default="", description="Detailed feedback")
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)


# =============================================================================
# Demonstration Functions
# =============================================================================


def demo_serialization() -> None:
    """Demonstrate schema serialization."""
    print("=" * 60)
    print("1. SCHEMA SERIALIZATION")
    print("=" * 60)

    # Serialize a schema to Python source code
    schema_text = serialize_pydantic_schema(TaskOutput)

    print("\nOriginal schema class: TaskOutput")
    print("\nSerialized to Python source:\n")
    print(schema_text)


def demo_validation() -> None:
    """Demonstrate schema validation."""
    print("\n" + "=" * 60)
    print("2. SCHEMA VALIDATION")
    print("=" * 60)

    # Valid schema text
    valid_schema = """
class ValidSchema(BaseModel):
    name: str
    value: int = Field(ge=0)
    tags: list[str] = Field(default_factory=list)
"""

    print("\nValidating a valid schema...")
    result: SchemaValidationResult = validate_schema_text(valid_schema)
    print(f"  Class name: {result.class_name}")
    print(f"  Field count: {result.field_count}")
    print(f"  Field names: {result.field_names}")
    print(f"  Is BaseModel: {issubclass(result.schema_class, BaseModel)}")

    # Invalid schemas that will be rejected
    print("\n--- Security Validation Examples ---")

    # Schema with import (rejected)
    schema_with_import = """
import os
class Malicious(BaseModel):
    path: str = os.getcwd()
"""
    try:
        validate_schema_text(schema_with_import)
    except Exception as e:
        print("\n[REJECTED] Schema with import:")
        print(f"  Error: {type(e).__name__}")
        print("  Reason: Import statements not allowed")

    # Schema with function (rejected)
    schema_with_function = """
def helper():
    return "hack"

class WithFunction(BaseModel):
    field: str = helper()
"""
    try:
        validate_schema_text(schema_with_function)
    except Exception as e:
        print("\n[REJECTED] Schema with function definition:")
        print(f"  Error: {type(e).__name__}")
        print("  Reason: Function definitions not allowed")

    # Schema without BaseModel inheritance (rejected)
    not_basemodel = """
class NotAModel:
    field: str
"""
    try:
        validate_schema_text(not_basemodel)
    except Exception as e:
        print("\n[REJECTED] Class not inheriting BaseModel:")
        print(f"  Error: {type(e).__name__}")
        print("  Reason: Must inherit from BaseModel")


def demo_deserialization() -> None:
    """Demonstrate schema deserialization."""
    print("\n" + "=" * 60)
    print("3. SCHEMA DESERIALIZATION")
    print("=" * 60)

    # Deserialize schema text to a usable class
    schema_text = """
class DeserializedSchema(BaseModel):
    title: str = Field(description="Document title")
    content: str = Field(description="Document content")
    word_count: int = Field(ge=0, default=0)
"""

    print("\nDeserializing schema text...")
    DeserializedSchema = deserialize_schema(schema_text)

    print(f"  Class name: {DeserializedSchema.__name__}")
    print(f"  Fields: {list(DeserializedSchema.model_fields.keys())}")

    # Create an instance to prove it works
    print("\nCreating instance from deserialized class:")
    instance = DeserializedSchema(
        title="Test Document",
        content="This is a test.",
        word_count=4,
    )
    print(f"  title: {instance.title}")
    print(f"  content: {instance.content}")
    print(f"  word_count: {instance.word_count}")


def demo_round_trip() -> None:
    """Demonstrate round-trip: serialize -> deserialize."""
    print("\n" + "=" * 60)
    print("4. ROUND-TRIP (Serialize -> Deserialize)")
    print("=" * 60)

    print("\nOriginal class: EvaluationOutput")
    print(f"  Fields: {list(EvaluationOutput.model_fields.keys())}")

    # Serialize
    schema_text = serialize_pydantic_schema(EvaluationOutput)
    print("\nSerialized to text...")

    # Deserialize
    RestoredSchema = deserialize_schema(schema_text)
    print(f"\nDeserialized class: {RestoredSchema.__name__}")
    print(f"  Fields: {list(RestoredSchema.model_fields.keys())}")

    # Verify fields match
    original_fields = set(EvaluationOutput.model_fields.keys())
    restored_fields = set(RestoredSchema.model_fields.keys())
    print(f"\nFields preserved: {original_fields == restored_fields}")

    # Create instances with both
    print("\nCreating instances with both classes:")
    original = EvaluationOutput(
        score=0.85,
        feedback="Good work!",
        strengths=["Clear", "Concise"],
        improvements=["Add examples"],
    )
    restored = RestoredSchema(
        score=0.85,
        feedback="Good work!",
        strengths=["Clear", "Concise"],
        improvements=["Add examples"],
    )
    print(f"  Original score: {original.score}")
    print(f"  Restored score: {restored.score}")
    print(f"  Values match: {original.score == restored.score}")


def demo_allowed_namespace() -> None:
    """Show what names are available in the schema namespace."""
    print("\n" + "=" * 60)
    print("5. ALLOWED NAMESPACE")
    print("=" * 60)

    print("\nNames available for schema execution:")
    for name, value in sorted(SCHEMA_NAMESPACE.items()):
        if value is not None:
            print(f"  {name}: {type(value).__name__}")


def main() -> None:
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("OUTPUT SCHEMA EVOLUTION - UTILITIES DEMO")
    print("=" * 60)

    demo_serialization()
    demo_validation()
    demo_deserialization()
    demo_round_trip()
    demo_allowed_namespace()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nThese utilities enable output_schema evolution in gepa-adk.")
    print("The evolution engine uses them to:")
    print("  1. Serialize agent.output_schema to component_text")
    print("  2. Validate proposed schema mutations before acceptance")
    print("  3. Deserialize evolved schema for use with the agent")


if __name__ == "__main__":
    main()
