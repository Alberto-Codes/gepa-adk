"""Acceptance tests for the root export of the Scorer protocol.

``from gepa_adk import Scorer`` must work, ``Scorer`` must be listed in
``gepa_adk.__all__``, and the deep path ``gepa_adk.ports.Scorer`` must keep
working and refer to the same object.
"""

from __future__ import annotations

import pytest

import gepa_adk
from gepa_adk import Scorer
from gepa_adk.ports import Scorer as PortsScorer
from tests.conftest import MockScorer

pytestmark = pytest.mark.unit


class TestScorerRootExport:
    """Scorer is reachable from the package root."""

    def test_scorer_is_in_all(self) -> None:
        """The root __all__ lists Scorer."""
        assert "Scorer" in gepa_adk.__all__

    def test_root_and_ports_paths_are_the_same_object(self) -> None:
        """Both import paths resolve to one protocol class."""
        assert Scorer is PortsScorer

    def test_root_scorer_is_runtime_checkable(self) -> None:
        """The runtime check works through the root import."""
        assert isinstance(MockScorer(), Scorer)
        assert not isinstance(object(), Scorer)
