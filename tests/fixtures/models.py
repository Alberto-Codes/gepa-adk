"""Canonical Gemini model identifiers for the test suite.

Every test that sends a request to a live Gemini model — and the
``requires_gemini`` availability probe in ``tests/conftest.py`` — reads its
model name from :data:`GEMINI_TEST_MODEL` instead of hardcoding one. When
Google retires a generation, updating this module is the only edit needed to
keep the API-tier tests pointing at a live model.

:data:`DEPRECATED_GEMINI_PREFIXES` records the generations Google has
announced a shutdown date for, so a guard test can fail loudly if the
canonical model (or a default-model path in ``src``) ever resolves to one of
them. Add newly announced retirements there; the guard tests then flag
anything still pinned to them.

Examples:
    ```python
    from tests.fixtures.models import GEMINI_TEST_MODEL

    agent = LlmAgent(name="reflector", model=GEMINI_TEST_MODEL)
    ```

See Also:
    - `docs/reference/model-selection.md`: Which model identifiers each
      surface of the project uses, and the procedure to follow when Google
      announces a retirement.
    - `tests/conftest.py`: The ``requires_gemini`` availability probe that
      reads :data:`GEMINI_TEST_MODEL`.
    - `tests/unit/test_resolve_model_for_agent.py`: The guard tests that read
      :data:`DEPRECATED_GEMINI_PREFIXES`.
"""

from __future__ import annotations

#: Current-generation Gemini model used by every live-model test.
#:
#: The installed ``google-genai`` model literal
#: (``google/genai/_gaos/types/interactions/model.py``) is the catalog this
#: pin follows: it annotates ``gemini-3.8-flash`` as the newest Flash model and
#: ``gemini-3.6-flash`` as previous-generation. Prefer that catalog over the
#: deprecations page, whose replacement column lags behind it.
GEMINI_TEST_MODEL: str = "gemini-3.8-flash"

#: Prefixes of Gemini generations that are entirely retired or retiring. The
#: single deprecation rule: it covers every dated, suffixed, and preview
#: variant of a generation without enumerating them. Sourced from
#: https://ai.google.dev/gemini-api/docs/deprecations plus the Agent Platform
#: notice retiring the Gemini 2.5 GA family no earlier than 2026-10-16.
DEPRECATED_GEMINI_PREFIXES: tuple[str, ...] = (
    "gemini-1.0-",
    "gemini-1.5-",
    "gemini-2.0-",
    "gemini-2.5-",
    "gemini-live-2.5-",
)


def is_deprecated_gemini_model(model: str) -> bool:
    """Report whether a model identifier names a retired Gemini generation.

    Args:
        model: Model identifier to check. May carry a LiteLLM provider prefix
            (``gemini/gemini-2.5-flash``) or a Vertex AI publisher path.

    Returns:
        True when the identifier names a Gemini model with an announced
        shutdown date, False otherwise. Non-Gemini identifiers are never
        deprecated by this check.

    Examples:
        ```python
        is_deprecated_gemini_model("gemini-2.5-flash")
        # True

        is_deprecated_gemini_model("gemini-3.8-flash")
        # False

        is_deprecated_gemini_model("ollama_chat/gpt-oss:20b")
        # False
        ```
    """
    bare = model.rsplit("/", 1)[-1]
    return bare.startswith(DEPRECATED_GEMINI_PREFIXES)
