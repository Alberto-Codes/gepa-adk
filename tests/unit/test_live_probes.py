"""Unit tests for the live-model availability probes in ``tests/conftest.py``.

A configured probe that raises must fail the pytest session instead of
silently skipping the live tier. An unconfigured probe must still skip,
without making any network call.

Examples:
    Run only these tests:

    ```bash
    uv run pytest tests/unit/test_live_probes.py -q
    ```

See Also:
    [`tests.conftest`][]: The probes and collection hook under test.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from _pytest.outcomes import Exit

from tests.conftest import (
    _get_ollama_models,
    _is_gemini_available,
    pytest_collection_modifyitems,
)

pytestmark = pytest.mark.unit

_GEMINI_ENV_VARS = (
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
)


class _Recorder:
    """Callable stand-in that records calls and optionally raises.

    Attributes:
        calls (list[tuple[tuple[Any, ...], dict[str, Any]]]): Arguments of
            every call.
        exc (BaseException | None): Exception raised on call, or None to
            return the recorder itself.

    Examples:
        ```python
        rec = _Recorder()
        rec(1, a=2)
        assert rec.calls == [((1,), {"a": 2})]
        ```
    """

    def __init__(self, exc: BaseException | None = None) -> None:
        """Store the exception to raise.

        Args:
            exc: Exception raised when called, or None.
        """
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.exc = exc

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Record the call, then raise or return self.

        Args:
            *args: Positional arguments to record.
            **kwargs: Keyword arguments to record.

        Returns:
            This recorder, when no exception is configured.

        Raises:
            BaseException: The configured exception, when one is set.
        """
        self.calls.append((args, kwargs))
        if self.exc is not None:
            raise self.exc
        return self


class _RaisingClient:
    """Fake ``google.genai.Client`` whose ``models.get`` raises.

    Attributes:
        models (SimpleNamespace): Stand-in for ``client.models``; its ``get``
            raises ``RuntimeError("boom")``.

    Examples:
        ```python
        client = _RaisingClient(http_options=None)
        client.models.get(model="m")  # raises RuntimeError("boom")
        ```
    """

    def __init__(self, **kwargs: Any) -> None:
        """Build the raising ``models`` stand-in.

        Args:
            **kwargs: Ignored client options.
        """
        self.models = SimpleNamespace(get=_Recorder(exc=RuntimeError("boom")))


def test_configured_gemini_probe_failure_exits_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured Gemini probe that raises calls ``pytest.exit``."""
    for name in _GEMINI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setattr("google.genai.Client", _RaisingClient)

    with pytest.raises(Exit) as excinfo:
        _is_gemini_available()

    assert excinfo.value.returncode == 1
    assert "GEMINI_TEST_MODEL" in excinfo.value.msg
    assert "RuntimeError('boom')" in excinfo.value.msg


def test_unconfigured_gemini_probe_returns_false_without_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no Gemini credentials the probe skips and builds no client."""
    for name in _GEMINI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    client = _Recorder()
    monkeypatch.setattr("google.genai.Client", client)

    assert _is_gemini_available() is False
    assert client.calls == []


def test_configured_ollama_probe_failure_exits_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured Ollama probe that raises calls ``pytest.exit``."""
    monkeypatch.setenv("OLLAMA_API_BASE", "http://ollama.test:11434")
    urlopen = _Recorder(exc=OSError("down"))
    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    with pytest.raises(Exit) as excinfo:
        _get_ollama_models()

    assert excinfo.value.returncode == 1
    assert "http://ollama.test:11434/api/tags" in excinfo.value.msg
    assert "OSError('down')" in excinfo.value.msg
    assert len(urlopen.calls) == 1


def test_unconfigured_ollama_probe_returns_empty_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With ``OLLAMA_API_BASE`` unset the probe skips and opens no URL."""
    monkeypatch.delenv("OLLAMA_API_BASE", raising=False)
    urlopen = _Recorder(exc=OSError("must not be called"))
    monkeypatch.setattr("urllib.request.urlopen", urlopen)

    assert _get_ollama_models() == []
    assert urlopen.calls == []


def test_collection_hook_runs_after_marker_deselection() -> None:
    """The probe hook is ``trylast`` so ``-m`` deselection runs first."""
    impl = getattr(pytest_collection_modifyitems, "pytest_impl", None)

    assert impl is not None
    assert impl.get("trylast") is True
