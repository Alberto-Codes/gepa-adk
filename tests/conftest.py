"""Root pytest configuration for gepa-adk tests.

This module provides shared fixtures and configuration for all tests.
It automatically loads environment variables from .env file.

Note:
    Environment variables are loaded at pytest startup to ensure
    integration tests have access to API keys and configuration.
"""

import warnings
from pathlib import Path
from typing import TextIO

import pytest
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
_env_file = _project_root / ".env"

if _env_file.exists():
    load_dotenv(_env_file)


def _suppress_pydantic_serializer_warnings() -> None:
    warnings.filterwarnings(
        "ignore",
        message="Pydantic serializer warnings:.*",
        category=UserWarning,
        module=r"pydantic\.main",
    )


_suppress_pydantic_serializer_warnings()

_original_showwarning = warnings.showwarning


def _filtered_showwarning(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: TextIO | None = None,
    line: str | None = None,
) -> None:
    if "Pydantic serializer warnings" in str(message):
        return
    return _original_showwarning(message, category, filename, lineno, file, line)


warnings.showwarning = _filtered_showwarning  # type: ignore[assignment]

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


def pytest_sessionfinish(session, exitstatus) -> None:
    """Re-apply warning filters before interpreter shutdown."""
    _suppress_pydantic_serializer_warnings()


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
