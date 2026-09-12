"""Canonical Gemini model identifiers for the test suite.

Every test that sends a request to a live Gemini model — and the
``requires_gemini`` availability probe in ``tests/conftest.py`` — reads its
model name from :data:`GEMINI_TEST_MODEL` instead of hardcoding one. When
Google retires a generation, updating this module is the only edit needed to
keep the API-tier tests pointing at a live model.

:data:`DEPRECATED_GEMINI_MODELS` records the identifiers Google has announced
a shutdown date for, so a guard test can fail loudly if the canonical model
(or a default-model path in ``src``) ever resolves to one of them. Add newly
announced retirements here; the guard tests then flag anything still pinned
to them.

Note:
    ``GEPA_ADK_TEST_GEMINI_MODEL`` overrides the canonical model for a single
    run, which lets a maintainer verify a newer generation before committing
    the change.

Examples:
    ```python
    from tests.fixtures.models import GEMINI_TEST_MODEL

    agent = LlmAgent(name="reflector", model=GEMINI_TEST_MODEL)
    ```
"""

from __future__ import annotations

import os

#: Current-generation Gemini model used by every live-model test.
#:
#: ``gemini-3.6-flash`` is the GA replacement Google names for the retiring
#: ``gemini-2.x`` Flash line on https://ai.google.dev/gemini-api/docs/deprecations.
GEMINI_TEST_MODEL: str = os.environ.get(
    "GEPA_ADK_TEST_GEMINI_MODEL", "gemini-3.6-flash"
)

#: Gemini identifiers with an announced shutdown date, or that never named a
#: real published model. Sourced from
#: https://ai.google.dev/gemini-api/docs/deprecations plus the Agent Platform
#: notice retiring the Gemini 2.5 GA family no earlier than 2026-10-16.
DEPRECATED_GEMINI_MODELS: frozenset[str] = frozenset(
    {
        # Gemini 2.5 GA family — retiring no earlier than 2026-10-16.
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        # Gemini 2.5 previews and image variants with published shutdown dates.
        "gemini-2.5-flash-image",
        "gemini-2.5-flash-image-preview",
        "gemini-2.5-flash-lite-preview-09-2025",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-flash-preview-09-25",
        "gemini-2.5-pro-preview-03-25",
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.5-pro-preview-06-05",
        "gemini-live-2.5-flash-preview",
        # Gemini 2.0 family — shut down 2026-06-01 and earlier.
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash-lite-preview",
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.0-flash-live-001",
        "gemini-2.0-flash-preview-image-generation",
        # Gemini 1.x — retired well before the 2.x line.
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
    }
)

#: Prefixes of Gemini generations that are entirely retired or retiring. Used
#: to catch dated or suffixed variants that are not enumerated above.
DEPRECATED_GEMINI_PREFIXES: tuple[str, ...] = (
    "gemini-1.0-",
    "gemini-1.5-",
    "gemini-2.0-",
    "gemini-2.5-",
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

        is_deprecated_gemini_model("gemini-3.6-flash")
        # False

        is_deprecated_gemini_model("ollama_chat/gpt-oss:20b")
        # False
        ```
    """
    bare = model.rsplit("/", 1)[-1]
    if bare in DEPRECATED_GEMINI_MODELS:
        return True
    return bare.startswith(DEPRECATED_GEMINI_PREFIXES)
