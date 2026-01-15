"""Protocol definition for agent loading and persistence.

This module defines the AgentProvider protocol that enables custom agent
loading and persistence for gepa-adk. Implementations provide agent configuration
storage and retrieval, enabling the evolution system to load agents and persist
evolved instructions.

Attributes:
    AgentProvider (protocol): Protocol for loading and persisting agents.

Examples:
    Implement a minimal in-memory provider:

    ```python
    from google.adk.agents import LlmAgent
    from gepa_adk.ports import AgentProvider


    class InMemoryProvider:
        def __init__(self):
            self._agents = {}

        def get_agent(self, name: str) -> LlmAgent:
            if name not in self._agents:
                raise KeyError(f"Agent not found: {name}")
            return self._agents[name]

        def save_instruction(self, name: str, instruction: str) -> None:
            if name not in self._agents:
                raise KeyError(f"Agent not found: {name}")
            self._agents[name].instruction = instruction

        def list_agents(self) -> list[str]:
            return list(self._agents.keys())
    ```

    Use the provider:

    ```python
    provider = InMemoryProvider()
    agent = provider.get_agent("my_agent")
    provider.save_instruction("my_agent", "New instruction")
    ```

Note:
    The protocol uses sync methods for simplicity. Implementations that need
    async can use async internally and block in sync methods, or provide
    async wrappers. The protocol itself does not perform I/O; implementations
    handle storage operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from google.adk.agents import LlmAgent


@runtime_checkable
class AgentProvider(Protocol):
    """Protocol for loading and persisting agents.

    Implementations provide agent configuration storage and retrieval,
    enabling the evolution system to load agents and persist evolved
    instructions.

    Examples:
        Implement a minimal in-memory provider:

        ```python
        class InMemoryProvider:
            def __init__(self):
                self._agents = {}

            def get_agent(self, name: str) -> LlmAgent:
                if name not in self._agents:
                    raise KeyError(f"Agent not found: {name}")
                return self._agents[name]

            def save_instruction(self, name: str, instruction: str) -> None:
                if name not in self._agents:
                    raise KeyError(f"Agent not found: {name}")
                self._agents[name].instruction = instruction

            def list_agents(self) -> list[str]:
                return list(self._agents.keys())
        ```

        Verify protocol compliance:

        ```python
        from gepa_adk.ports import AgentProvider

        provider = InMemoryProvider()
        assert isinstance(provider, AgentProvider)  # Runtime check works
        ```

    Note:
        All implementations must provide get_agent(), save_instruction(),
        and list_agents() methods. Use @runtime_checkable to enable
        isinstance() checks for protocol compliance.
    """

    def get_agent(self, name: str) -> "LlmAgent":
        """Load an agent by its unique name.

        Args:
            name: The unique identifier for the agent.

        Returns:
            The configured LlmAgent instance ready for use.

        Raises:
            KeyError: If no agent with the given name exists.
            ValueError: If name is empty or invalid.

        Examples:
            Load a named agent:

            ```python
            provider = MyAgentProvider()
            agent = provider.get_agent("my_agent")
            print(agent.instruction)
            ```

        Note:
            Only fully configured agents ready for use with the evolution
            system should be returned.
        """
        ...

    def save_instruction(self, name: str, instruction: str) -> None:
        """Persist an evolved instruction for a named agent.

        Args:
            name: The unique identifier for the agent.
            instruction: The new instruction text to persist.

        Raises:
            KeyError: If no agent with the given name exists.
            ValueError: If name is empty or invalid.
            IOError: If persistence fails (implementation-specific).

        Examples:
            Save an evolved instruction:

            ```python
            provider.save_instruction(
                "my_agent", "You are a helpful assistant specialized in coding."
            )
            ```

        Note:
            Only after successful persistence should subsequent calls to
            get_agent() return an agent with the updated instruction.
        """
        ...

    def list_agents(self) -> list[str]:
        """List all available agent names.

        Returns:
            A list of agent name strings. Empty list if no agents.

        Examples:
            Discover available agents:

            ```python
            provider = MyAgentProvider()
            for name in provider.list_agents():
                print(f"Found agent: {name}")
            ```

        Note:
            Only the list of agent names is guaranteed; the order of
            returned names is not guaranteed and implementations may
            return names in any order.
        """
        ...
