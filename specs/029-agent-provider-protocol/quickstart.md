# Quickstart: AgentProvider Protocol

**Date**: 2026-01-15
**Feature**: 029-agent-provider-protocol

## Overview

The `AgentProvider` protocol enables custom agent loading and persistence for gepa-adk. This guide shows how to implement a provider and integrate it with the evolution system.

## Installation

No additional dependencies required. The protocol uses only:
- `typing.Protocol` (stdlib)
- `google.adk.agents.LlmAgent` (existing dependency)

## Quick Example

### 1. Implement the Protocol

```python
from google.adk.agents import LlmAgent
from gepa_adk.ports import AgentProvider


class InMemoryAgentProvider:
    """Simple in-memory agent provider for testing."""

    def __init__(self):
        self._agents: dict[str, LlmAgent] = {}

    def register(self, agent: LlmAgent) -> None:
        """Register an agent (helper method, not part of protocol)."""
        self._agents[agent.name] = agent

    def get_agent(self, name: str) -> LlmAgent:
        """Load an agent by name."""
        if not name:
            raise ValueError("Agent name cannot be empty")
        if name not in self._agents:
            raise KeyError(f"Agent not found: {name}")
        return self._agents[name]

    def save_instruction(self, name: str, instruction: str) -> None:
        """Persist an evolved instruction."""
        if not name:
            raise ValueError("Agent name cannot be empty")
        if name not in self._agents:
            raise KeyError(f"Agent not found: {name}")
        # Note: LlmAgent.instruction can be reassigned
        self._agents[name].instruction = instruction

    def list_agents(self) -> list[str]:
        """List available agent names."""
        return list(self._agents.keys())


# Verify protocol compliance
assert isinstance(InMemoryAgentProvider(), AgentProvider)
```

### 2. Use with Evolution System

```python
from gepa_adk.ports import AgentProvider

def evolve_agent(provider: AgentProvider, agent_name: str) -> str:
    # Load the agent
    agent = provider.get_agent(agent_name)

    # Get current instruction
    current = agent.instruction

    # ... perform evolution logic ...
    evolved = f"{current}\n\nIMPROVED: Be more concise."

    # Persist the evolved instruction
    provider.save_instruction(agent_name, evolved)

    return evolved
```

### 3. File-Based Provider (Example)

```python
from pathlib import Path
import yaml
from google.adk.agents import LlmAgent


class FileAgentProvider:
    """YAML file-based agent provider."""

    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir

    def get_agent(self, name: str) -> LlmAgent:
        if not name:
            raise ValueError("Agent name cannot be empty")
        config_path = self.agents_dir / f"{name}.yaml"
        if not config_path.exists():
            raise KeyError(f"Agent not found: {name}")

        config = yaml.safe_load(config_path.read_text())
        return LlmAgent(
            name=name,
            instruction=config.get("instruction", ""),
            model=config.get("model", "gemini-2.5-flash"),
            description=config.get("description", ""),
        )

    def save_instruction(self, name: str, instruction: str) -> None:
        if not name:
            raise ValueError("Agent name cannot be empty")
        config_path = self.agents_dir / f"{name}.yaml"
        if not config_path.exists():
            raise KeyError(f"Agent not found: {name}")

        config = yaml.safe_load(config_path.read_text())
        config["instruction"] = instruction
        config_path.write_text(yaml.dump(config, default_flow_style=False))

    def list_agents(self) -> list[str]:
        return [p.stem for p in self.agents_dir.glob("*.yaml")]
```

## Common Patterns

### Discovery and Iteration

```python
def process_all_agents(provider: AgentProvider):
    """Process all agents in the provider."""
    for name in provider.list_agents():
        agent = provider.get_agent(name)
        print(f"Agent: {name}")
        print(f"  Instruction: {agent.instruction[:50]}...")
```

### Error Handling

```python
def safe_get_agent(provider: AgentProvider, name: str) -> LlmAgent | None:
    """Safely get an agent, returning None if not found."""
    try:
        return provider.get_agent(name)
    except KeyError:
        return None
```

### Type Checking at Runtime

```python
def validate_provider(obj: object) -> bool:
    """Check if an object satisfies the AgentProvider protocol."""
    from gepa_adk.ports import AgentProvider
    return isinstance(obj, AgentProvider)
```

## Testing Your Implementation

```python
import pytest
from gepa_adk.ports import AgentProvider


class TestMyProvider:
    """Contract tests for custom provider."""

    def test_protocol_compliance(self):
        provider = MyAgentProvider()
        assert isinstance(provider, AgentProvider)

    def test_get_agent_returns_llm_agent(self):
        provider = MyAgentProvider()
        # ... setup ...
        agent = provider.get_agent("test_agent")
        assert hasattr(agent, "instruction")

    def test_save_instruction_persists(self):
        provider = MyAgentProvider()
        # ... setup ...
        provider.save_instruction("test_agent", "New instruction")
        agent = provider.get_agent("test_agent")
        assert agent.instruction == "New instruction"

    def test_list_agents_returns_list(self):
        provider = MyAgentProvider()
        names = provider.list_agents()
        assert isinstance(names, list)
```

## Next Steps

1. Implement a provider for your storage backend
2. Register it with the evolution engine
3. Run `pytest tests/contracts/test_agent_provider_protocol.py` to verify compliance
