# AgentProvider Protocol Contract

**Version**: 1.0.0
**Date**: 2026-01-15

## Protocol Definition

```python
from typing import Protocol, runtime_checkable, TYPE_CHECKING

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

    Note:
        Use @runtime_checkable to enable isinstance() checks.
        Implementations must provide all three methods.
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
            The returned agent should be fully configured and ready
            for use with the evolution system.
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
                "my_agent",
                "You are a helpful assistant specialized in coding."
            )
            ```

        Note:
            After calling this method, subsequent calls to get_agent()
            should return an agent with the updated instruction.
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
            The order of returned names is not guaranteed.
            Implementations may return names in any order.
        """
        ...
```

## Contract Tests

The protocol compliance is verified by contract tests that check:

1. **Protocol Compliance**:
   - Implementation satisfies `isinstance(impl, AgentProvider)`
   - All three methods exist and are callable

2. **get_agent() Behavior**:
   - Returns `LlmAgent` for valid names
   - Raises error for non-existent agents
   - Handles multiple sequential calls

3. **save_instruction() Behavior**:
   - Persists instruction successfully
   - Raises error for non-existent agents
   - Updated instruction visible in subsequent get_agent() calls

4. **list_agents() Behavior**:
   - Returns list[str] type
   - Returns empty list when no agents
   - Contains all registered agent names

## Implementation Requirements

| Requirement | Description |
|-------------|-------------|
| Runtime Checkable | Must satisfy `isinstance(impl, AgentProvider)` |
| Type Hints | Must accept and return specified types |
| Error Handling | Must raise errors for invalid inputs |
| Idempotency | `list_agents()` must be idempotent |
| Consistency | `save_instruction()` must be immediately visible |

## Usage Patterns

### Basic Usage

```python
from gepa_adk.ports import AgentProvider

def run_evolution(provider: AgentProvider, agent_name: str):
    # Load agent
    agent = provider.get_agent(agent_name)

    # ... perform evolution ...
    new_instruction = evolve(agent.instruction)

    # Persist result
    provider.save_instruction(agent_name, new_instruction)
```

### Discovery Pattern

```python
def list_and_load(provider: AgentProvider):
    agents = {}
    for name in provider.list_agents():
        agents[name] = provider.get_agent(name)
    return agents
```

### Type Checking

```python
def validate_provider(obj: object) -> bool:
    return isinstance(obj, AgentProvider)
```
