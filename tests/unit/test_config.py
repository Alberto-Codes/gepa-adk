"""Unit tests for EvolutionConfig reflection_prompt field.

Tests cover the reflection_prompt configuration field including:
- Field acceptance and default value
- Placeholder validation warnings (US2)
- Empty string handling (US2)
"""

from structlog.testing import capture_logs

from gepa_adk.domain.models import EvolutionConfig


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
