# API Contract: evolve_group()

**Feature**: 014-multi-agent-coevolution  
**Date**: January 11, 2026  
**Status**: Draft

## Overview

This contract defines the public API for multi-agent co-evolution.

---

## Function Signature

```python
async def evolve_group(
    agents: list[LlmAgent],
    primary: str,
    trainset: list[dict[str, Any]],
    critic: LlmAgent | None = None,
    share_session: bool = True,
    config: EvolutionConfig | None = None,
) -> MultiAgentEvolutionResult:
    """Evolve multiple agents together.
    
    Optimizes instructions for all provided agents by targeting
    the primary agent's output score. When share_session=True,
    agents execute sequentially with shared session state, enabling
    later agents to access earlier agents' outputs.
    
    Args:
        agents: List of ADK agents to evolve together. Must have
            at least one agent. All agents must have unique names.
        primary: Name of the agent whose output is used for scoring.
            Must match one of the agent names in the list.
        trainset: Training examples for evaluation. Each example
            should have an "input" key and optionally an "expected" key.
        critic: Optional critic agent for scoring. If None, the primary
            agent must have an output_schema for schema-based scoring.
        share_session: Whether agents share session state during
            execution. When True (default), uses SequentialAgent.
            When False, agents execute with isolated sessions.
        config: Evolution configuration. If None, uses EvolutionConfig
            defaults.
    
    Returns:
        MultiAgentEvolutionResult containing evolved_instructions dict
        mapping agent names to their optimized instruction text, along
        with score metrics and iteration history.
    
    Raises:
        MultiAgentValidationError: If agents list is empty, primary
            agent not found, duplicate agent names, or no scorer
            and primary lacks output_schema.
        EvolutionError: If evolution fails during execution.
    
    Examples:
        Basic usage with three agents:
        
        ```python
        from google.adk.agents import LlmAgent
        from gepa_adk import evolve_group
        
        generator = LlmAgent(
            name="generator",
            model="gemini-2.0-flash",
            instruction="Generate code based on the requirement.",
        )
        critic = LlmAgent(
            name="critic", 
            model="gemini-2.0-flash",
            instruction="Review the code in {generator_output}.",
        )
        validator = LlmAgent(
            name="validator",
            model="gemini-2.0-flash",
            instruction="Validate the reviewed code.",
            output_schema=ValidationResult,
        )
        
        result = await evolve_group(
            agents=[generator, critic, validator],
            primary="validator",
            trainset=training_data,
        )
        
        print(result.evolved_instructions["generator"])
        print(result.evolved_instructions["critic"])
        print(result.evolved_instructions["validator"])
        ```
        
        With custom critic scorer:
        
        ```python
        scoring_critic = LlmAgent(
            name="quality_scorer",
            model="gemini-2.0-flash",
            instruction="Score the output quality.",
            output_schema=CriticOutput,
        )
        
        result = await evolve_group(
            agents=[generator, validator],
            primary="validator",
            trainset=training_data,
            critic=scoring_critic,
        )
        ```
    """
```

---

## Parameters

### agents

| Property | Value |
|----------|-------|
| Type | `list[LlmAgent]` |
| Required | Yes |
| Constraints | len >= 1, unique names |

**Behavior**:
- Each agent's instruction is included in the candidate for evolution
- Agents execute in list order when `share_session=True`
- Original agents are not mutated

### primary

| Property | Value |
|----------|-------|
| Type | `str` |
| Required | Yes |
| Constraints | Must match an agent name |

**Behavior**:
- Only this agent's output is scored
- Other agents contribute to the pipeline but aren't directly evaluated

### trainset

| Property | Value |
|----------|-------|
| Type | `list[dict[str, Any]]` |
| Required | Yes |
| Constraints | len >= 1 |

**Expected Structure**:
```python
[
    {"input": "Create a function...", "expected": "def foo(): ..."},
    {"input": "Write a class...", "expected": "class Bar: ..."},
]
```

### critic

| Property | Value |
|----------|-------|
| Type | `LlmAgent | None` |
| Required | No |
| Default | `None` |

**Behavior**:
- If provided, wraps in `CriticScorer` for evaluation
- If None, primary agent must have `output_schema` for schema-based scoring

### share_session

| Property | Value |
|----------|-------|
| Type | `bool` |
| Required | No |
| Default | `True` |

**Behavior**:
- `True`: Agents execute via `SequentialAgent`, sharing `InvocationContext`
- `False`: Agents execute with isolated sessions

### config

| Property | Value |
|----------|-------|
| Type | `EvolutionConfig | None` |
| Required | No |
| Default | `None` (uses EvolutionConfig defaults) |

---

## Return Type

### MultiAgentEvolutionResult

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class MultiAgentEvolutionResult:
    evolved_instructions: dict[str, str]  # agent_name -> instruction
    original_score: float
    final_score: float
    primary_agent: str
    iteration_history: list[IterationRecord]
    total_iterations: int
    
    @property
    def improvement(self) -> float: ...
    
    @property
    def improved(self) -> bool: ...
    
    @property
    def agent_names(self) -> list[str]: ...
```

---

## Error Conditions

| Condition | Exception | Message Pattern |
|-----------|-----------|-----------------|
| Empty agents list | `MultiAgentValidationError` | "agents list cannot be empty" |
| Primary not found | `MultiAgentValidationError` | "primary agent '{name}' not found in agents list" |
| Duplicate names | `MultiAgentValidationError` | "duplicate agent name: '{name}'" |
| No scorer, no schema | `MultiAgentValidationError` | "no scorer and primary agent lacks output_schema" |
| Evolution failure | `EvolutionError` | Context-dependent |

---

## Invariants

1. **Immutability**: Original agents are never mutated
2. **Completeness**: Result contains instructions for ALL input agents
3. **Consistency**: `primary_agent` in result matches `primary` parameter
4. **Order preservation**: `evolved_instructions` keys match agent order

---

## Concurrency

- Function is async and should be awaited
- Multiple `evolve_group()` calls can run concurrently (isolated state)
- Internal evaluations respect `config.max_concurrent_evals`

---

## Idempotency

- Not idempotent: Different runs may produce different results due to LLM stochasticity
- Deterministic test mode possible via fixed seed (future enhancement)
