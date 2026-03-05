"""Unit tests for pre-flight validation enhancements (Story 2.5).

Tests cover critic type validation, EvolutionConfig consistency checks,
component name list validation, consolidated pre-flight functions, and
stateless retry after validation failure.

Note:
    Tests verify that all validation errors raise ConfigurationError with
    structured context (field, value, constraint) and that no validation
    check makes network calls (guaranteed by synchronous function signatures).
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent, SequentialAgent
from structlog.testing import capture_logs

from gepa_adk.api import (
    _pre_flight_validate_evolve,
    _pre_flight_validate_group,
    _pre_flight_validate_workflow,
    _validate_critic,
    _validate_evolve_components,
)
from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import EvolutionConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def valid_agent() -> LlmAgent:
    """Create a valid LlmAgent for testing."""
    return LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant.",
    )


@pytest.fixture
def valid_agent_with_schema() -> LlmAgent:
    """Create a valid LlmAgent with output_schema for testing."""
    from pydantic import BaseModel, Field

    class TestSchema(BaseModel):
        answer: str
        score: float = Field(ge=0.0, le=1.0)

    return LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant.",
        output_schema=TestSchema,
    )


@pytest.fixture
def valid_critic() -> LlmAgent:
    """Create a valid critic LlmAgent for testing."""
    from pydantic import BaseModel, Field

    class CriticSchema(BaseModel):
        score: float = Field(ge=0.0, le=1.0)

    return LlmAgent(
        name="critic",
        model="gemini-2.5-flash",
        instruction="Score the response.",
        output_schema=CriticSchema,
    )


@pytest.fixture
def sample_trainset() -> list[dict[str, str]]:
    """Create a sample training set."""
    return [
        {"input": "What is 2+2?", "expected": "4"},
        {"input": "What is the capital of France?", "expected": "Paris"},
    ]


class TestValidateCritic:
    """Tests for _validate_critic() function."""

    def test_valid_llm_agent_critic(self, valid_critic: LlmAgent) -> None:
        """Test that valid LlmAgent critic passes validation."""
        _validate_critic(valid_critic)

    def test_none_critic_with_output_schema(
        self, valid_agent_with_schema: LlmAgent
    ) -> None:
        """Test that None critic is valid when agent has output_schema."""
        _validate_critic(None, agent=valid_agent_with_schema)

    def test_none_critic_without_output_schema_raises(
        self, valid_agent: LlmAgent
    ) -> None:
        """Test that None critic without output_schema raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_critic(None, agent=valid_agent)
        assert exc_info.value.field == "critic"
        assert exc_info.value.constraint == "must provide critic or agent.output_schema"

    def test_invalid_critic_type_raises(self) -> None:
        """Test that non-LlmAgent critic raises ConfigurationError."""
        fake_critic = SequentialAgent(name="bad_critic", sub_agents=[])
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_critic(fake_critic)
        assert exc_info.value.field == "critic"
        assert exc_info.value.value == "SequentialAgent"
        assert exc_info.value.constraint == "must be LlmAgent"

    def test_string_critic_raises(self) -> None:
        """Test that string critic raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_critic("some_shortcut")
        assert exc_info.value.field == "critic"
        assert exc_info.value.value == "str"

    def test_none_critic_no_agent(self) -> None:
        """Test that None critic with no agent passes (group path)."""
        _validate_critic(None)


class TestEvolutionConfigConsistency:
    """Tests for EvolutionConfig cross-field consistency checks."""

    def test_use_merge_without_invocations_raises(self) -> None:
        """Test use_merge=True with max_merge_invocations=0 raises."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(use_merge=True, max_merge_invocations=0)
        assert exc_info.value.field == "max_merge_invocations"
        assert exc_info.value.value == 0
        assert "use_merge=True" in str(exc_info.value.constraint)

    def test_use_merge_with_invocations_passes(self) -> None:
        """Test use_merge=True with max_merge_invocations > 0 passes."""
        config = EvolutionConfig(use_merge=True, max_merge_invocations=5)
        assert config.use_merge is True
        assert config.max_merge_invocations == 5

    def test_patience_exceeds_max_iterations_warns(self) -> None:
        """Test patience > max_iterations logs warning."""
        with capture_logs() as logs:
            config = EvolutionConfig(patience=100, max_iterations=10)
        assert config.patience == 100
        assert config.max_iterations == 10
        warning_logs = [
            log
            for log in logs
            if log.get("event") == "config.patience.exceeds_max_iterations"
        ]
        assert len(warning_logs) == 1
        assert warning_logs[0]["patience"] == 100
        assert warning_logs[0]["max_iterations"] == 10

    def test_patience_within_max_iterations_no_warning(self) -> None:
        """Test patience <= max_iterations does not warn."""
        with capture_logs() as logs:
            EvolutionConfig(patience=5, max_iterations=50)
        warning_logs = [
            log
            for log in logs
            if log.get("event") == "config.patience.exceeds_max_iterations"
        ]
        assert len(warning_logs) == 0

    def test_patience_zero_no_warning(self) -> None:
        """Test patience=0 (disabled) does not warn regardless of max_iterations."""
        with capture_logs() as logs:
            EvolutionConfig(patience=0, max_iterations=5)
        warning_logs = [
            log
            for log in logs
            if log.get("event") == "config.patience.exceeds_max_iterations"
        ]
        assert len(warning_logs) == 0

    def test_stop_callbacks_non_callable_raises(self) -> None:
        """Test non-callable stop_callbacks raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(stop_callbacks=["not_callable"])
        assert exc_info.value.field == "stop_callbacks[0]"
        assert exc_info.value.value == "str"
        assert exc_info.value.constraint == "must be callable"

    def test_stop_callbacks_callable_passes(self) -> None:
        """Test callable stop_callbacks pass validation."""

        def my_stopper(state: object) -> bool:
            return False

        config = EvolutionConfig(stop_callbacks=[my_stopper])
        assert len(config.stop_callbacks) == 1

    def test_stop_callbacks_empty_passes(self) -> None:
        """Test empty stop_callbacks list passes validation."""
        config = EvolutionConfig(stop_callbacks=[])
        assert config.stop_callbacks == []

    def test_stop_callbacks_multiple_with_one_invalid(self) -> None:
        """Test multiple callbacks where one is invalid raises."""

        def valid_stopper(state: object) -> bool:
            return False

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(stop_callbacks=[valid_stopper, 42])
        assert exc_info.value.field == "stop_callbacks[1]"
        assert exc_info.value.value == "int"


class TestValidateEvolveComponents:
    """Tests for _validate_evolve_components() function."""

    def test_none_components_passes(self) -> None:
        """Test None components passes validation."""
        _validate_evolve_components(None, context="test")

    def test_valid_components_passes(self) -> None:
        """Test valid component list passes validation."""
        _validate_evolve_components(["instruction", "output_schema"], context="test")

    def test_duplicate_components_raises(self) -> None:
        """Test duplicate components raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_evolve_components(["instruction", "instruction"], context="test")
        assert exc_info.value.field == "components"
        assert "duplicate" in str(exc_info.value).lower()

    def test_empty_string_component_raises(self) -> None:
        """Test empty string in components raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_evolve_components(["instruction", ""], context="test")
        assert exc_info.value.field == "component_name"

    def test_invalid_identifier_component_raises(self) -> None:
        """Test non-identifier component name raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_evolve_components(["has spaces"], context="test")
        assert exc_info.value.field == "component_name"
        assert exc_info.value.value == "has spaces"

    def test_digit_start_component_raises(self) -> None:
        """Test component starting with digit raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_evolve_components(["123invalid"], context="test")
        assert exc_info.value.field == "component_name"
        assert exc_info.value.value == "123invalid"

    def test_special_chars_component_raises(self) -> None:
        """Test component with special chars raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_evolve_components(["foo-bar"], context="test")
        assert exc_info.value.field == "component_name"


class TestPreFlightValidateWorkflow:
    """Tests for _pre_flight_validate_workflow() consolidated function."""

    def test_valid_inputs_pass(self, sample_trainset: list[dict[str, str]]) -> None:
        """Test valid workflow inputs pass all pre-flight checks."""
        _pre_flight_validate_workflow(sample_trainset, None, None)

    def test_empty_trainset_raises(self) -> None:
        """Test empty trainset raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_workflow([], None, None)
        assert exc_info.value.field == "trainset"

    def test_invalid_critic_raises(self, sample_trainset: list[dict[str, str]]) -> None:
        """Test non-LlmAgent critic raises ConfigurationError."""
        bad_critic = SequentialAgent(name="bad", sub_agents=[])
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_workflow(sample_trainset, bad_critic, None)
        assert exc_info.value.field == "critic"

    def test_duplicate_components_raises(
        self, sample_trainset: list[dict[str, str]]
    ) -> None:
        """Test duplicate per-agent components raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_workflow(
                sample_trainset,
                None,
                {"agent_a": ["instruction", "instruction"]},
            )
        assert exc_info.value.field == "components"


class TestPreFlightValidateEvolve:
    """Tests for _pre_flight_validate_evolve() consolidated function."""

    def test_valid_inputs_pass(
        self,
        valid_agent_with_schema: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test valid inputs pass all pre-flight checks."""
        _pre_flight_validate_evolve(
            valid_agent_with_schema, sample_trainset, None, None
        )

    def test_valid_inputs_with_critic(
        self,
        valid_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
        valid_critic: LlmAgent,
    ) -> None:
        """Test valid inputs with critic pass all pre-flight checks."""
        _pre_flight_validate_evolve(valid_agent, sample_trainset, valid_critic, None)

    def test_invalid_agent_type_raises(
        self, sample_trainset: list[dict[str, str]]
    ) -> None:
        """Test non-LlmAgent raises ConfigurationError."""
        bad_agent = SequentialAgent(name="bad", sub_agents=[])
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_evolve(
                bad_agent,
                sample_trainset,
                None,
                None,
            )
        assert exc_info.value.field == "agent"

    def test_empty_trainset_raises(self, valid_agent_with_schema: LlmAgent) -> None:
        """Test empty trainset raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_evolve(valid_agent_with_schema, [], None, None)
        assert exc_info.value.field == "trainset"

    def test_invalid_critic_type_raises(
        self,
        valid_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test non-LlmAgent critic raises ConfigurationError."""
        bad_critic = SequentialAgent(name="bad_critic", sub_agents=[])
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_evolve(
                valid_agent,
                sample_trainset,
                bad_critic,
                None,
            )
        assert exc_info.value.field == "critic"

    def test_duplicate_components_raises(
        self,
        valid_agent_with_schema: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test duplicate components in evolve raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_evolve(
                valid_agent_with_schema,
                sample_trainset,
                None,
                ["instruction", "instruction"],
            )
        assert exc_info.value.field == "components"


class TestPreFlightValidateGroup:
    """Tests for _pre_flight_validate_group() consolidated function."""

    def test_valid_inputs_pass(
        self,
        valid_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test valid group inputs pass all pre-flight checks."""
        _pre_flight_validate_group(
            {"agent_a": valid_agent}, sample_trainset, None, None
        )

    def test_invalid_agent_name_raises(
        self,
        valid_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test invalid agent name raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_group(
                {"123invalid": valid_agent}, sample_trainset, None, None
            )
        assert exc_info.value.field == "component_name"

    def test_invalid_critic_type_raises(
        self,
        valid_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test non-LlmAgent critic in group raises ConfigurationError."""
        bad_critic = SequentialAgent(name="bad", sub_agents=[])
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_group(
                {"agent_a": valid_agent},
                sample_trainset,
                bad_critic,
                None,
            )
        assert exc_info.value.field == "critic"

    def test_duplicate_components_in_group_raises(
        self,
        valid_agent: LlmAgent,
        sample_trainset: list[dict[str, str]],
    ) -> None:
        """Test duplicate components per-agent raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            _pre_flight_validate_group(
                {"agent_a": valid_agent},
                sample_trainset,
                None,
                {"agent_a": ["instruction", "instruction"]},
            )
        assert exc_info.value.field == "components"


class TestStatelessRetry:
    """Tests for stateless retry after validation failure (AC 4)."""

    def test_config_retry_after_failure(self) -> None:
        """Test creating EvolutionConfig after catching validation error."""
        # First: create invalid config
        with pytest.raises(ConfigurationError):
            EvolutionConfig(max_iterations=-1)

        # Then: create valid config (no re-import needed)
        config = EvolutionConfig(max_iterations=10)
        assert config.max_iterations == 10

    def test_config_consistency_retry_after_failure(self) -> None:
        """Test retry after consistency validation failure."""
        # First: create invalid config
        with pytest.raises(ConfigurationError):
            EvolutionConfig(use_merge=True, max_merge_invocations=0)

        # Then: create valid config
        config = EvolutionConfig(use_merge=True, max_merge_invocations=5)
        assert config.use_merge is True
        assert config.max_merge_invocations == 5

    def test_pre_flight_retry_after_failure(self) -> None:
        """Test pre-flight validation retry after failure."""
        # First: fail with bad critic
        with pytest.raises(ConfigurationError):
            _validate_critic("not_an_agent")
        # Then: succeed with valid critic (no re-import needed)
        valid_critic = LlmAgent(
            name="critic",
            model="gemini-2.5-flash",
            instruction="Score.",
        )
        _validate_critic(valid_critic)


class TestConfigurationErrorStructure:
    """Tests verifying ConfigurationError includes field/value/constraint."""

    def test_critic_error_has_structured_fields(self) -> None:
        """Test critic validation error has all structured fields."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_critic(42)
        error = exc_info.value
        assert error.field is not None
        assert error.value is not None
        assert error.constraint is not None

    def test_config_consistency_error_has_structured_fields(self) -> None:
        """Test config consistency error has all structured fields."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(use_merge=True, max_merge_invocations=0)
        error = exc_info.value
        assert error.field == "max_merge_invocations"
        assert error.value == 0
        assert error.constraint is not None

    def test_stop_callbacks_error_has_structured_fields(self) -> None:
        """Test stop_callbacks error has all structured fields."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(stop_callbacks=[None])
        error = exc_info.value
        assert error.field == "stop_callbacks[0]"
        assert error.value == "NoneType"
        assert error.constraint == "must be callable"

    def test_component_duplicate_error_has_structured_fields(self) -> None:
        """Test component duplicate error has all structured fields."""
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_evolve_components(["instruction", "instruction"], context="test")
        error = exc_info.value
        assert error.field == "components"
        assert error.value is not None
        assert error.constraint is not None


class TestEvolutionConfigBoundaryFields:
    """[TEA] Verify each __post_init__ range check has field/value/constraint."""

    def test_max_iterations_negative_structured(self) -> None:
        """Negative max_iterations produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_iterations=-1)
        error = exc_info.value
        assert error.field == "max_iterations"
        assert error.value == -1
        assert error.constraint == ">= 0"

    def test_max_concurrent_evals_zero_structured(self) -> None:
        """Zero max_concurrent_evals produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_concurrent_evals=0)
        error = exc_info.value
        assert error.field == "max_concurrent_evals"
        assert error.value == 0
        assert error.constraint == ">= 1"

    def test_min_improvement_threshold_negative_structured(self) -> None:
        """Negative threshold produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=-0.01)
        error = exc_info.value
        assert error.field == "min_improvement_threshold"
        assert error.value == -0.01
        assert error.constraint == ">= 0.0"

    def test_patience_negative_structured(self) -> None:
        """Negative patience produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(patience=-1)
        error = exc_info.value
        assert error.field == "patience"
        assert error.value == -1
        assert error.constraint == ">= 0"

    def test_reflection_model_empty_structured(self) -> None:
        """Empty reflection_model produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(reflection_model="")
        error = exc_info.value
        assert error.field == "reflection_model"
        assert error.value == ""
        assert error.constraint == "non-empty string"

    def test_acceptance_metric_invalid_structured(self) -> None:
        """Invalid acceptance_metric produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(acceptance_metric="invalid")
        error = exc_info.value
        assert error.field == "acceptance_metric"
        assert error.value == "invalid"
        assert error.constraint == "sum|mean"

    def test_max_merge_invocations_negative_structured(self) -> None:
        """Negative max_merge_invocations produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(max_merge_invocations=-1)
        error = exc_info.value
        assert error.field == "max_merge_invocations"
        assert error.value == -1
        assert error.constraint == ">= 0"

    def test_frontier_type_invalid_structured(self) -> None:
        """Invalid frontier_type produces structured ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(frontier_type="bogus")
        error = exc_info.value
        assert error.field == "frontier_type"
        assert error.value == "bogus"
        assert error.constraint is not None


class TestEvolutionConfigFloatEdgeCases:
    """[TEA] IEEE 754 edge case tests for float fields (GH #284)."""

    def test_min_improvement_threshold_inf_raises(self) -> None:
        """Positive infinity threshold raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=float("inf"))
        error = exc_info.value
        assert error.field == "min_improvement_threshold"
        assert error.constraint == "finite float"

    def test_min_improvement_threshold_neg_inf_raises(self) -> None:
        """Negative infinity threshold raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=float("-inf"))
        error = exc_info.value
        assert error.field == "min_improvement_threshold"
        assert error.constraint == "finite float"

    def test_min_improvement_threshold_nan_raises(self) -> None:
        """NaN threshold raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=float("nan"))
        error = exc_info.value
        assert error.field == "min_improvement_threshold"
        assert error.constraint == "finite float"

    def test_min_improvement_threshold_epsilon(self) -> None:
        """Very small positive threshold is valid."""
        import sys

        config = EvolutionConfig(min_improvement_threshold=sys.float_info.epsilon)
        assert config.min_improvement_threshold > 0.0

    def test_min_improvement_threshold_zero(self) -> None:
        """Zero threshold is valid (accept any improvement)."""
        config = EvolutionConfig(min_improvement_threshold=0.0)
        assert config.min_improvement_threshold == 0.0

    def test_min_improvement_threshold_negative_epsilon(self) -> None:
        """Negative epsilon raises ConfigurationError."""
        import sys

        with pytest.raises(ConfigurationError) as exc_info:
            EvolutionConfig(min_improvement_threshold=-sys.float_info.epsilon)
        error = exc_info.value
        assert error.field == "min_improvement_threshold"
        assert error.value < 0.0
        assert error.constraint == ">= 0.0"
