# Research: Multi-Agent Co-Evolution

**Feature**: 014-multi-agent-coevolution  
**Date**: January 11, 2026  
**Status**: Complete

## Overview

This document captures research findings for implementing multi-agent co-evolution in gepa-adk. The goal is to enable evolving multiple ADK agents together while sharing session state.

---

## Research Topics

### 1. ADK Multi-Agent Session State Sharing

**Question**: How do ADK agents share session state during execution?

**Findings**:

ADK provides three primary mechanisms for agent communication:

1. **Shared Session State (`session.state`)**: Agents share an `InvocationContext` containing a `Session` object. State is accessed via `context.state['key']` or the `output_key` property on LlmAgent.

2. **SequentialAgent**: Passes the same `InvocationContext` to each sub-agent sequentially. Earlier agents can write to state (e.g., via `output_key`), later agents read that state.

3. **output_key Property**: LlmAgent automatically saves its final response to `state[output_key]`. Subsequent agents can reference this via template strings like `{output_key}` in their instructions.

**Decision**: Use ADK's `SequentialAgent` with `output_key` for session sharing. This is the native ADK pattern for passing data between agents in a pipeline.

**Implementation Details** (from ADK source code analysis):

1. **State Class Prefixes**: ADK's `State` class (`google.adk.sessions.state`) uses prefixes for scoping:
   - `app:` - Application-level state (persistent)
   - `user:` - User-level state (persistent)
   - `temp:` - Temporary state (cleared between invocations)
   
   ```python
   APP_PREFIX = "app:"
   USER_PREFIX = "user:"
   TEMP_PREFIX = "temp:"
   ```

2. **SequentialAgent Implementation**: The `_run_async_impl` method iterates through `sub_agents`:
   ```python
   async for event in sub_agent.run_async(ctx):
       yield event
   ```
   Each sub-agent receives the **same** `InvocationContext`, ensuring state changes propagate.

3. **Session Model**: Session (`google.adk.sessions.session.Session`) contains:
   ```python
   state: dict[str, Any] = {}  # Session state dictionary
   events: list[Event] = []    # Event history
   ```

**Rationale**: Native ADK support means:
- No custom session management code needed
- Consistent with ADK best practices
- Automatic state propagation handled by framework

**Alternatives Considered**:
- Custom state passing via middleware: Rejected - reinvents existing functionality
- Explicit parameter passing between agents: Rejected - doesn't leverage ADK's design

---

### 2. Multi-Agent Execution Orchestration

**Question**: How should multiple agents be executed together for evaluation?

**Findings**:

ADK provides `SequentialAgent` which:
- Executes sub-agents in defined order
- Shares `InvocationContext` (including temp state) between all sub-agents
- Is deterministic in execution order (not LLM-driven)
- Supports nested workflow agents

```python
from google.adk.agents import SequentialAgent, LlmAgent

pipeline = SequentialAgent(
    name="MultiAgentPipeline",
    sub_agents=[generator, critic, validator]
)
```

For non-shared sessions (`share_session=False`), we can execute agents independently using separate `Runner` instances with isolated sessions.

**Decision**: Create a dynamic `SequentialAgent` at evaluation time with instruction-overridden agents as sub-agents.

**Rationale**: 
- Leverages ADK's native multi-agent orchestration
- Session state sharing handled automatically
- Clean separation between orchestration and evolution logic

**Alternatives Considered**:
- Manual sequential execution with state copying: Rejected - error-prone, duplicates ADK logic
- ParallelAgent: Rejected - agents need sequential execution for state sharing

---

### 3. Candidate Structure for Multi-Agent Evolution

**Question**: How should the candidate dictionary be structured for multiple agents?

**Findings**:

Current single-agent candidate structure:
```python
candidate = {"instruction": "Be helpful..."}
```

For multi-agent, each agent needs its own instruction slot:
```python
candidate = {
    "generator_instruction": "Generate code...",
    "critic_instruction": "Review code...",
    "validator_instruction": "Validate code...",
}
```

The naming convention `{agent.name}_instruction` ensures:
- Unique keys for each agent
- Clear mapping between agents and their instructions
- Compatibility with existing mutation proposer (operates on string values)

**Decision**: Use `{agent.name}_instruction` as keys in the candidate dictionary.

**Rationale**: 
- Simple, predictable naming convention
- Works with existing evolution engine (treats candidate as dict[str, str])
- Easy to map back to agents after evolution

**Alternatives Considered**:
- Nested structure `{"agents": {"gen": {...}}}`: Rejected - requires engine changes
- Index-based keys `agent_0_instruction`: Rejected - less readable, harder to debug

---

### 4. Scoring Strategy for Multi-Agent Pipelines

**Question**: How should the primary agent's output be scored in a multi-agent pipeline?

**Findings**:

Two scoring approaches exist in gepa-adk:

1. **Schema-based scoring**: When agent has `output_schema`, structured output is validated/scored
2. **Critic-based scoring**: `CriticScorer` wraps a critic agent that evaluates outputs

For multi-agent pipelines:
- The `primary` agent's output determines the overall score
- Other agents contribute to the pipeline but aren't directly scored
- The critic agent (if provided) evaluates the primary agent's final output

**Decision**: Score only the primary agent's output. Use `CriticScorer` when critic is provided, otherwise use schema-based scoring if primary agent has `output_schema`.

**Rationale**:
- Aligns with spec requirement (FR-002, FR-012)
- Simple mental model: optimize for primary agent's quality
- Supporting agents are co-evolved to improve primary's performance

**Alternatives Considered**:
- Weighted multi-objective scoring: Rejected - increases complexity, not in spec
- Score all agents and combine: Rejected - unclear how to weight contributions

---

### 5. Instruction Override Mechanism

**Question**: How do we override agent instructions during evaluation without mutating original agents?

**Findings**:

ADK `LlmAgent` stores instruction as `agent.instruction` property. Options:

1. **Clone and modify**: Create agent copies with new instructions
2. **Instruction parameter override**: Some ADK patterns allow instruction at runtime
3. **Agent factory pattern**: Function that creates agents with given instructions

Looking at existing `ADKAdapter`:
```python
# Caches original instruction and restores after evaluation
original_instruction = self.agent.instruction
self.agent.instruction = candidate.get("instruction", original_instruction)
# ... evaluate ...
self.agent.instruction = original_instruction
```

**Decision**: Clone agents with modified instructions for each evaluation. Use a factory function to create agent copies.

**Implementation Details** (from ADK source code analysis):

1. **Pydantic BaseModel**: `LlmAgent` extends Pydantic `BaseModel`, so we get `model_copy()`:
   ```python
   cloned_agent = original_agent.model_copy(
       update={"instruction": new_instruction}
   )
   ```

2. **Critical Constraint - output_schema**: When `output_schema` is set on LlmAgent, the agent **CANNOT use tools**:
   ```python
   # From llm_agent.py line 113:
   # "When this is set, agent can ONLY reply and CANNOT use any tools"
   output_schema: Optional[type[BaseModel]] = None
   ```
   This affects how we handle tool-using agents in the pipeline.

3. **Agent Properties Available for Cloning**:
   - `name: str` - Agent identifier
   - `instruction: str | InstructionProvider | Callable` - The evolvable property
   - `sub_agents: list[BaseAgent]` - Nested agents (for orchestrators)
   - `model: str | None` - LLM model name
   - `output_key: str | None` - State key for automatic output storage

**Rationale**:
- Avoids mutation of user's original agents
- Thread-safe (no shared mutable state)
- Clean separation between original and evolved agents
- Pydantic's `model_copy()` provides efficient shallow copy with updates

**Alternatives Considered**:
- Mutate-evaluate-restore pattern: Rejected - not thread-safe, error-prone
- Subclass with instruction override: Rejected - over-engineered

---

### 6. Return Type Design

**Question**: What should `evolve_group()` return?

**Findings**:

Current `EvolutionResult` structure:
```python
@dataclass(frozen=True)
class EvolutionResult:
    original_score: float
    final_score: float
    evolved_instruction: str  # Single instruction
    iteration_history: list[IterationRecord]
    total_iterations: int
```

For multi-agent, we need:
- Dictionary of evolved instructions per agent
- Same score metrics (original, final)
- Iteration history

**Decision**: Extend or create new dataclass with `evolved_instructions: dict[str, str]` field mapping agent names to instructions.

**Rationale**:
- Directly usable: users can apply instructions by agent name
- Compatible with spec requirement (FR-008)
- Preserves existing metrics for analysis

**Alternatives Considered**:
- Return list of results: Rejected - harder to access by agent name
- Modify agents in-place: Rejected - violates immutability principle

---

## Summary of Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| Session Sharing | Use ADK `SequentialAgent` | Native ADK pattern, automatic state propagation |
| Orchestration | Dynamic SequentialAgent per evaluation | Leverages ADK, handles instruction overrides |
| Candidate Keys | `{agent.name}_instruction` | Simple, predictable, compatible with engine |
| Scoring | Primary agent only, via CriticScorer or schema | Aligns with spec, simple mental model |
| Instruction Override | Clone agents with new instructions | Thread-safe, no mutation of originals |
| Return Type | `evolved_instructions: dict[str, str]` | Direct usability, spec-compliant |

## Dependencies Confirmed

- **#6 AsyncGEPAEngine**: ✅ Available - handles evolution loop with adapter
- **#8 ADK Adapter**: ✅ Available - reference implementation for single-agent
- **#9 CriticScorer**: ✅ Available - can score primary agent output

---

## GEPA Compatibility Analysis

**Source**: Analysis of `gepa` 0.0.24 in `.venv`

### Key GEPA Types

```python
# From gepa/core/adapter.py
Candidate = dict[str, str]  # Type alias - our multi-agent candidate is compatible!

class GEPAAdapter(Protocol):
    """Protocol for adapters connecting GEPA to agent frameworks."""
    
    async def evaluate(
        self,
        batch: EvaluationBatch,
        candidate: Candidate,
        capture_traces: bool = False,
    ) -> EvaluationBatch:
        """Evaluate a candidate against a batch of examples."""
        ...
    
    def make_reflective_dataset(
        self,
        batch: EvaluationBatch
    ) -> list[str]:
        """Generate reflective dataset from evaluation results."""
        ...
```

### GEPA optimize() Function

```python
# From gepa/api.py
async def optimize(
    adapter: GEPAAdapter,
    seed_candidate: Candidate,  # dict[str, str] - multi-agent compatible!
    eval_batch: EvaluationBatch,
    proposer: MutationProposer,
    *,
    max_iterations: int = 10,
    score_threshold: float | None = None,
) -> EvolutionResult:
```

### Compatibility Confirmation

Our `MultiAgentAdapter` can use `Candidate = dict[str, str]` directly:
```python
candidate = {
    "generator_instruction": "...",
    "critic_instruction": "...",
    "validator_instruction": "...",
}
```

This is fully compatible with GEPA's `seed_candidate` parameter and existing mutation proposers that operate on `dict[str, str]`.

---

## Open Questions

None - all technical questions resolved.
