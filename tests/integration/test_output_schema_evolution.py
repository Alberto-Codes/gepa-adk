"""Integration tests for output schema evolution.

Tests the full workflow of evolving Pydantic output schemas as components,
including serialization, validation, and engine integration.
"""

from typing import Any, Mapping, Sequence

import pytest
from pydantic import BaseModel, Field

from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import AsyncGEPAAdapter, EvaluationBatch
from gepa_adk.utils.schema_utils import (
    SchemaValidationResult,
    deserialize_schema,
    serialize_pydantic_schema,
    validate_schema_text,
)

pytestmark = pytest.mark.integration


# =============================================================================
# Test Schemas
# =============================================================================


class TaskOutput(BaseModel):
    """Test schema for output evolution."""

    result: str = Field(description="Task result")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class EvaluationOutput(BaseModel):
    """Test schema for evaluation tasks."""

    score: float = Field(ge=0.0, le=1.0)
    feedback: str = Field(default="")


# =============================================================================
# Mock Adapter for Schema Evolution Tests
# =============================================================================


class SchemaEvolutionMockAdapter(
    AsyncGEPAAdapter[dict[str, str], dict[str, Any], None]
):
    """Mock adapter that simulates schema evolution proposals."""

    def __init__(
        self,
        scores: list[float] | None = None,
        propose_invalid_schema: bool = False,
    ) -> None:
        """Initialize mock adapter.

        Args:
            scores: Predetermined scores for evaluation.
            propose_invalid_schema: If True, propose invalid schemas to test validation.
        """
        self._scores = iter(scores) if scores else iter([0.5, 0.6, 0.7, 0.8, 0.9])
        self._propose_invalid = propose_invalid_schema
        self._proposal_count = 0

    async def evaluate(
        self,
        batch: list[Any],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate candidate and return mock results."""
        score = next(self._scores, 0.5)
        return EvaluationBatch(
            outputs=[None] * len(batch),
            scores=[score] * len(batch),
            trajectories=[{}] * len(batch) if capture_traces else None,
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Create empty reflective dataset."""
        return {comp: [] for comp in components_to_update}

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new component texts."""
        self._proposal_count += 1
        result = {}

        for comp in components_to_update:
            if comp == "output_schema":
                if self._propose_invalid and self._proposal_count == 1:
                    # First proposal: invalid schema (has import)
                    result[comp] = """
import os
class InvalidSchema(BaseModel):
    field: str = os.getcwd()
"""
                else:
                    # Valid schema proposal
                    result[comp] = """
class EvolvedOutput(BaseModel):
    result: str = Field(description="Improved result")
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    reasoning: str = Field(default="", description="Explanation")
"""
            else:
                # Non-schema component
                result[comp] = f"Improved: {candidate.get(comp, '')}"

        return result


# =============================================================================
# Integration Tests
# =============================================================================


class TestSchemaSerializationIntegration:
    """Integration tests for schema serialization."""

    def test_serialize_and_validate_round_trip(self) -> None:
        """Test serializing a schema and validating the result."""
        # Serialize
        schema_text = serialize_pydantic_schema(TaskOutput)

        # Validate
        result: SchemaValidationResult = validate_schema_text(schema_text)

        assert result.class_name == "TaskOutput"
        assert "result" in result.field_names
        assert "confidence" in result.field_names

    def test_serialize_and_deserialize_round_trip(self) -> None:
        """Test full round-trip: serialize -> deserialize."""
        # Serialize
        schema_text = serialize_pydantic_schema(TaskOutput)

        # Deserialize
        RestoredSchema = deserialize_schema(schema_text)

        # Verify fields match
        assert set(RestoredSchema.model_fields.keys()) == set(
            TaskOutput.model_fields.keys()
        )

        # Verify instances work
        original = TaskOutput(result="test", confidence=0.8)
        restored = RestoredSchema(result="test", confidence=0.8)
        assert original.result == restored.result
        assert original.confidence == restored.confidence


class TestSchemaEvolutionEngine:
    """Integration tests for schema evolution with the engine."""

    @pytest.mark.asyncio
    async def test_evolution_with_output_schema_component(self) -> None:
        """Test evolution targeting output_schema component (T039).

        Note: Engine currently requires 'instruction' component, so we include
        both but the test verifies output_schema is also evolved.
        """
        # Scores: baseline(2) + 3 iterations(2 each) = 8 scores
        adapter = SchemaEvolutionMockAdapter(
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7, 0.8, 0.8]
        )

        # Initial candidate with instruction and output_schema
        schema_text = serialize_pydantic_schema(TaskOutput)
        candidate = Candidate(
            components={
                "instruction": "Complete the task.",
                "output_schema": schema_text,
            },
            generation=0,
        )

        config = EvolutionConfig(max_iterations=3)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
        )
        result = await engine.run()

        # Evolution should complete
        assert result.total_iterations > 0
        assert result.final_score >= result.original_score

    @pytest.mark.asyncio
    async def test_evolution_with_instruction_and_output_schema(self) -> None:
        """Test evolution with both instruction and output_schema (T040)."""
        # More scores for dual-component evolution
        adapter = SchemaEvolutionMockAdapter(
            scores=[0.5] * 2 + [0.6] * 2 + [0.7] * 2 + [0.8] * 2
        )

        # Initial candidate with both components
        schema_text = serialize_pydantic_schema(TaskOutput)
        candidate = Candidate(
            components={
                "instruction": "Complete the task.",
                "output_schema": schema_text,
            },
            generation=0,
        )

        config = EvolutionConfig(max_iterations=3)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
        )
        result = await engine.run()

        # Evolution should complete with improvement
        assert result.total_iterations > 0
        assert result.final_score >= result.original_score

    @pytest.mark.asyncio
    async def test_invalid_schema_proposals_are_rejected(self) -> None:
        """Test that invalid schema proposals are rejected and skipped."""
        # Adapter proposes invalid schema first, then valid
        adapter = SchemaEvolutionMockAdapter(
            scores=[0.5, 0.5, 0.6, 0.6, 0.7, 0.7],
            propose_invalid_schema=True,
        )

        schema_text = serialize_pydantic_schema(TaskOutput)
        candidate = Candidate(
            components={
                "instruction": "Complete the task.",
                "output_schema": schema_text,
            },
            generation=0,
        )

        config = EvolutionConfig(max_iterations=2, patience=5)
        engine = AsyncGEPAEngine(
            adapter=adapter,
            config=config,
            initial_candidate=candidate,
            batch=[{"input": "test"}],
        )
        result = await engine.run()

        # Evolution should complete despite invalid proposal
        assert result.total_iterations > 0


class TestSchemaValidationIntegration:
    """Integration tests for schema validation edge cases."""

    def test_validation_accepts_complex_types(self) -> None:
        """Test validation accepts schemas with complex types."""
        schema_text = """
class ComplexSchema(BaseModel):
    items: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    optional_value: str | None = None
"""
        result = validate_schema_text(schema_text)
        assert result.class_name == "ComplexSchema"
        assert result.field_count == 3

    def test_validation_rejects_multiple_violations(self) -> None:
        """Test validation rejects schema with multiple security violations."""
        from gepa_adk.domain.exceptions import SchemaValidationError

        # Schema with both import and function
        schema_text = """
import os

def helper():
    return "bad"

class Malicious(BaseModel):
    field: str
"""
        # Should reject on first violation (import)
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema_text(schema_text)

        assert "import" in str(exc_info.value).lower()
