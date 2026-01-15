"""Contract tests for AgentProvider protocol compliance.

Note:
    These tests ensure implementations satisfy the AgentProvider protocol
    with correct method signatures, return types, and runtime checks.
"""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.ports.agent_provider import AgentProvider

pytestmark = pytest.mark.contract


class InMemoryAgentProvider:
    """Minimal agent provider implementation for contract testing.

    Note:
        Provides in-memory storage for agents to verify protocol compliance.
    """

    def __init__(self):
        """Initialize empty agent storage."""
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


class TestAgentProviderProtocol:
    """Contract tests for AgentProvider protocol compliance."""

    def test_agent_provider_protocol_is_runtime_checkable(self):
        """Verify @runtime_checkable decorator works for isinstance() checks."""
        provider = InMemoryAgentProvider()
        assert isinstance(provider, AgentProvider), (
            "InMemoryAgentProvider should satisfy AgentProvider protocol"
        )

    def test_get_agent_returns_llm_agent(self):
        """Verify get_agent() returns LlmAgent instance."""
        provider = InMemoryAgentProvider()
        agent = LlmAgent(
            name="test_agent",
            instruction="You are a helpful assistant.",
            model="gemini-2.0-flash",
        )
        provider.register(agent)

        result = provider.get_agent("test_agent")
        assert isinstance(result, LlmAgent), "get_agent() must return LlmAgent"
        assert result.name == "test_agent"
        assert result.instruction == "You are a helpful assistant."

    def test_get_agent_raises_for_nonexistent(self):
        """Verify get_agent() raises error for non-existent agents."""
        provider = InMemoryAgentProvider()

        with pytest.raises(KeyError, match="Agent not found"):
            provider.get_agent("nonexistent_agent")

    def test_get_agent_handles_multiple_agents(self):
        """Verify get_agent() can handle multiple sequential calls."""
        provider = InMemoryAgentProvider()

        agent1 = LlmAgent(
            name="agent1",
            instruction="First agent instruction.",
            model="gemini-2.0-flash",
        )
        agent2 = LlmAgent(
            name="agent2",
            instruction="Second agent instruction.",
            model="gemini-2.0-flash",
        )
        provider.register(agent1)
        provider.register(agent2)

        # Retrieve both agents
        retrieved1 = provider.get_agent("agent1")
        retrieved2 = provider.get_agent("agent2")

        assert retrieved1.name == "agent1"
        assert retrieved1.instruction == "First agent instruction."
        assert retrieved2.name == "agent2"
        assert retrieved2.instruction == "Second agent instruction."

        # Verify they are different instances
        assert retrieved1 is not retrieved2

    def test_save_instruction_persists(self):
        """Verify save_instruction() persists instruction successfully."""
        provider = InMemoryAgentProvider()
        agent = LlmAgent(
            name="test_agent",
            instruction="Original instruction.",
            model="gemini-2.0-flash",
        )
        provider.register(agent)

        new_instruction = "Updated instruction after evolution."
        provider.save_instruction("test_agent", new_instruction)

        # Verify instruction was updated
        updated_agent = provider.get_agent("test_agent")
        assert updated_agent.instruction == new_instruction

    def test_save_instruction_raises_for_nonexistent(self):
        """Verify save_instruction() raises error for non-existent agents."""
        provider = InMemoryAgentProvider()

        with pytest.raises(KeyError, match="Agent not found"):
            provider.save_instruction("nonexistent_agent", "Some instruction")

    def test_save_instruction_visible_in_subsequent_get(self):
        """Verify saved instruction is visible in subsequent get_agent() calls."""
        provider = InMemoryAgentProvider()
        agent = LlmAgent(
            name="test_agent",
            instruction="Initial instruction.",
            model="gemini-2.0-flash",
        )
        provider.register(agent)

        # Save new instruction
        evolved_instruction = "Evolved instruction with improvements."
        provider.save_instruction("test_agent", evolved_instruction)

        # Retrieve agent and verify instruction was persisted
        retrieved = provider.get_agent("test_agent")
        assert retrieved.instruction == evolved_instruction

    def test_list_agents_returns_list(self):
        """Verify list_agents() returns list[str] type."""
        provider = InMemoryAgentProvider()
        result = provider.list_agents()

        assert isinstance(result, list), "list_agents() must return a list"
        assert all(isinstance(name, str) for name in result), (
            "All elements must be strings"
        )

    def test_list_agents_empty_when_no_agents(self):
        """Verify list_agents() returns empty list when no agents registered."""
        provider = InMemoryAgentProvider()
        result = provider.list_agents()

        assert result == [], "Empty provider should return empty list"

    def test_list_agents_contains_all_registered(self):
        """Verify list_agents() contains all registered agent names."""
        provider = InMemoryAgentProvider()

        agent1 = LlmAgent(
            name="agent1",
            instruction="First agent.",
            model="gemini-2.0-flash",
        )
        agent2 = LlmAgent(
            name="agent2",
            instruction="Second agent.",
            model="gemini-2.0-flash",
        )
        agent3 = LlmAgent(
            name="agent3",
            instruction="Third agent.",
            model="gemini-2.0-flash",
        )

        provider.register(agent1)
        provider.register(agent2)
        provider.register(agent3)

        names = provider.list_agents()
        assert len(names) == 3, "Should return 3 agent names"
        assert "agent1" in names
        assert "agent2" in names
        assert "agent3" in names

    def test_protocol_requires_all_three_methods(self):
        """Verify class missing any method does not satisfy AgentProvider protocol."""

        # Class missing save_instruction()
        class IncompleteProvider1:
            def get_agent(self, name: str) -> LlmAgent:
                raise NotImplementedError

            def list_agents(self) -> list[str]:
                return []

        provider1 = IncompleteProvider1()
        assert not isinstance(provider1, AgentProvider), (
            "IncompleteProvider1 should NOT satisfy protocol (missing save_instruction)"
        )

        # Class missing list_agents()
        class IncompleteProvider2:
            def get_agent(self, name: str) -> LlmAgent:
                raise NotImplementedError

            def save_instruction(self, name: str, instruction: str) -> None:
                pass

        provider2 = IncompleteProvider2()
        assert not isinstance(provider2, AgentProvider), (
            "IncompleteProvider2 should NOT satisfy protocol (missing list_agents)"
        )

        # Class missing get_agent()
        class IncompleteProvider3:
            def save_instruction(self, name: str, instruction: str) -> None:
                pass

            def list_agents(self) -> list[str]:
                return []

        provider3 = IncompleteProvider3()
        assert not isinstance(provider3, AgentProvider), (
            "IncompleteProvider3 should NOT satisfy protocol (missing get_agent)"
        )

    def test_get_agent_with_empty_name(self):
        """Verify edge case: get_agent() with empty name raises ValueError."""
        provider = InMemoryAgentProvider()

        # Empty string should raise ValueError (per protocol docstring)
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            provider.get_agent("")

    def test_save_instruction_with_empty_name(self):
        """Verify edge case: save_instruction() with empty name raises ValueError."""
        provider = InMemoryAgentProvider()
        agent = LlmAgent(
            name="test_agent",
            instruction="Test instruction.",
            model="gemini-2.0-flash",
        )
        provider.register(agent)

        # Empty string should raise ValueError (per protocol docstring)
        with pytest.raises(ValueError, match="Agent name cannot be empty"):
            provider.save_instruction("", "Some instruction")
