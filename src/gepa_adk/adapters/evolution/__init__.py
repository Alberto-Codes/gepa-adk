"""Core adapter implementations for GEPA evolution.

Contains the single-agent ADKAdapter and multi-agent MultiAgentAdapter that
implement the AsyncGEPAAdapter protocol for Google ADK agents.

Anticipated growth: adapter variants for specific evolution strategies,
co-evolutionary adapters.

Attributes:
    ADKAdapter: Single-agent adapter for Google ADK agents.
    MultiAgentAdapter: Multi-agent adapter for workflow-level evolution.

Examples:
    Create an adapter for a single ADK agent:

    ```python
    from gepa_adk.adapters.evolution import ADKAdapter

    adapter = ADKAdapter(agent=my_agent, scorer=my_scorer)
    ```

    Create an adapter for a multi-agent workflow:

    ```python
    from gepa_adk.adapters.evolution import MultiAgentAdapter

    adapter = MultiAgentAdapter(workflow=my_workflow, scorer=my_scorer)
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.ports.adapter`][gepa_adk.ports.adapter]: AsyncGEPAAdapter protocol that
        adapters implement.
    - [`gepa_adk.adapters.execution`][gepa_adk.adapters.execution]: Agent execution
        infrastructure used by adapters.
    - [`gepa_adk.adapters.components`][gepa_adk.adapters.components]: Component handlers
        for evolvable surfaces.
"""

from gepa_adk.adapters.evolution.adk_adapter import ADKAdapter
from gepa_adk.adapters.evolution.multi_agent import MultiAgentAdapter

__all__ = [
    "ADKAdapter",
    "MultiAgentAdapter",
]
