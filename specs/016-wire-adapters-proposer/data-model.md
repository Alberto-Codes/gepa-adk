# Data Model: Wire Adapters to AsyncReflectiveMutationProposer

**Feature**: 016-wire-adapters-proposer  
**Phase**: 1 - Design  
**Date**: 2026-01-12

## Entity Overview

This feature modifies existing entities rather than creating new ones. No new domain models required.

### Modified Entities

#### ADKAdapter

**Location**: `src/gepa_adk/adapters/adk_adapter.py`

**New Attribute**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `_proposer` | `AsyncReflectiveMutationProposer` | Mutation proposer for generating improved instructions via LLM |

**Constructor Change**:
```
__init__(..., proposer: AsyncReflectiveMutationProposer | None = None)
```

**Behavior Change**: `propose_new_texts()` delegates to `_proposer.propose()` instead of returning stub values.

---

#### MultiAgentAdapter

**Location**: `src/gepa_adk/adapters/multi_agent.py`

**New Attribute**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `_proposer` | `AsyncReflectiveMutationProposer` | Mutation proposer for generating improved instructions via LLM |

**Constructor Change**:
```
__init__(..., proposer: AsyncReflectiveMutationProposer | None = None)
```

**Behavior Change**: `propose_new_texts()` delegates to `_proposer.propose()` instead of heuristic selection.

---

## Type Definitions

### Existing Types (No Changes)

```python
# From gepa_adk.engine.proposer
ReflectiveDataset = Mapping[str, Sequence[Mapping[str, Any]]]
ProposalResult = dict[str, str] | None

# Candidate type (used throughout)
Candidate = dict[str, str]

# Components list
ComponentsToUpdate = list[str]
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Evolution Loop                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Adapter.propose_new_texts()                       │
│  Input: candidate, reflective_dataset, components_to_update          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AsyncReflectiveMutationProposer.propose()               │
│  - Builds LLM prompt from current instruction + feedback             │
│  - Calls LiteLLM acompletion() or ADK reflection agent               │
│  - Returns improved instruction text or None                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
              ┌───────────────────┐   ┌───────────────────┐
              │  Result: dict     │   │  Result: None     │
              │  (proposed texts) │   │  (empty dataset)  │
              └───────────────────┘   └───────────────────┘
                          │                   │
                          ▼                   ▼
              ┌───────────────────┐   ┌───────────────────┐
              │  Merge with       │   │  Return unchanged │
              │  candidate for    │   │  candidate values │
              │  missing keys     │   │                   │
              └───────────────────┘   └───────────────────┘
                          │                   │
                          └─────────┬─────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Return: dict[str, str]                           │
│  Maps component names to proposed (or unchanged) text values         │
└─────────────────────────────────────────────────────────────────────┘
```

## Validation Rules

### Constructor Validation

| Rule | Validation | Error Type |
|------|------------|------------|
| Proposer type | If provided, must be `AsyncReflectiveMutationProposer` instance or duck-typed equivalent | `TypeError` |

**Note**: Strict type checking not required since Python uses duck typing. The proposer just needs a compatible `propose()` method.

### Runtime Validation

| Rule | Validation | Behavior |
|------|------------|----------|
| Empty dataset | `reflective_dataset == {}` | Proposer returns `None`, adapter returns unchanged values |
| Missing components | Component not in dataset | Proposer skips, adapter preserves original value |
| LLM failure | Exception from proposer | Propagate to caller (no swallowing) |

## State Transitions

No state machine needed. The `propose_new_texts()` method is stateless:
- Input → Process → Output
- No persistent state changes in adapter
- Each call is independent

## Relationship Diagram

```
┌─────────────────────────┐         ┌──────────────────────────────────┐
│      ADKAdapter         │         │   AsyncReflectiveMutationProposer │
│  (adapters layer)       │────────▶│   (engine layer)                  │
│                         │   has   │                                   │
│  _proposer              │         │   propose()                       │
│  propose_new_texts()    │         │   model, temperature, etc.        │
└─────────────────────────┘         └──────────────────────────────────┘
           │                                       │
           │                                       │
           │ implements                            │ uses
           ▼                                       ▼
┌─────────────────────────┐         ┌──────────────────────────────────┐
│  AsyncGEPAAdapter       │         │   litellm.acompletion()           │
│  (ports layer)          │         │   (external dependency)           │
│                         │         │                                   │
│  Protocol definition    │         │   Async LLM API calls             │
└─────────────────────────┘         └──────────────────────────────────┘

┌─────────────────────────┐
│   MultiAgentAdapter     │
│  (adapters layer)       │────────▶ [Same relationship to proposer]
│                         │
│  _proposer              │
│  propose_new_texts()    │
└─────────────────────────┘
```

## Migration Notes

No data migration needed. This feature:
- Adds optional parameter (backward compatible)
- Changes internal behavior only
- No persisted state affected
- No database schema changes

---

## GEPA Library Alignment

### Reflective Dataset Format

Our adapters use the same reflective dataset format as the original GEPA library:

```python
# Standard format (from gepa/adapters/default_adapter/default_adapter.py)
{
    "Inputs": str | dict[str, str],      # Input to the component
    "Generated Outputs": str,             # Model output
    "Feedback": str,                      # Performance feedback
}
```

This format is produced by `build_reflection_example()` in both adapters and consumed by `AsyncReflectiveMutationProposer.propose()`.

### Type Compatibility

| gepa-adk Type | GEPA Equivalent | Compatible |
|---------------|-----------------|------------|
| `ReflectiveDataset` | `Mapping[str, Sequence[Mapping[str, Any]]]` | ✅ Yes |
| `dict[str, str]` | `Candidate` | ✅ Yes |
| `ProposalResult` (`dict[str, str] \| None`) | `dict[str, str]` (never None) | ⚠️ Adapter handles None |

The key difference is our proposer can return `None` (empty dataset case), which adapters convert to fallback values.