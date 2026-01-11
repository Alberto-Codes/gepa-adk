# Data Model: Multi-Agent Co-Evolution

**Feature**: 014-multi-agent-coevolution  
**Date**: January 11, 2026  
**Status**: Draft

## Overview

This document defines the data structures and entities for multi-agent co-evolution. The design follows hexagonal architecture with domain models separated from adapter implementations.

---

## Entity Definitions

### 1. MultiAgentEvolutionResult (Domain Entity)

**Location**: `src/gepa_adk/domain/models.py`

**Description**: Outcome of a completed multi-agent evolution run. Extends the concept of `EvolutionResult` for multiple agents.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class MultiAgentEvolutionResult:
    """Outcome of a completed multi-agent evolution run.
    
    Contains evolved instructions for all agents in the group,
    along with performance metrics and evolution history.
    
    Attributes:
        evolved_instructions: Mapping of agent name to evolved instruction text.
        original_score: Starting performance score (baseline).
        final_score: Ending performance score (best achieved).
        primary_agent: Name of the agent whose output was used for scoring.
        iteration_history: Chronological list of iteration records.
        total_iterations: Number of iterations performed.
    """
    
    evolved_instructions: dict[str, str]
    original_score: float
    final_score: float
    primary_agent: str
    iteration_history: list[IterationRecord]
    total_iterations: int
```

**Computed Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `improvement` | `float` | `final_score - original_score` |
| `improved` | `bool` | `final_score > original_score` |
| `agent_names` | `list[str]` | Sorted list of evolved agent names |

**Validation Rules**:
- `evolved_instructions` must have at least one entry
- `primary_agent` must be a key in `evolved_instructions`
- `original_score` and `final_score` should be in [0.0, 1.0] by convention

**Relationships**:
- Contains: `IterationRecord` instances (from existing domain)
- Created by: `evolve_group()` API function

---

### 2. MultiAgentAdapter (Adapter Entity)

**Location**: `src/gepa_adk/adapters/multi_agent.py`

**Description**: Orchestrates evaluation of multiple ADK agents with session state sharing. Implements `AsyncGEPAAdapter` protocol.

```python
class MultiAgentAdapter:
    """Adapter for multi-agent pipeline evaluation.
    
    Wraps multiple ADK agents into a SequentialAgent for evaluation,
    enabling session state sharing between agents. Implements
    AsyncGEPAAdapter protocol for use with AsyncGEPAEngine.
    
    Attributes:
        agents: List of ADK agents to evaluate together.
        primary: Name of agent whose output is used for scoring.
        scorer: Scoring implementation (CriticScorer or similar).
        share_session: Whether agents share session state.
        session_service: Session service for state management.
        _logger: Bound structlog logger with context.
    """
    
    agents: list[LlmAgent]
    primary: str
    scorer: Scorer | None
    share_session: bool
    session_service: BaseSessionService
    _logger: BoundLogger
```

**Initialization Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agents` | `list[LlmAgent]` | Yes | - | ADK agents to evolve together |
| `primary` | `str` | Yes | - | Name of agent for scoring |
| `scorer` | `Scorer \| None` | No | `None` | Custom scorer (uses schema-based if None) |
| `share_session` | `bool` | No | `True` | Whether to share session state |
| `session_service` | `BaseSessionService \| None` | No | `None` | Custom session service |
| `app_name` | `str` | No | `"multi_agent_eval"` | Application name for sessions |

**Protocol Compliance**: Implements `AsyncGEPAAdapter[dict[str, Any], MultiAgentTrajectory, str]`

**Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `evaluate` | `async (batch, candidate, capture_traces) -> EvaluationBatch` | Evaluate pipeline with candidate instructions |
| `make_reflective_dataset` | `async (candidate, eval_batch, components) -> dict` | Generate reflection data from trajectories |
| `propose_new_texts` | `async (candidate, dataset, components) -> dict[str, str]` | Propose mutations for all agent instructions |

**Validation Rules**:
- `agents` must have at least one agent
- `primary` must match an agent's name in the list
- All agent names must be unique
- If `scorer` is None, primary agent should have `output_schema`

---

### 3. MultiAgentTrajectory (Domain Entity)

**Location**: `src/gepa_adk/domain/trajectory.py`

**Description**: Captures execution traces from multi-agent pipeline evaluation.

```python
@dataclass(frozen=True, slots=True)
class MultiAgentTrajectory:
    """Execution trace from multi-agent pipeline evaluation.
    
    Captures individual agent trajectories and overall pipeline metrics.
    
    Attributes:
        agent_trajectories: Mapping of agent name to individual trajectory.
        pipeline_output: Final output from the primary agent.
        total_token_usage: Aggregated token usage across all agents.
        error: Error message if pipeline execution failed.
    """
    
    agent_trajectories: dict[str, ADKTrajectory]
    pipeline_output: str
    total_token_usage: TokenUsage | None
    error: str | None = None
```

**Relationships**:
- Contains: `ADKTrajectory` (from existing domain)
- Stored in: `EvaluationBatch.trajectories`

---

### 4. MultiAgentCandidate (Type Alias)

**Location**: `src/gepa_adk/domain/types.py`

**Description**: Type alias for multi-agent candidate structure.

```python
# Multi-agent candidate: maps "{agent_name}_instruction" -> instruction text
MultiAgentCandidate = dict[str, str]
```

**Structure Convention**:
```python
{
    "generator_instruction": "Generate Python code...",
    "critic_instruction": "Review the code...",
    "validator_instruction": "Validate the code...",
}
```

**Key Format**: `{agent.name}_instruction`

---

## Exception Definitions

### MultiAgentValidationError

**Location**: `src/gepa_adk/domain/exceptions.py`

**Description**: Raised when multi-agent configuration is invalid.

```python
class MultiAgentValidationError(EvolutionError):
    """Raised when multi-agent configuration validation fails.
    
    Attributes:
        message: Error description.
        field: Configuration field that failed validation.
        value: The invalid value.
        constraint: Description of the violated constraint.
    """
    
    def __init__(
        self,
        message: str,
        *,
        field: str,
        value: Any,
        constraint: str,
    ) -> None:
        super().__init__(message)
        self.field = field
        self.value = value
        self.constraint = constraint
```

**Raised When**:
- Empty agents list provided
- Primary agent name not in agents list
- Duplicate agent names detected
- No scorer and primary agent lacks output_schema

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         evolve_group()                          │
│                      (Public API Function)                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │ creates
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MultiAgentAdapter                          │
│              (Implements AsyncGEPAAdapter protocol)             │
├─────────────────────────────────────────────────────────────────┤
│  - agents: list[LlmAgent]                                       │
│  - primary: str                                                 │
│  - scorer: Scorer | None                                        │
│  - share_session: bool                                          │
└─────────────────────────────┬───────────────────────────────────┘
                              │ used by
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AsyncGEPAEngine                            │
│              (Existing evolution orchestrator)                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ produces
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  MultiAgentEvolutionResult                      │
│                    (Immutable result type)                      │
├─────────────────────────────────────────────────────────────────┤
│  - evolved_instructions: dict[str, str]                         │
│  - original_score: float                                        │
│  - final_score: float                                           │
│  - primary_agent: str                                           │
│  - iteration_history: list[IterationRecord]                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## State Transitions

### MultiAgentAdapter Evaluation Flow

```
┌──────────────┐    ┌───────────────────┐    ┌──────────────────┐
│   Receive    │    │  Build Pipeline   │    │    Execute       │
│   Candidate  │───▶│  (SequentialAgent │───▶│    Pipeline      │
│              │    │   with overrides) │    │                  │
└──────────────┘    └───────────────────┘    └────────┬─────────┘
                                                      │
                    ┌───────────────────┐             │
                    │  Return           │◀────────────┘
                    │  EvaluationBatch  │
                    └───────────────────┘
```

### Instruction Override Flow

```
For each agent in agents:
    1. Get original instruction: agent.instruction
    2. Lookup candidate key: f"{agent.name}_instruction"
    3. If key exists: clone agent with new instruction
    4. Else: use agent unchanged
    
Build SequentialAgent from cloned agents
Execute pipeline
Extract primary agent output for scoring
```

---

## Validation Matrix

| Field | Validation | Error Type | Error Message |
|-------|------------|------------|---------------|
| `agents` | len >= 1 | `MultiAgentValidationError` | "agents list cannot be empty" |
| `primary` | in agent names | `MultiAgentValidationError` | "primary agent '{name}' not found in agents list" |
| agent names | unique | `MultiAgentValidationError` | "duplicate agent name: '{name}'" |
| scorer/schema | scorer or output_schema | `MultiAgentValidationError` | "no scorer and primary agent lacks output_schema" |
