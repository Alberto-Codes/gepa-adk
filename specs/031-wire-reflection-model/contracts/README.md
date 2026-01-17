# Contracts: Wire Reflection Model Config to Proposer

**Feature**: 031-wire-reflection-model
**Date**: 2026-01-17

## Overview

This feature does not introduce new API contracts. It wires an existing configuration field through internal components.

## Existing Contracts (Unchanged)

### EvolutionConfig API

The `EvolutionConfig` dataclass already exposes `reflection_model` as a public field:

```python
from gepa_adk import EvolutionConfig

config = EvolutionConfig(
    max_iterations=50,
    reflection_model="gemini/gemini-2.0-flash"  # Already documented
)
```

### evolve() / evolve_group() API

These functions already accept `EvolutionConfig`:

```python
from gepa_adk import evolve, EvolutionConfig

result = await evolve(
    agent=my_agent,
    trainset=my_trainset,
    scorer=my_scorer,
    config=EvolutionConfig(reflection_model="ollama_chat/llama3:8b")
)
```

## Why No New Contracts

1. **No new endpoints**: This is internal wiring, not a new API
2. **No protocol changes**: `ProposerProtocol` unchanged
3. **No new data structures**: Using existing `EvolutionConfig`
4. **Backward compatible**: Existing code continues to work

## Verification

The feature will be verified through unit tests that confirm:
1. Config value flows to proposer
2. Default value is used when not specified
3. Both adapter paths (single/multi-agent) work correctly
