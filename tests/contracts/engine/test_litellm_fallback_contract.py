"""Contract tests for LiteLLM fallback behavior (US3).

NOTE: Nothing Escapes Virtue; Excellence Requires Thoughtful, Honest Engineering
"""

import pytest

from gepa_adk.engine.proposer import AsyncReflectiveMutationProposer


def test_adk_reflection_fn_none_is_valid() -> None:
    """Test that adk_reflection_fn=None is a valid initialization."""
    # Arrange & Act
    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
        adk_reflection_fn=None,  # Explicit None
    )

    # Assert
    assert proposer.adk_reflection_fn is None


def test_adk_reflection_fn_omitted_defaults_to_none() -> None:
    """Test that omitting adk_reflection_fn defaults to None."""
    # Arrange & Act
    proposer = AsyncReflectiveMutationProposer(
        model="gpt-4",
    )

    # Assert: Should default to None
    assert proposer.adk_reflection_fn is None


def test_backwards_compatible_constructor_signature() -> None:
    """Test that existing code without adk_reflection_fn still works."""
    # Arrange & Act: Old-style constructor call (no adk_reflection_fn)
    proposer = AsyncReflectiveMutationProposer(
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=500,
    )

    # Assert: Should initialize successfully
    assert proposer.model == "gpt-3.5-turbo"
    assert proposer.adk_reflection_fn is None
