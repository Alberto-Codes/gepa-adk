# Extending Agent Providers

This guide explains how to implement custom agent persistence by creating an `AgentProvider`.

!!! tip "When to Use"
    Create a custom `AgentProvider` when you need to load and persist agents from a
    custom storage backend — for example, a database, file system, or remote registry.
    The evolution engine uses the provider to load agents and save evolved instructions.

## Protocol Definition

The `AgentProvider` protocol defines three methods:

```python
from gepa_adk import AgentProvider

class AgentProvider(Protocol):
    def get_agent(self, name: str) -> LlmAgent:
        """Load an agent by its unique name."""
        ...

    def save_instruction(self, name: str, instruction: str) -> None:
        """Persist an evolved instruction for a named agent."""
        ...

    def list_agents(self) -> list[str]:
        """List all available agent names."""
        ...
```

!!! note "Error Contracts"
    - `get_agent()` raises `KeyError` for unknown names, `ValueError` for empty/invalid names.
    - `save_instruction()` raises `KeyError` for unknown names, `ValueError` for empty/invalid names, `IOError` for persistence failures.
    - `list_agents()` returns an empty list when no agents are available.

## Step-by-Step Implementation

Here is a `JsonFileAgentProvider` that reads and writes agent configurations from JSON files:

```python
import json
from pathlib import Path

from google.adk.agents import LlmAgent

from gepa_adk import AgentProvider  # verify structural subtyping


class JsonFileAgentProvider:
    """Agent provider backed by JSON files on disk."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def _agent_path(self, name: str) -> Path:
        return self._directory / f"{name}.json"

    def get_agent(self, name: str) -> LlmAgent:
        if not name:
            raise ValueError("Agent name cannot be empty")
        path = self._agent_path(name)
        if not path.exists():
            raise KeyError(f"Agent not found: {name}")
        try:
            data = json.loads(path.read_text())
        except OSError as e:
            raise IOError(f"Failed to read agent file: {path}") from e
        return LlmAgent(
            name=data["name"],
            model=data["model"],
            instruction=data.get("instruction", ""),
        )

    def save_instruction(self, name: str, instruction: str) -> None:
        if not name:
            raise ValueError("Agent name cannot be empty")
        path = self._agent_path(name)
        if not path.exists():
            raise KeyError(f"Agent not found: {name}")
        try:
            data = json.loads(path.read_text())
            data["instruction"] = instruction
            path.write_text(json.dumps(data, indent=2))
        except OSError as e:
            raise IOError(f"Failed to save instruction: {path}") from e

    def list_agents(self) -> list[str]:
        return [p.stem for p in self._directory.glob("*.json")]
```

Note that `JsonFileAgentProvider` is a **plain class** — it does not inherit from `AgentProvider`.
gepa-adk uses structural subtyping (ADR-002): any class with matching method signatures
satisfies the protocol automatically.

## Registration / Injection

Unlike `ComponentHandler` (which uses a registry), `AgentProvider` is injected directly
into the evolution engine or your orchestration code:

```python
from pathlib import Path

provider = JsonFileAgentProvider(Path("./agents"))
agent = provider.get_agent("my_assistant")
```

There is no global registry for agent providers — you pass the provider to wherever
it is needed.

## Runnable Example

This example demonstrates the full get_agent/save_instruction/list_agents cycle
without requiring an LLM API key:

```python
import json
import tempfile
from pathlib import Path

from google.adk.agents import LlmAgent

from gepa_adk import AgentProvider


class JsonFileAgentProvider:
    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def _agent_path(self, name: str) -> Path:
        return self._directory / f"{name}.json"

    def get_agent(self, name: str) -> LlmAgent:
        if not name:
            raise ValueError("Agent name cannot be empty")
        path = self._agent_path(name)
        if not path.exists():
            raise KeyError(f"Agent not found: {name}")
        data = json.loads(path.read_text())
        return LlmAgent(
            name=data["name"],
            model=data["model"],
            instruction=data.get("instruction", ""),
        )

    def save_instruction(self, name: str, instruction: str) -> None:
        if not name:
            raise ValueError("Agent name cannot be empty")
        path = self._agent_path(name)
        if not path.exists():
            raise KeyError(f"Agent not found: {name}")
        data = json.loads(path.read_text())
        data["instruction"] = instruction
        path.write_text(json.dumps(data, indent=2))

    def list_agents(self) -> list[str]:
        return [p.stem for p in self._directory.glob("*.json")]


# Verify protocol compliance
provider = JsonFileAgentProvider(Path(tempfile.mkdtemp()))
assert isinstance(provider, AgentProvider)

# Seed an agent config file
agent_data = {"name": "helper", "model": "gemini-2.5-flash", "instruction": "Be helpful"}
(provider._directory / "helper.json").write_text(json.dumps(agent_data))

# Demonstrate the full cycle
print(f"Available agents: {provider.list_agents()}")  # ["helper"]

agent = provider.get_agent("helper")
print(f"Instruction: {agent.instruction}")  # "Be helpful"

provider.save_instruction("helper", "Be concise and helpful")
updated = provider.get_agent("helper")
print(f"Updated: {updated.instruction}")  # "Be concise and helpful"
```

To integrate with `evolve()`, pass the provider to your orchestration code:

```python
from gepa_adk import EvolutionConfig, evolve, run_sync

provider = JsonFileAgentProvider(Path("./agents"))
agent = provider.get_agent("my_assistant")

config = EvolutionConfig(max_iterations=5)
result = run_sync(evolve(agent, trainset, config=config))

# Persist the evolved instruction
provider.save_instruction("my_assistant", result.best_instruction)
```

## Common Pitfalls

!!! warning "Avoid These Mistakes"
    **Missing validation on empty names.** Both `get_agent()` and `save_instruction()`
    must raise `ValueError` for empty or `None` names. This is part of the protocol
    contract — callers expect consistent error behavior.

    **Not persisting before returning.** `save_instruction()` must fully persist the
    instruction before returning. If a subsequent `get_agent()` call does not reflect
    the saved instruction, the evolution engine may use stale data.

    **Ignoring IOError handling.** File and network operations can fail. Wrap I/O in
    try/except and raise `IOError` with a descriptive message so callers can distinguish
    persistence failures from missing-agent errors.

    **Inheriting from the Protocol.** Do NOT write `class MyProvider(AgentProvider):`.
    gepa-adk uses structural subtyping (ADR-002) — just implement the methods with
    matching signatures. Inheriting from a Protocol is misleading and unnecessary.

## Contract Test Skeleton

When adding a new provider, write contract tests to verify protocol compliance. This skeleton
follows the three-class template established in the project.

!!! note "Exemplar Reference"
    This skeleton follows the pattern in `tests/contracts/test_agent_provider_protocol.py`
    — always check the latest exemplar before starting.

```python
import pytest
from google.adk.agents import LlmAgent

from gepa_adk import AgentProvider

pytestmark = pytest.mark.contract


class TestMyProviderRuntimeCheckable:
    """Positive compliance: isinstance checks."""

    def test_satisfies_agent_provider_protocol(self):
        provider = MyProvider()
        assert isinstance(provider, AgentProvider)

    def test_protocol_has_required_methods(self):
        provider = MyProvider()
        assert hasattr(provider, "get_agent")
        assert hasattr(provider, "save_instruction")
        assert hasattr(provider, "list_agents")


class TestMyProviderBehavior:
    """Behavioral expectations: return types, error contracts."""

    def test_get_agent_returns_llm_agent(self):
        provider = MyProvider()
        # ... register a test agent ...
        agent = provider.get_agent("test_agent")
        assert isinstance(agent, LlmAgent)

    def test_get_agent_raises_key_error_for_unknown(self):
        provider = MyProvider()
        with pytest.raises(KeyError):
            provider.get_agent("nonexistent")

    def test_get_agent_raises_value_error_for_empty(self):
        provider = MyProvider()
        with pytest.raises(ValueError):
            provider.get_agent("")

    def test_save_instruction_persists(self):
        provider = MyProvider()
        # ... register a test agent ...
        provider.save_instruction("test_agent", "New instruction")
        agent = provider.get_agent("test_agent")
        assert agent.instruction == "New instruction"

    def test_list_agents_returns_list_of_strings(self):
        provider = MyProvider()
        result = provider.list_agents()
        assert isinstance(result, list)
        assert all(isinstance(n, str) for n in result)

    def test_list_agents_empty_when_no_agents(self):
        provider = MyProvider()
        assert provider.list_agents() == []


class TestMyProviderNonCompliance:
    """Negative cases: missing methods fail isinstance."""

    def test_missing_save_instruction_fails(self):
        class Incomplete:
            def get_agent(self, name):
                raise NotImplementedError

            def list_agents(self):
                return []

        assert not isinstance(Incomplete(), AgentProvider)

    def test_missing_list_agents_fails(self):
        class Incomplete:
            def get_agent(self, name):
                raise NotImplementedError

            def save_instruction(self, name, instruction):
                pass

        assert not isinstance(Incomplete(), AgentProvider)

    def test_missing_get_agent_fails(self):
        class Incomplete:
            def save_instruction(self, name, instruction):
                pass

            def list_agents(self):
                return []

        assert not isinstance(Incomplete(), AgentProvider)
```

## API Reference

- [`AgentProvider`][gepa_adk.ports.agent_provider.AgentProvider] — Protocol definition
