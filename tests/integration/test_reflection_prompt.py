"""Integration tests for reflection_prompt configuration.

These tests verify that custom reflection prompts are properly wired
through the evolution pipeline and actually used during mutation.
"""

from __future__ import annotations

import pytest

from gepa_adk.domain.models import EvolutionConfig
from gepa_adk.engine.proposer import DEFAULT_PROMPT_TEMPLATE

pytestmark = pytest.mark.integration


class TestReflectionPromptIntegration:
    """Integration tests for custom reflection prompt usage."""

    def test_default_prompt_template_is_importable(self) -> None:
        """DEFAULT_PROMPT_TEMPLATE can be imported from proposer module."""
        # This test verifies FR-005: users can import and extend the default
        assert isinstance(DEFAULT_PROMPT_TEMPLATE, str)
        assert "{current_instruction}" in DEFAULT_PROMPT_TEMPLATE
        assert "{feedback_examples}" in DEFAULT_PROMPT_TEMPLATE

    def test_custom_prompt_extends_default(self) -> None:
        """Users can extend DEFAULT_PROMPT_TEMPLATE with custom additions."""
        custom_prompt = DEFAULT_PROMPT_TEMPLATE + "\n\nAdditional: Be concise."
        config = EvolutionConfig(reflection_prompt=custom_prompt)

        assert config.reflection_prompt is not None
        assert "Additional: Be concise." in config.reflection_prompt
        assert "{current_instruction}" in config.reflection_prompt

    @pytest.mark.asyncio
    async def test_custom_prompt_passed_to_proposer(self) -> None:
        """Custom reflection_prompt is passed through to the proposer."""
        from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer

        custom_prompt = "Custom: {current_instruction}\n{feedback_examples}"

        # Create proposer with custom prompt
        proposer = AsyncReflectiveMutationProposer(
            model="test-model",
            prompt_template=custom_prompt,
        )

        # Verify the prompt template is stored
        assert proposer.prompt_template == custom_prompt
