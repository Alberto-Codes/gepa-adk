"""Unit tests for _resolve_model_for_agent helper function."""

from __future__ import annotations

import pytest
from google.adk.models.lite_llm import LiteLlm

from gepa_adk.api import _resolve_model_for_agent


class TestResolveModelForAgent:
    """Tests for model resolution and conditional LiteLLM wrapping."""

    @pytest.mark.parametrize(
        "model_string",
        [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
            "model-optimizer-abc123",
            "model-optimizer-exp-001",
            "projects/my-project/locations/us-central1/endpoints/12345",
            "projects/p/locations/l/publishers/google/models/gemini-pro",
            "projects/test-proj/locations/europe-west1/publishers/google/models/gemini-2.0-flash",
        ],
        ids=[
            "gemini_flash_2.5",
            "gemini_flash_2.0",
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
