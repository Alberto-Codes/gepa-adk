"""Root pytest configuration for gepa-adk tests.

This module provides shared fixtures and configuration for all tests.
It automatically loads environment variables from .env file.

Note:
    Environment variables are loaded at pytest startup to ensure
    integration tests have access to API keys and configuration.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
_env_file = _project_root / ".env"

if _env_file.exists():
    load_dotenv(_env_file)


def _get_ollama_models() -> list[str]:
    """Get list of available Ollama models via API.

    Returns:
        List of model names available on the Ollama server, or empty list if
        the server is unreachable or has no models.
    """
    import urllib.request

    api_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
    try:
        parsed = urlparse(api_base)
        host = parsed.hostname or "localhost"
        port = parsed.port or 11434
        url = f"http://{host}:{port}/api/tags"

        with urllib.request.urlopen(url, timeout=2) as response:
            import json

            data = json.loads(response.read().decode())
            return [model["name"] for model in data.get("models", [])]
    except Exception:
        return []


def _is_ollama_available() -> bool:
    """Check if Ollama service is reachable with at least one model."""
    return len(_get_ollama_models()) > 0


def _is_gemini_available() -> bool:
    """Check if Gemini API is available.

    Checks for either:
    1. Vertex AI configuration (GOOGLE_GENAI_USE_VERTEXAI + GOOGLE_CLOUD_PROJECT)
    2. API key configuration (GOOGLE_API_KEY or GEMINI_API_KEY)

    Note:
        This checks configuration only, not actual API connectivity.
        A full connectivity check would require making an API call.
    """
    # Check for Vertex AI configuration
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").upper() == "TRUE":
        if os.environ.get("GOOGLE_CLOUD_PROJECT"):
            return True

    # Check for API key configuration
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return True

    return False


# Cache the results at module load time
_OLLAMA_AVAILABLE = _is_ollama_available()
_GEMINI_AVAILABLE = _is_gemini_available()


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip tests marked with requires_ollama/requires_gemini if unavailable."""
    skip_ollama = pytest.mark.skip(
        reason="Ollama service not available or has no models"
    )
    skip_gemini = pytest.mark.skip(reason="Gemini API not configured")

    for item in items:
        # Check for requires_ollama marker (includes class-level markers)
        if item.get_closest_marker("requires_ollama") and not _OLLAMA_AVAILABLE:
            item.add_marker(skip_ollama)

        # Check for requires_gemini marker (includes class-level markers)
        if item.get_closest_marker("requires_gemini") and not _GEMINI_AVAILABLE:
            item.add_marker(skip_gemini)


try:
    import litellm

    # Avoid LiteLLM registering its default atexit async-client cleanup.
    #
    # LiteLLM uses the internal flag `_async_client_cleanup_registered` to ensure
    # its async HTTP client cleanup is only registered once via `atexit`. In this
    # test suite we perform deterministic cleanup in the `cleanup_litellm_clients`
    # session-scoped fixture below, which closes all cached async clients explicitly.
    #
    # Setting this internal flag to True prevents LiteLLM from installing an atexit
    # handler that might run after pytest has torn down its event loop, which has
    # previously resulted in noisy "coroutine was never awaited" warnings during
    # interpreter shutdown. At the time of writing there is no public LiteLLM API
    # for disabling this automatic registration, so we intentionally reach into this
    # private attribute in the test configuration only.
    litellm._async_client_cleanup_registered = True  # type: ignore[assignment]
except Exception:
    # LiteLLM may not be installed or importable in all environments.
    pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_litellm_clients():
    """Clean up LiteLLM async HTTP clients after all tests complete.

    This prevents 'coroutine never awaited' warnings from LiteLLM's
    async client cleanup at exit time.
    """
    yield  # Run all tests first

    # Clean up LiteLLM's cached async clients
    try:
        import asyncio

        from litellm.llms.custom_httpx.async_client_cleanup import (
            close_litellm_async_clients,
        )

        cleanup_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(cleanup_loop)
            cleanup_loop.run_until_complete(close_litellm_async_clients())
        finally:
            cleanup_loop.close()
            # Provide a fresh, open loop for LiteLLM atexit cleanup.
            asyncio.set_event_loop(asyncio.new_event_loop())
    except ImportError:
        # LiteLLM not installed or module structure changed
        pass
    except Exception:
        # Silently ignore cleanup errors - tests already passed
        pass


@pytest.fixture
def trainset_samples() -> list[dict[str, str]]:
    """Return a small trainset fixture for evolution tests.

    Note:
        Supports repeatable evolution setup across unit and integration tests.
    """
    return [
        {"input": "train-question-1", "expected": "train-answer-1"},
        {"input": "train-question-2", "expected": "train-answer-2"},
        {"input": "train-question-3", "expected": "train-answer-3"},
    ]


@pytest.fixture
def valset_samples() -> list[dict[str, str]]:
    """Return a small valset fixture for evolution tests.

    Note:
        Supports validation scoring paths with a distinct dataset.
    """
    return [
        {"input": "val-question-1", "expected": "val-answer-1"},
        {"input": "val-question-2", "expected": "val-answer-2"},
        {"input": "val-question-3", "expected": "val-answer-3"},
        {"input": "val-question-4", "expected": "val-answer-4"},
    ]


@pytest.fixture
def deterministic_scores() -> list[float]:
    """Return deterministic scores for acceptance scoring tests.

    Returns:
        List of scores: [0.1, 0.2, 0.3, 0.4, 0.5]

    Note:
        Supports testing sum vs mean aggregation with predictable results.
        Sum = 1.5, Mean = 0.3
    """
    return [0.1, 0.2, 0.3, 0.4, 0.5]


@pytest.fixture
def deterministic_score_batch() -> list[float]:
    """Return a batch of deterministic scores for iteration evaluation.

    Returns:
        List of scores: [0.6, 0.7, 0.8]

    Note:
        Supports testing acceptance aggregation on iteration batches.
        Sum = 2.1, Mean ≈ 0.7
    """
    return [0.6, 0.7, 0.8]
