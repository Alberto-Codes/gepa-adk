"""Utility functions for trajectory extraction and processing.

This module provides utilities for extracting, redacting, and truncating
trajectory data from ADK agent execution events.

Note:
    Utilities in this module are infrastructure concerns, not domain logic.
    They consume domain models but don't define them.
"""

from gepa_adk.utils.events import extract_trajectory

__all__ = ["extract_trajectory"]
