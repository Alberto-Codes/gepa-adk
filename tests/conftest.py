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


class MockScorer:
    """Reusable mock scorer for testing.

    Properly implements the Scorer protocol with the correct signature:
    - score(input_text, output, expected) -> tuple[float, dict]
    - async_score(input_text, output, expected) -> tuple[float, dict]

    Attributes:
        score_value: The fixed score value to return (default 0.8)
        score_calls: List of (input_text, output, expected) call records

    Example:
        >>> scorer = MockScorer(score_value=0.9)
        >>> score, metadata = scorer.score("input", "output", "expected")
        >>> assert score == 0.9
        >>> assert scorer.score_calls == [("input", "output", "expected")]

    Note:
        This class consolidates ~9 duplicate MockScorer implementations
        across the test suite into a single source of truth.
    """

    def __init__(self, score_value: float = 0.8) -> None:
        """Initialize mock scorer with fixed score value.

        Args:
            score_value: The score to return from all scoring calls.
        """
        self.score_value = score_value
        self.score_calls: list[tuple[str, str, str | None]] = []

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict]:
        """Record call and return fixed score with empty metadata.

        Args:
            input_text: The input query text
            output: The agent's generated output
            expected: The expected output (optional)

        Returns:
            Tuple of (score_value, empty_dict)
        """
        self.score_calls.append((input_text, output, expected))
        return (self.score_value, {})

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict]:
        """Record call and return fixed score with empty metadata.

        Args:
            input_text: The input query text
            output: The agent's generated output
            expected: The expected output (optional)

        Returns:
            Tuple of (score_value, empty_dict)
        """
        self.score_calls.append((input_text, output, expected))
        return (self.score_value, {})


@pytest.fixture
def mock_scorer_factory():
    """Factory fixture for creating MockScorer instances.

    Returns a callable that creates MockScorer instances with custom score values.

    Returns:
        Callable that creates MockScorer instances

    Example:
        def test_something(mock_scorer_factory):
            scorer = mock_scorer_factory(0.9)  # Custom score
            scorer_default = mock_scorer_factory()  # Uses default 0.8
    """

    def _make_scorer(score_value: float = 0.8) -> MockScorer:
        return MockScorer(score_value)

    return _make_scorer


@pytest.fixture
def mock_proposer(mocker):
    """Create a mock AsyncReflectiveMutationProposer for testing.

    Returns a MagicMock configured as an AsyncMock for the propose method.

    Returns:
        MagicMock with propose as AsyncMock

    Note:
        Used by tests that need to verify proposer delegation behavior.
    """
    mock = mocker.MagicMock()
    mock.propose = mocker.AsyncMock(return_value={})
    return mock


class MockExecutor:
    """Mock executor for contract testing.

    Mock implementation of AgentExecutorProtocol for testing multi-agent
    execution paths without requiring real ADK agents or session services.

    Attributes:
        execute_count: Number of times execute_agent was called
        calls: List of dicts containing all execute_agent call parameters

    Note:
        Tracks all execute_agent calls for verification in tests.
    """

    def __init__(self):
        """Set the mock executor state to empty and zero.

        Initializes execute_count to 0 and calls to an empty list.
        """
        self.execute_count = 0
        self.calls: list[dict] = []

    async def execute_agent(
        self,
        agent,
        input_text: str,
        **kwargs,
    ):
        """Mock execution of an agent that records the call and returns success.

        Increments the execute_count, records all parameters in calls list, and
        returns a successful ExecutionResult with mock values.

        Args:
            agent: The agent to execute (recorded but not used)
            input_text: Input text for the agent
            **kwargs: Additional keyword arguments (all recorded)

        Returns:
            ExecutionResult with SUCCESS status and mock values

        Note:
            Always succeeds with extracted_value="mock output". Override this method
            or use a different mock if you need failure scenarios.
        """
        from gepa_adk.ports.agent_executor import ExecutionResult, ExecutionStatus

        self.execute_count += 1
        self.calls.append(
            {
                "agent": agent,
                "input_text": input_text,
                **kwargs,
            }
        )
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            session_id="mock_session",
            extracted_value="mock output",
        )


@pytest.fixture
def mock_executor():
    """Return a fresh MockExecutor instance for each test.

    Returns:
        MockExecutor: A new mock executor with no recorded calls

    Note:
        Provides isolation between tests by returning a new instance each time.
    """
    return MockExecutor()
