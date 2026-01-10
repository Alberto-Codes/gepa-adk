"""Async evolution engine for gepa-adk.

This module provides the AsyncGEPAEngine class that orchestrates the
core evolution loop for optimizing agent instructions using the GEPA
algorithm with async support.

Attributes:
    AsyncGEPAEngine: Main evolution engine class.

Examples:
    Basic usage:

    ```python
    from gepa_adk.engine import AsyncGEPAEngine
    from gepa_adk.domain.models import EvolutionConfig, Candidate

    engine = AsyncGEPAEngine(
        adapter=my_adapter,
        config=EvolutionConfig(max_iterations=50),
        initial_candidate=Candidate(components={"instruction": "Be helpful"}),
        batch=training_data,
    )
    result = await engine.run()
    ```

See Also:
    - `gepa_adk.ports.adapter.AsyncGEPAAdapter`: Protocol for adapters.
    - `gepa_adk.domain.models`: Domain models used by the engine.
"""

from gepa_adk.engine.async_engine import AsyncGEPAEngine

__all__ = ["AsyncGEPAEngine"]
