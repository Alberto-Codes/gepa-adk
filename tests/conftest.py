"""Root pytest configuration for gepa-adk tests.

This module provides shared fixtures and configuration for all tests.
It automatically loads environment variables from .env file.

Note:
    Environment variables are loaded at pytest startup to ensure
    integration tests have access to API keys and configuration.
"""

import warnings
from pathlib import Path

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


def _filtered_showwarning(message, category, filename, lineno, file=None, line=None):
    if "Pydantic serializer warnings" in str(message):
        return
    return _original_showwarning(message, category, filename, lineno, file, line)


warnings.showwarning = _filtered_showwarning

try:
    import litellm

    # Avoid LiteLLM registering its atexit cleanup (we manage cleanup here).
    setattr(litellm, "_async_client_cleanup_registered", True)
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
