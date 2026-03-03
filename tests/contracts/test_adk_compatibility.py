"""ADK import compatibility contract tests.

Verifies that all google-adk and google-genai import paths used by
gepa-adk are available in the installed ADK version. Catches import-path
renames and removals across ADK versions immediately on CI.

Attributes:
    pytestmark: Contract-level test marker.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.contract


class TestADKAgentImports:
    """Verify all ADK agent types used by gepa-adk are importable."""

    def test_llm_agent_importable(self) -> None:
        """LlmAgent is the primary building block for LLM-backed agents."""
        from google.adk.agents import LlmAgent  # noqa: F401

    def test_base_agent_importable(self) -> None:
        """BaseAgent is used for custom non-LLM agents."""
        from google.adk.agents import BaseAgent  # noqa: F401

    def test_sequential_agent_importable(self) -> None:
        """SequentialAgent orchestrates agents in sequence."""
        from google.adk.agents import SequentialAgent  # noqa: F401

    def test_loop_agent_importable(self) -> None:
        """LoopAgent orchestrates agents in a loop."""
        from google.adk.agents import LoopAgent  # noqa: F401

    def test_parallel_agent_importable(self) -> None:
        """ParallelAgent orchestrates agents in parallel."""
        from google.adk.agents import ParallelAgent  # noqa: F401


class TestADKSessionImports:
    """Verify all ADK session types used by gepa-adk are importable."""

    def test_base_session_service_importable(self) -> None:
        """BaseSessionService is the abstract session service interface."""
        from google.adk.sessions import BaseSessionService  # noqa: F401

    def test_in_memory_session_service_importable(self) -> None:
        """InMemorySessionService is the default session store."""
        from google.adk.sessions import InMemorySessionService  # noqa: F401

    def test_session_importable(self) -> None:
        """Session is the ADK session data type."""
        from google.adk.sessions import Session  # noqa: F401


class TestADKRunnerImports:
    """Verify ADK Runner is importable."""

    def test_runner_importable(self) -> None:
        """Runner executes agents within sessions."""
        from google.adk.runners import Runner  # noqa: F401


class TestADKModelImports:
    """Verify ADK model types used by gepa-adk are importable."""

    def test_base_llm_importable(self) -> None:
        """BaseLlm is the abstract LLM interface."""
        from google.adk.models.base_llm import BaseLlm  # noqa: F401

    def test_lite_llm_importable(self) -> None:
        """LiteLlm provides multi-provider LLM support via LiteLLM."""
        from google.adk.models.lite_llm import LiteLlm  # noqa: F401


class TestADKToolImports:
    """Verify ADK tool types used by gepa-adk are importable."""

    def test_function_tool_importable(self) -> None:
        """FunctionTool wraps Python callables as ADK tools."""
        from google.adk.tools import FunctionTool  # noqa: F401


class TestADKAppImports:
    """Verify ADK App type used by gepa-adk is importable."""

    def test_app_importable(self) -> None:
        """App is the ADK application entry point."""
        from google.adk.apps.app import App  # noqa: F401


class TestGenAITypeImports:
    """Verify google-genai types used by gepa-adk are importable."""

    def test_content_importable(self) -> None:
        """Content is the ADK message container type."""
        from google.genai.types import Content  # noqa: F401

    def test_part_importable(self) -> None:
        """Part is the ADK message part type."""
        from google.genai.types import Part  # noqa: F401

    def test_generate_content_config_importable(self) -> None:
        """GenerateContentConfig is used for model configuration."""
        from google.genai.types import GenerateContentConfig  # noqa: F401


__all__: list[str] = []
