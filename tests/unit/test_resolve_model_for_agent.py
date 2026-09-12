"""Unit tests for the model-selection path and Gemini deprecation guards.

Covers ``_resolve_model_for_agent`` — the helper every agent factory routes a
model string through — plus guards ensuring no default-model path and no
live-model test constant resolves to a Gemini generation Google has announced
a shutdown date for.
"""

from __future__ import annotations

import pytest
from google.adk.models.lite_llm import LiteLlm

from gepa_adk.api import _resolve_model_for_agent
from gepa_adk.domain.models import EvolutionConfig
from tests.fixtures.models import GEMINI_TEST_MODEL, is_deprecated_gemini_model

pytestmark = pytest.mark.unit


class TestResolveModelForAgent:
    """Tests for model resolution and conditional LiteLLM wrapping."""

    @pytest.mark.parametrize(
        "model_string",
        [
            # Deprecated generations are included deliberately: the native
            # pattern is version-agnostic and must keep matching them so a
            # user pinning an old model still reaches ADK's Gemini path
            # (and its error message) rather than the LiteLLM fallback.
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
            "model-optimizer-abc123",
            "model-optimizer-exp-001",
            "projects/my-project/locations/us-central1/endpoints/12345",
            "projects/p/locations/l/publishers/google/models/gemini-pro",
            "projects/test-proj/locations/europe-west1/publishers/google/models/gemini-2.5-flash",
        ],
        ids=[
            "gemini_flash_2.5",
            "gemini_pro_1.5",
            "gemini_pro_1.0",
            "model_optimizer",
            "model_optimizer_exp",
            "vertex_endpoint",
            "vertex_gemini_publisher",
            "vertex_gemini_publisher_full",
        ],
    )
    def test_native_adk_models_return_string(self, model_string: str) -> None:
        """Native ADK models should return string for native handling."""
        result = _resolve_model_for_agent(model_string)
        assert result == model_string
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "model_string",
        [
            "ollama_chat/gpt-oss:20b",
            "ollama_chat/llama3.1:70b",
            "ollama_chat/mistral:latest",
            "ollama/codellama:13b",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/gpt-3.5-turbo",
            "groq/llama-3.1-70b-versatile",
            "groq/mixtral-8x7b-32768",
            "anthropic/claude-3-opus-20240229",
            "anthropic/claude-3-sonnet-20240229",
            "together_ai/meta-llama/Llama-3-70b-chat-hf",
            "azure/gpt-4-deployment",
            "bedrock/anthropic.claude-v2",
        ],
        ids=[
            "ollama_gpt_oss",
            "ollama_llama",
            "ollama_mistral",
            "ollama_codellama",
            "openai_gpt4o",
            "openai_gpt4o_mini",
            "openai_gpt35",
            "groq_llama",
            "groq_mixtral",
            "anthropic_opus",
            "anthropic_sonnet",
            "together_ai_llama",
            "azure_gpt4",
            "bedrock_claude",
        ],
    )
    def test_litellm_providers_return_wrapped_instance(self, model_string: str) -> None:
        """Non-native models should return LiteLlm wrapper instance."""
        result = _resolve_model_for_agent(model_string)
        assert isinstance(result, LiteLlm)

    @pytest.mark.parametrize(
        "model_string",
        [
            "ollama_chat/gpt-oss:20b",
            "openai/gpt-4o",
            "anthropic/claude-3-opus-20240229",
        ],
        ids=[
            "ollama",
            "openai",
            "anthropic",
        ],
    )
    def test_litellm_wrapper_preserves_model_name(self, model_string: str) -> None:
        """LiteLlm wrapper should preserve the original model string."""
        result = _resolve_model_for_agent(model_string)
        assert isinstance(result, LiteLlm)
        assert result.model == model_string

    @pytest.mark.parametrize(
        "model_string",
        [
            "gpt-4",
            "claude-3-opus",
            "llama-3-70b",
            "custom-model",
            "my-fine-tuned-model",
        ],
        ids=[
            "bare_gpt4",
            "bare_claude",
            "bare_llama",
            "custom",
            "fine_tuned",
        ],
    )
    def test_unknown_models_wrapped_with_litellm(self, model_string: str) -> None:
        """Unknown/unrecognized models should be wrapped with LiteLlm."""
        result = _resolve_model_for_agent(model_string)
        assert isinstance(result, LiteLlm)
        assert result.model == model_string

    def test_gemini_partial_match_not_native(self) -> None:
        """Models containing 'gemini' but not matching pattern should wrap."""
        # 'my-gemini-model' doesn't match 'gemini-.*' pattern
        result = _resolve_model_for_agent("my-gemini-model")
        assert isinstance(result, LiteLlm)

    def test_vertex_endpoint_requires_full_path(self) -> None:
        """Partial Vertex paths should not match native patterns."""
        # Missing required path segments
        result = _resolve_model_for_agent("projects/my-project/endpoints/123")
        assert isinstance(result, LiteLlm)


class TestCanonicalModelNotDeprecated:
    """Guards that the model strings this repo actually sends are current.

    ``_resolve_model_for_agent`` matches ``gemini-.*`` and therefore cannot
    tell a live model from a retired one — a deprecated string sails through
    and fails later at call time with an opaque ADK error. These tests put the
    check where it can fail loudly instead: on the constants the repo resolves
    from. When Google announces the next retirement, adding its prefix to
    ``DEPRECATED_GEMINI_PREFIXES`` makes the affected test fail.
    """

    def test_gemini_test_model_is_not_deprecated(self) -> None:
        """The live-model test constant must name a current Gemini model."""
        assert not is_deprecated_gemini_model(GEMINI_TEST_MODEL), (
            f"GEMINI_TEST_MODEL={GEMINI_TEST_MODEL!r} names a retired Gemini "
            "generation; every requires_gemini test and the availability probe "
            "in tests/conftest.py would silently skip. Update "
            "tests/fixtures/models.py to a current model."
        )

    def test_gemini_test_model_resolves_natively(self) -> None:
        """The canonical model must still take ADK's native Gemini path."""
        result = _resolve_model_for_agent(GEMINI_TEST_MODEL)
        assert result == GEMINI_TEST_MODEL
        assert not isinstance(result, LiteLlm)

    def test_default_reflection_model_is_not_deprecated(self) -> None:
        """EvolutionConfig's default reflection model must not be a retired model."""
        default_model = EvolutionConfig().reflection_model
        assert not is_deprecated_gemini_model(default_model), (
            f"EvolutionConfig.reflection_model defaults to {default_model!r}, a "
            "retired Gemini generation. Users who never pass reflection_model "
            "would hit a model-not-found error."
        )

    def test_default_reflection_model_resolves(self) -> None:
        """The default reflection model must resolve to a usable agent model."""
        default_model = EvolutionConfig().reflection_model
        result = _resolve_model_for_agent(default_model)
        assert isinstance(result, LiteLlm)
        assert result.model == default_model


class TestIsDeprecatedGeminiModel:
    """Tests for the deprecation predicate backing the guards above."""

    @pytest.mark.parametrize(
        "model_string",
        [
            "gemini-2.5-flash",
            "gemini/gemini-2.5-flash",
            "vertex_ai/gemini-2.0-flash",
            "gemini-2.5-flash-exp",
            "gemini-1.5-flash-8b",
            "gemini-live-2.5-flash-preview",
            "projects/p/locations/l/publishers/google/models/gemini-1.5-pro",
        ],
        ids=[
            "bare_deprecated",
            "litellm_gemini_prefix",
            "litellm_vertex_prefix",
            "unpublished_exp_suffix",
            "unenumerated_1_5_variant",
            "live_api_variant",
            "vertex_publisher_path",
        ],
    )
    def test_deprecated_variants_flagged(self, model_string: str) -> None:
        """Prefixed, suffixed, and Vertex-path forms must still be flagged."""
        assert is_deprecated_gemini_model(model_string)

    @pytest.mark.parametrize(
        "model_string",
        [
            "gemini-3.7-flash",
            "gemini-3.1-pro-preview",
            "gemini-3.8-flash",
            "gemini/gemini-3.8-flash",
            "ollama_chat/gpt-oss:20b",
            "openai/gpt-4o",
            "projects/p/locations/l/publishers/google/models/gemini-3.8-flash",
        ],
        ids=[
            "current_flash",
            "current_pro_preview",
            "newest_stable_flash",
            "litellm_current_flash",
            "ollama",
            "openai",
            "vertex_publisher_current",
        ],
    )
    def test_current_models_not_flagged(self, model_string: str) -> None:
        """Current Gemini and non-Gemini identifiers must not be flagged."""
        assert not is_deprecated_gemini_model(model_string)
