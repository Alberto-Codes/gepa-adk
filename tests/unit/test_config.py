"""Unit tests for EvolutionConfig fields.

Tests cover configuration fields including:
- reflection_prompt field acceptance and validation
- stop_callbacks field acceptance
"""

from structlog.testing import capture_logs

from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.domain.stopper import StopperState


class TestReflectionPromptField:
    """Tests for reflection_prompt field in EvolutionConfig."""

    def test_reflection_prompt_accepts_string(self) -> None:
        """EvolutionConfig accepts a string for reflection_prompt."""
        custom_prompt = "Improve: {component_text}\n{trials}"
        config = EvolutionConfig(reflection_prompt=custom_prompt)
        assert config.reflection_prompt == custom_prompt

    def test_reflection_prompt_defaults_to_none(self) -> None:
        """EvolutionConfig.reflection_prompt defaults to None."""
        config = EvolutionConfig()
        assert config.reflection_prompt is None

    def test_reflection_prompt_accepts_none_explicitly(self) -> None:
        """EvolutionConfig accepts None explicitly for reflection_prompt."""
        config = EvolutionConfig(reflection_prompt=None)
        assert config.reflection_prompt is None


class TestReflectionPromptValidation:
    """Tests for reflection_prompt placeholder validation warnings."""

    def test_missing_component_text_placeholder_warns(self) -> None:
        """Warning logged when {component_text} placeholder is missing."""
        with capture_logs() as cap_logs:
            config = EvolutionConfig(reflection_prompt="Improve based on: {trials}")

        # Should still create config (warning, not error)
        assert config.reflection_prompt is not None

        # Check warning was logged with correct placeholder
        warning_logs = [
            log
            for log in cap_logs
            if log.get("log_level") == "warning"
            and log.get("placeholder") == "component_text"
        ]
        assert len(warning_logs) == 1

    def test_missing_trials_placeholder_warns(self) -> None:
        """Warning logged when {trials} placeholder is missing."""
        with capture_logs() as cap_logs:
            config = EvolutionConfig(reflection_prompt="Improve: {component_text}")

        # Should still create config (warning, not error)
        assert config.reflection_prompt is not None

        # Check warning was logged with correct placeholder
        warning_logs = [
            log
            for log in cap_logs
            if log.get("log_level") == "warning" and log.get("placeholder") == "trials"
        ]
        assert len(warning_logs) == 1

    def test_valid_prompt_no_warning(self) -> None:
        """No warning when both placeholders are present."""
        with capture_logs() as cap_logs:
            config = EvolutionConfig(
                reflection_prompt="Improve: {component_text}\nTrials: {trials}"
            )

        assert config.reflection_prompt is not None

        # Should not have placeholder warnings
        warning_logs = [
            log
            for log in cap_logs
            if log.get("log_level") == "warning"
            and log.get("event") == "config.reflection_prompt.missing_placeholder"
        ]
        assert len(warning_logs) == 0

    def test_empty_string_treated_as_none(self) -> None:
        """Empty string reflection_prompt is converted to None."""
        with capture_logs() as cap_logs:
            config = EvolutionConfig(reflection_prompt="")

        # Should be converted to None
        assert config.reflection_prompt is None

        # Should log info about empty string
        info_logs = [
            log
            for log in cap_logs
            if log.get("log_level") == "info"
            and log.get("event") == "config.reflection_prompt.empty"
        ]
        assert len(info_logs) == 1


class MaxIterationsStopper:
    """Sample stopper for testing stop_callbacks field."""

    def __init__(self, max_iterations: int) -> None:
        """Initialize with maximum iteration count."""
        self.max_iterations = max_iterations

    def __call__(self, state: StopperState) -> bool:
        """Return True when iteration count reaches max_iterations."""
        return state.iteration >= self.max_iterations


class TestStopCallbacksField:
    """Tests for stop_callbacks field in EvolutionConfig."""

    def test_stop_callbacks_defaults_to_empty_list(self) -> None:
        """EvolutionConfig.stop_callbacks defaults to empty list."""
        config = EvolutionConfig()
        assert config.stop_callbacks == []
        assert isinstance(config.stop_callbacks, list)

    def test_stop_callbacks_accepts_list_of_stoppers(self) -> None:
        """EvolutionConfig accepts a list of stopper callbacks."""
        stopper1 = MaxIterationsStopper(100)
        stopper2 = MaxIterationsStopper(50)

        config = EvolutionConfig(stop_callbacks=[stopper1, stopper2])

        assert len(config.stop_callbacks) == 2
        assert config.stop_callbacks[0] is stopper1
        assert config.stop_callbacks[1] is stopper2

    def test_stop_callbacks_accepts_empty_list(self) -> None:
        """EvolutionConfig accepts an explicit empty list."""
        config = EvolutionConfig(stop_callbacks=[])
        assert config.stop_callbacks == []

    def test_stop_callbacks_accepts_single_stopper(self) -> None:
        """EvolutionConfig accepts a list with a single stopper."""
        stopper = MaxIterationsStopper(100)
        config = EvolutionConfig(stop_callbacks=[stopper])

        assert len(config.stop_callbacks) == 1
        assert config.stop_callbacks[0] is stopper

    def test_stop_callbacks_stoppers_are_callable(self) -> None:
        """Stoppers in stop_callbacks are callable with StopperState."""
        stopper = MaxIterationsStopper(10)
        config = EvolutionConfig(stop_callbacks=[stopper])

        state = StopperState(
            iteration=5,
            best_score=0.5,
            stagnation_counter=0,
            total_evaluations=25,
            candidates_count=1,
            elapsed_seconds=60.0,
        )

        # Verify stopper can be called
        result = config.stop_callbacks[0](state)
        assert isinstance(result, bool)
        assert result is False

    def test_stop_callbacks_accepts_function_stoppers(self) -> None:
        """EvolutionConfig accepts function-based stoppers."""

        def score_stopper(state: StopperState) -> bool:
            return state.best_score >= 0.95

        config = EvolutionConfig(stop_callbacks=[score_stopper])

        assert len(config.stop_callbacks) == 1
        assert callable(config.stop_callbacks[0])

    def test_stop_callbacks_accepts_lambda_stoppers(self) -> None:
        """EvolutionConfig accepts lambda stoppers."""
        config = EvolutionConfig(
            stop_callbacks=[lambda state: state.elapsed_seconds >= 3600.0]
        )

        assert len(config.stop_callbacks) == 1
        assert callable(config.stop_callbacks[0])

    def test_stop_callbacks_mixed_stopper_types(self) -> None:
        """EvolutionConfig accepts mixed stopper implementations."""
        class_stopper = MaxIterationsStopper(100)

        def func_stopper(state: StopperState) -> bool:
            return state.best_score >= 0.95

        lambda_stopper = lambda state: state.stagnation_counter >= 10  # noqa: E731

        config = EvolutionConfig(
            stop_callbacks=[class_stopper, func_stopper, lambda_stopper]
        )

        assert len(config.stop_callbacks) == 3
        for stopper in config.stop_callbacks:
            assert callable(stopper)
