# gepa-adk: Evolutionary Optimization for Google ADK Agents

> **Status**: Proposal Draft
> **Author**: agent-workflow-suite team
> **Date**: 2026-01-09
> **Repository**: New standalone repo `gepa-adk` (not a fork)
> **Reference**: This proposal lives in agent-workflow-suite for historical context

---

## TL;DR

**What**: Create new `gepa-adk` package implementing GEPA's algorithm from scratch with async-first ADK integration.

**Why**: No bridge exists between GEPA's evolutionary optimization and ADK's agent framework. Teams must build ~500+ lines of custom adapter code.

**Approach**:
- New standalone repo (not a fork)
- Reference `.venv/gepa` for algorithm parity
- Reference `agent-workflow-suite/adapters/gepa/` for ADK patterns
- Validate by swapping into agent-workflow-suite

**Key Innovations**:
- **Async-first** engine (GEPA algorithm reimplemented as async)
- **Critic agents** with structured `{score, feedback}` output (vs GEPA's mechanical scoring)
- **ADK reflection agents** for instruction proposals (vs raw LiteLLM calls)
- **Concurrent batch evaluation** (3-5x speedup via semaphore-controlled parallelism)

**Architecture**: Hexagonal (ADR-000) with Protocol-based interfaces (ADR-002)

**Outcome**: `from gepa_adk import evolve` → one-line evolution for any ADK agent

---

## Table of Contents

1. [Architecture Alignment](#architecture-alignment) - ADR compliance
2. [Executive Summary](#executive-summary) - Problem and solution
3. [Core Features](#core-features) - What the package does
4. [Package Structure](#package-structure-adr-000-hexagonal) - Hexagonal layout
5. [Async-First Architecture](#async-first-architecture) - Why and how
6. [Testing Strategy](#testing-strategy-adr-005) - Three-layer approach
7. [Feature Prioritization](#feature-prioritization) - MVP vs roadmap
8. [Migration Path](#migration-path-for-agent-workflow-suite) - 5-week plan
9. [Open Questions](#open-questions) - Decisions needed
10. [Appendices](#appendix-a-code-reference-map) - Technical details

---

## Architecture Alignment

This package follows architectural principles established in agent-workflow-suite ADRs:

| ADR | Principle | Application in gepa-adk |
|-----|-----------|------------------------|
| **ADR-000** | Hexagonal Architecture | Domain (evolution models) → Ports (async protocols) → Adapters (ADK impl) |
| **ADR-002** | Protocol for Interfaces | `AsyncGEPAAdapter`, `Scorer`, `AgentProvider` use Protocol (not ABC) |
| **ADR-005** | Three-Layer Testing | Contract tests (protocol compliance) + Integration (real ADK) + Unit (mock adapter) |
| **ADR-006** | External Library Integration | GEPA concepts behind ports; ADK access via adapters; package IS the adapter |
| **ADR-009** | Exception Hierarchy | `EvolutionError(message, *, cause)` base pattern |

### Why Protocol (ADR-002)

Per ADR-002 decision flowchart:
- ❌ No lifecycle management (no context managers)
- ❌ No `isinstance()` checks needed
- ❌ No complex generic type variables
- ✅ Simple method signatures → **Use Protocol**

```python
# ✅ CORRECT: Protocol for async adapter
@runtime_checkable
class AsyncGEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    async def evaluate(self, batch, candidate, capture_traces=False) -> EvaluationBatch: ...
    async def make_reflective_dataset(...) -> Mapping: ...
```

### Hexagonal Structure (ADR-000)

```
gepa-adk/
├── domain/                    # 🏢 CORE - Pure evolution logic
│   ├── models.py             # EvolutionConfig, EvolutionResult, Candidate
│   └── exceptions.py         # EvolutionError hierarchy
│
├── ports/                     # 🔌 INTERFACES - Protocols
│   ├── adapter.py            # AsyncGEPAAdapter protocol
│   ├── scorer.py             # Scorer protocol
│   └── agent_provider.py     # AgentProvider protocol (optional persistence)
│
├── adapters/                  # 🔧 IMPLEMENTATIONS - ADK-specific
│   ├── adk_adapter.py        # ADKAdapter implements AsyncGEPAAdapter
│   ├── critic_scorer.py      # CriticScorer implements Scorer
│   └── litellm_reflection.py # LiteLLM-based reflection fallback
│
├── engine/                    # 🔄 ORCHESTRATION - Async engine
│   ├── async_engine.py       # AsyncGEPAEngine
│   └── proposer.py           # AsyncReflectiveMutationProposer
│
├── utils/                     # 🛠️ UTILITIES
│   ├── state_guard.py        # State key preservation
│   ├── event_extraction.py   # ADK event parsing
│   └── parsing.py            # JSON/YAML parsing
│
└── api.py                     # 📦 PUBLIC API - evolve(), evolve_sync()
```

### Exception Hierarchy (ADR-009)

```python
# domain/exceptions.py
class EvolutionError(Exception):
    """Base exception for evolution operations.

    Attributes:
        message: Human-readable error description
        cause: Original exception that caused this error (for chaining)
    """

    def __init__(
        self,
        message: str,
        *,  # Force keyword arguments
        cause: Exception | None = None,
        agent_name: str | None = None,
    ):
        self.message = message
        self.cause = cause
        self.agent_name = agent_name
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.cause:
            return f"{base} (caused by: {self.cause})"
        return base


class EvaluationError(EvolutionError):
    """Raised when batch evaluation fails."""
    pass


class ProposalError(EvolutionError):
    """Raised when instruction proposal fails."""
    pass


class ScoringError(EvolutionError):
    """Raised when critic scoring fails."""
    pass
```

Usage with proper chaining:
```python
try:
    result = await executor.execute_agent(...)
except ADKError as e:
    raise EvaluationError(
        "Agent execution failed",
        agent_name=agent_name,
        cause=e,
    ) from e  # Both cause attribute AND from e
```

---

## Executive Summary

`gepa-adk` is a proposed Python package that bridges [GEPA](https://github.com/gepa-ai/gepa) (Genetic-Pareto optimization) with [Google's Agent Development Kit (ADK)](https://github.com/google/adk-python), enabling **evolutionary optimization of ADK agent instructions** through GEPA's proven optimization framework.

This package extracts battle-tested integration code from the `agent-workflow-suite` project, providing a clean, reusable library for anyone building ADK agents who wants to leverage evolutionary prompt optimization.

### Key Innovation: ADK-First Architecture

Unlike GEPA's default approach (raw LiteLLM calls for reflection), `gepa-adk` is **ADK-first**:

| Role | GEPA Default | gepa-adk (ADK-First) |
|------|--------------|----------------------|
| **Generator** | Any callable | ADK `LlmAgent` with tools, sessions, schemas |
| **Critic/Scorer** | Mechanical metric (exact match, etc.) | ADK agent with `output_schema` → structured `{score, feedback}` |
| **Reflection/Proposer** | Raw `litellm.completion()` call | ADK `LlmAgent` with configurable instruction |
| **Trajectory Data** | User-defined opaque object | ADK session state, events, tool calls |

---

## About the Upstream Projects

### GEPA (Genetic-Pareto Optimization)

[GEPA](https://github.com/gepa-ai/gepa) is a state-of-the-art framework for optimizing text components (prompts, code, instructions) using **reflective text evolution**. Developed by researchers from Databricks and UC Berkeley, GEPA:

- Outperforms GRPO by 10% on average (up to 20%) while using **35x fewer rollouts**
- Outperforms MIPROv2 by over 10% across multiple LLMs
- Uses Pareto-aware candidate selection for robust multi-objective optimization
- Provides the `GEPAAdapter` protocol for custom system integration

**Paper**: [GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning](https://arxiv.org/abs/2507.19457)

### Google ADK (Agent Development Kit)

[Google ADK](https://google.github.io/adk-docs/) is a code-first Python toolkit for building AI agents:

- **Multi-agent orchestration**: `SequentialAgent`, `LoopAgent`, `ParallelAgent`
- **Session management**: `DatabaseSessionService`, `InMemorySessionService` for state persistence
- **Tool support**: MCP tools, OpenAPI tools, built-in tools
- **Structured output**: `output_schema` for type-safe agent responses
- **Event capture**: Tool calls, state deltas, token usage tracking

---

## Problem Statement

### The Gap

- **GEPA** provides a powerful framework for evolving agent instructions through genetic algorithms and reflection-based optimization
- **Google ADK** provides a production-ready agent execution framework with sessions, tools, and multi-agent orchestration
- **No bridge exists** to use GEPA's optimization with ADK's execution model while preserving ADK's rich features

### GEPA's Default Scoring is Mechanical

GEPA's built-in adapters use mechanical scoring:
```python
# GEPA's default: exact match or simple metric
score = 1.0 if output == expected else 0.0
```

This works for well-defined tasks but loses valuable signal for complex agent outputs where nuanced feedback drives improvement.

### Current Workarounds

Teams wanting both capabilities must:
1. Build custom adapters from scratch (~500+ lines)
2. Lose ADK-specific features (session state, tool calls, events) during optimization
3. Manually handle multi-agent and workflow scenarios
4. Implement their own critic logic without ADK's structure

---

## Proposed Solution

### Package: `gepa-adk`

A lightweight adapter package that:
1. Implements GEPA's `GEPAAdapter` protocol using ADK's `AgentExecutor`
2. Enriches GEPA trajectories with ADK-specific observability data
3. Supports single-agent, multi-agent, and workflow evolution patterns
4. Provides safety layers for instruction mutation

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Application                        │
│  (agent-workflow-suite, custom ADK apps, notebooks, etc.)   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        gepa-adk                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  ADKGEPAAdapter │  │ EventExtraction │  │ StateGuard  │  │
│  │  (GEPA Protocol)│  │ (Trajectories)  │  │ (Safety)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  CriticScorer   │  │ MultiAgentUtil  │  │ WorkflowUtil│  │
│  │  (Evaluation)   │  │ (Co-evolution)  │  │ (Detection) │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│       gepa-ai           │     │      google-adk         │
│  (Evolution Engine)     │     │  (Agent Execution)      │
└─────────────────────────┘     └─────────────────────────┘
```

---

## Core Features

### 1. ADK-Native GEPA Adapter

```python
from gepa_adk import ADKAdapter, evolve

# Simple API - evolve any ADK agent
result = evolve(
    agent=my_adk_agent,           # google.adk.agents.LlmAgent
    trainset=examples,            # List of input/expected pairs
    critic=critic_agent,          # ADK agent with output_schema for scoring
    max_iterations=50,
    reflection_agent=reflection_agent,  # ADK agent for proposals (ADK-first!)
)

print(f"Improved from {result.original_score:.2f} → {result.final_score:.2f}")
print(f"Evolved instruction:\n{result.evolved_instruction}")
```

### 2. Critic Agents with Structured Feedback (Key Innovation)

**This is the core differentiator from GEPA's mechanical scoring.**

Critics are ADK agents with `output_schema` that return structured JSON:

```python
from google.adk.agents import LlmAgent

# Define critic with structured output schema
critic = LlmAgent(
    name="quality_critic",
    model="gemini-2.5-flash",
    instruction="""Evaluate the agent output for quality.
    Consider: accuracy, completeness, clarity, and actionability.""",
    output_schema={
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0, "maximum": 1},
            "feedback": {"type": "string"},
            "dimension_scores": {
                "type": "object",
                "properties": {
                    "accuracy": {"type": "number"},
                    "completeness": {"type": "number"},
                    "clarity": {"type": "number"}
                }
            },
            "actionable_guidance": {"type": "string"}
        },
        "required": ["score", "feedback"]
    }
)
```

The critic returns structured feedback that flows into GEPA's reflective dataset:

```json
{
  "score": 0.65,
  "feedback": "Output correctly identifies UI elements but misses error states.",
  "dimension_scores": {"accuracy": 0.8, "completeness": 0.5, "clarity": 0.7},
  "actionable_guidance": "Add explicit handling for validation errors and loading states."
}
```

This natural language feedback becomes **instrumental** for the reflection agent to propose targeted improvements—far richer than a simple 0/1 score.

### 3. ADK-First Reflection Agent

Instead of raw `litellm.completion()` calls, use an ADK agent for instruction proposals:

```python
from gepa_adk import create_adk_reflection_fn

# Create reflection agent with configurable instruction
reflection_agent = LlmAgent(
    name="instruction_evolver",
    model="gemini-2.5-flash",
    instruction="""Given the current instruction and execution feedback,
    propose an improved instruction that addresses the identified issues.

    Current instruction: {current_instruction}
    Execution results: {execution_results}

    Output ONLY the improved instruction text."""
)

# Use as GEPA's proposal function
proposal_fn = create_adk_reflection_fn(executor, "instruction_evolver")
```

Benefits over raw LiteLLM:
- **Configurable via YAML**: Change reflection prompts without code changes
- **Observability**: ADK sessions track all reflection calls
- **Tool access**: Reflection agent can use tools (e.g., validate syntax)
- **Retry/timeout handling**: Built into ADK executor

### 4. Rich Trajectory Capture (from ADK Sessions)

Trajectories leverage ADK's session state and event capture:

```python
from gepa_adk import TrajectoryConfig

config = TrajectoryConfig(
    include_tool_calls=True,      # Tool name, args, response from ADK events
    include_state_deltas=True,    # Session state changes over time
    include_token_usage=True,     # Aggregated from ADK model events
    redact_sensitive=True,        # Remove PII/secrets before reflection
)
```

**Session sharing** enables critics to access generator state:

```python
# Generator writes to session state
generator_result = await executor.execute_agent(
    "generator",
    input_text="Create Playwright script"
)
# session state now contains: {playwright_script: "..."}

# Critic reuses session to access the script
critic_result = await executor.execute_agent(
    "validator",
    input_text="Validate the script",
    existing_session_id=generator_result.adk_session_id  # Access {playwright_script}
)
```

### 5. Multi-Agent Co-Evolution

Evolve multiple agents together with shared session state:

```python
from gepa_adk import evolve_group

result = evolve_group(
    agents=[generator, critic, validator],  # ADK agents
    primary="validator",                     # Which agent's output to score
    share_session=True,                      # Pass state between agents
    trainset=examples,
)

# All three agents' instructions evolved together
for name, instruction in result.evolved_instructions.items():
    print(f"{name}: {instruction[:100]}...")
```

### 6. Workflow-as-Student

Automatically detect and evolve ADK workflow agents:

```python
from gepa_adk import evolve_workflow

# SequentialAgent, LoopAgent, or ParallelAgent
workflow = SequentialAgent(
    name="pipeline",
    sub_agents=[step1, step2, step3]
)

result = evolve_workflow(
    workflow=workflow,
    trainset=examples,
    max_depth=5,  # Recursively find nested LlmAgents
)
# All LlmAgent sub-agents evolved; workflow structure preserved
```

### 7. Multi-Component Evolution (Instruction + Schema)

GEPA's `components_to_update` mechanism supports evolving multiple text components simultaneously. `gepa-adk` leverages this for:

**A. Single-Agent with Schema Evolution**
```python
# Evolve both instruction AND output_schema together
result = evolve(
    agent=my_agent,
    trainset=examples,
    critic=critic_agent,
    evolve_schema=True,  # Include output_schema as component
)
# Returns both evolved_instruction and evolved_schema
```

Internal candidate structure:
```python
seed_candidate = {
    "instruction": "Original instruction...",
    "output_schema": '{"type": "object", "properties": {...}}'
}
# GEPA evolves both, proposing mutations to each
```

**B. Multi-Agent Co-Evolution**
```python
seed_candidate = {
    "generator_instruction": "Generate Playwright script...",
    "critic_instruction": "Evaluate script quality...",
    "validator_instruction": "Validate script runs..."
}
# Each agent's instruction is a component GEPA can mutate
```

**C. Schema Validation Service**
Evolved schemas are validated to ensure they:
- Are valid JSON
- Preserve required fields (`score`, `feedback` for critics)
- Fall back to original schema if validation fails

### 8. Workflow Critics (for Tool-Using Validators)

**Problem**: ADK's `output_schema` and `tools` are mutually exclusive on the same agent. Validators that use MCP tools (like Playwright for browser validation) can't return structured `{score, feedback}` directly.

**Solution**: A SequentialAgent pattern wrapping two sub-agents:

```yaml
# Workflow critic: validator-workflow
name: playwright-critic-workflow
agent_class: SequentialAgent
sub_agents:
  - name: playwright-validator  # Has MCP tools, saves to state
  - name: validation-scorer     # Reads state, has output_schema
```

```python
# CriticScorer auto-detects workflow critics
class CriticScorer:
    async def score(self, input_text, output, session_id):
        # Detect workflow critic (SequentialAgent, LoopAgent, ParallelAgent)
        critic_class = critic_agent.adk_config.get("agent_class")
        if is_workflow_agent(critic_class):
            # Execute full workflow; extract score from last sub-agent's output_key
            ...
```

The workflow extracts structured output from the final sub-agent's `output_key` in session state:

```
playwright-validator → saves validation results to state
validation-scorer    → reads state, returns {score: 0.8, feedback: "..."}
```

### 9. State Key Preservation

Safety layer preventing reflection models from breaking ADK state injection:

```python
from gepa_adk import StateGuard

guard = StateGuard(
    repair_missing=True,     # Re-append accidentally removed {tokens}
    escape_unauthorized=True # Convert new {tokens} to {{escaped}}
)

# Applied automatically during evolution
```

---

## Use Cases

### Use Case 1: Optimize a Video Analysis Agent

```python
from google.adk.agents import LlmAgent
from gepa_adk import evolve

agent = LlmAgent(
    name="video_analyzer",
    model="gemini-2.5-flash",
    instruction="Analyze the video and describe what you see."
)

examples = [
    {"input": "video_1.mp4", "expected": "User clicks login button..."},
    {"input": "video_2.mp4", "expected": "Form validation error appears..."},
]

result = evolve(agent, trainset=examples, max_iterations=30)
agent.instruction = result.evolved_instruction  # Apply improvement
```

### Use Case 2: Co-Evolve Generator + Critic

```python
from gepa_adk import evolve_group

generator = LlmAgent(name="generator", instruction="Generate a story...")
critic = LlmAgent(name="critic", instruction="Rate the story quality...")

result = evolve_group(
    agents=[generator, critic],
    primary="critic",  # Optimize for critic satisfaction
    trainset=story_prompts,
)
```

### Use Case 3: Evolve with Custom Scorer

```python
from gepa_adk import evolve, Scorer

class MyScorer(Scorer):
    def score(self, input: str, output: str, expected: str) -> tuple[float, dict]:
        # Custom scoring logic
        accuracy = compute_accuracy(output, expected)
        return accuracy, {"details": "..."}

result = evolve(agent, trainset=examples, scorer=MyScorer())
```

### Use Case 4: Notebook-Friendly Evolution

```python
# In Jupyter notebook
from gepa_adk import evolve, EvolutionConfig

config = EvolutionConfig(
    max_iterations=20,
    reflection_model="ollama/llama3:8b",
    verbose=True,  # Print progress
)

# Returns generator for streaming updates
for update in evolve(agent, trainset, config=config, stream=True):
    print(f"Iteration {update.iteration}: score={update.score:.3f}")
```

---

## Package Structure (ADR-000 Hexagonal)

```
gepa-adk/
├── src/
│   └── gepa_adk/
│       ├── __init__.py           # Public API: evolve, evolve_sync
│       │
│       ├── domain/               # 🏢 CORE - No external dependencies
│       │   ├── models.py         # EvolutionConfig, EvolutionResult
│       │   ├── exceptions.py     # EvolutionError hierarchy
│       │   └── types.py          # Type aliases, DTOs
│       │
│       ├── ports/                # 🔌 INTERFACES - Protocols
│       │   ├── adapter.py        # AsyncGEPAAdapter protocol
│       │   ├── scorer.py         # Scorer protocol
│       │   └── agent_provider.py # AgentProvider protocol
│       │
│       ├── adapters/             # 🔧 IMPLEMENTATIONS - ADK imports here
│       │   ├── adk_adapter.py    # ADKAdapter
│       │   ├── critic_scorer.py  # CriticScorer
│       │   └── workflow.py       # Workflow utilities
│       │
│       ├── engine/               # 🔄 ORCHESTRATION
│       │   ├── async_engine.py   # AsyncGEPAEngine
│       │   └── proposer.py       # Async proposer
│       │
│       └── utils/                # 🛠️ UTILITIES
│           ├── state_guard.py
│           ├── events.py
│           └── parsing.py
│
├── tests/                        # Three-layer testing (ADR-005)
│   ├── contracts/
│   ├── integration/
│   └── unit/
│
├── examples/
│   ├── basic_evolution.py
│   ├── multi_agent.py
│   └── notebooks/
│       └── getting_started.ipynb
│
├── pyproject.toml
└── README.md
```

**Layer Rules** (per ADR-000):
- `domain/` → imports nothing from `adapters/`
- `ports/` → imports only from `domain/`
- `adapters/` → imports from `ports/` + external libs (ADK, LiteLLM)
- `engine/` → imports from `ports/`, receives adapters via injection

---

## Dependencies

### Required
- `google-adk >= 1.21.0` - Agent execution, sessions, events
- `litellm >= 1.0.0` - Model abstraction (for reflection fallback)

### Optional
- `pyyaml` - YAML parsing for reflection output

### Dev Dependencies
- `pytest >= 8.0.0` - Testing framework
- `pytest-asyncio >= 0.24.0` - Async test support
- `pytest-cov >= 6.0.0` - Coverage reporting
- `ruff` - Linting and formatting

**Note**: We implement GEPA's core algorithm from scratch (not a fork) while referencing:
- `gepa-ai` in `.venv` for algorithm understanding and parity verification
- agent-workflow-suite's `adapters/gepa/` for our battle-tested ADK integration

**Why from scratch (not fork)?**
- Async-first implementation without sync bridges
- No dependency on GEPA's DSPy adapters we don't need
- Full control over evolution algorithm
- Clean repo history
- Clear Apache 2.0 attribution without fork complexity

---

## Comparison: Before & After

### Before (Custom Integration)

```python
# ~500+ lines of custom adapter code per project
class MyGEPAAdapter(GEPAAdapter):
    def evaluate(self, batch, candidate, capture_traces):
        # Manual ADK execution
        # Manual event extraction
        # Manual scoring
        # Manual trajectory building
        ...

    def make_reflective_dataset(self, candidate, eval_batch, components):
        # Manual dataset construction
        ...
```

### After (gepa-adk)

```python
from gepa_adk import evolve

result = evolve(agent, trainset, critic=critic_agent)
```

---

## Migration Path for agent-workflow-suite

### Development Setup

**New standalone repository** (not in agent-workflow-suite):
```
~/Projects/
├── agent-workflow-suite/        # Existing - reference for extraction
│   ├── src/agent_workflow_suite/adapters/gepa/  # Our ADK integration
│   ├── .venv/lib/.../gepa/      # GEPA source for algorithm reference
│   └── GEPA_ADK_PACKAGE_PROPOSAL.md  # This proposal (stays here)
│
└── gepa-adk/                    # NEW standalone repo
    ├── src/gepa_adk/
    ├── tests/
    └── pyproject.toml
```

**Local development integration**:
```toml
# agent-workflow-suite/pyproject.toml (during development)
[tool.uv.sources]
gepa-adk = { path = "../gepa-adk", editable = true }
```

**Validation milestone**: When agent-workflow-suite can swap `adapters/gepa/` imports for `gepa_adk` imports and all tests pass.

---

### Phase 1: Async Core Engine
1. Create `gepa-adk` repository with async-first architecture
2. Implement GEPA core algorithm from scratch (~1,000 lines equivalent) as async:
   - `AsyncGEPAEngine` with `async def run()`
   - `AsyncGEPAAdapter` protocol
   - `AsyncReflectiveMutationProposer`
3. Basic tests with mock async adapter

### Phase 2: ADK Integration (Week 2)
1. Port `ADKGEPAAdapter` from agent-workflow-suite, converting to native async
2. Port `CriticScorer` with async `score()` method
3. Port ADK reflection agent support (`create_adk_reflection_fn`)
4. Remove `run_async()` bridge - direct `await` everywhere
5. Integration tests with real ADK agents

### Phase 3: Concurrent Evaluation & Features (Week 3)
1. Add semaphore-controlled parallel batch evaluation
2. Benchmark and tune concurrency (expect 3-5x speedup)
3. Port remaining features:
   - Multi-agent co-evolution
   - Workflow-as-student detection
   - Schema evolution
   - State key preservation
4. Add `TrajectoryConfig` for event capture options

### Phase 4: Package & Migrate (Week 4)
1. Finalize package structure and public API
2. Add `evolve_sync()` compatibility wrapper
3. **Migrate agent-workflow-suite**:
   ```python
   # Before (internal)
   from agent_workflow_suite.adapters.gepa import ADKGEPAOptimizer

   # After (external package)
   from gepa_adk import evolve, EvolutionConfig
   ```
4. Remove `adapters/gepa/` from agent-workflow-suite (~5,000 lines)
5. Keep only thin integration layer (DB persistence, CLI)
6. Verify all existing tests pass

### Phase 5: Documentation & Release (Week 5)
1. Write comprehensive documentation
2. Create example notebooks (Jupyter, Colab)
3. Publish to PyPI as `gepa-adk`
4. Announce to GEPA and ADK communities
5. Submit PR to GEPA docs linking to gepa-adk

### Code Reduction in agent-workflow-suite

| Before | After | Savings |
|--------|-------|---------|
| `adapters/gepa/` (~5,000 lines) | ~200 lines (thin integration) | **~4,800 lines** |
| Custom `run_async()` bridge | Removed (native async) | Cleaner code |
| Duplicated types/configs | Import from `gepa-adk` | Single source of truth |

---

## API Design Principles

### 1. Progressive Disclosure
```python
# Simple case - one line
result = evolve(agent, trainset)

# Advanced case - full control
result = evolve(
    agent=agent,
    trainset=trainset,
    valset=valset,
    critic=critic,
    config=EvolutionConfig(...),
    trajectory_config=TrajectoryConfig(...),
    state_guard=StateGuard(...),
)
```

### 2. Protocol-Based Extension
```python
from gepa_adk import Scorer, AgentProvider

# Users can implement custom scorers
class MyScorer(Scorer):
    def score(self, input, output, expected) -> tuple[float, dict]: ...

# Users can implement custom agent loading
class MyAgentProvider(AgentProvider):
    def get_agent(self, name: str) -> LlmAgent: ...
    def save_instruction(self, name: str, instruction: str): ...
```

### 3. ADK-Native Types
```python
# Input/output uses ADK types directly
from google.adk.agents import LlmAgent
from google.adk.sessions import Session

# No wrapper types - work with ADK directly
agent: LlmAgent = ...
result = evolve(agent, trainset)
```

---

## Async-First Architecture

### Why Async-First?

ADK is fundamentally async. The current agent-workflow-suite bridges sync GEPA to async ADK with `asyncio.run()`:

```python
# Current: Blocking bridge (creates new event loop per call!)
def run_async(coro):
    return asyncio.run(coro)

result = run_async(executor.execute_agent(...))  # Blocks, inefficient
```

**`gepa-adk` will be async-native**, eliminating this impedance mismatch.

### GEPA Core Size Assessment

GEPA is surprisingly small—only ~1,000 lines of core logic need conversion:

| Component | Lines | Conversion Effort |
|-----------|-------|-------------------|
| `core/engine.py` | 325 | `async def run()` |
| `core/adapter.py` | 179 | Async protocol |
| `api.py` | 349 | `async def optimize()` |
| `proposer/reflective_mutation.py` | 165 | `async def propose()` |
| **Total Core** | **~1,000** | Manageable |

The remaining ~5,300 lines are adapters (DSPy, RAG) and examples we don't need.

### Async Protocol Design

```python
from typing import Protocol, TypeVar, Mapping, Sequence, Any

DataInst = TypeVar("DataInst")
Trajectory = TypeVar("Trajectory")
RolloutOutput = TypeVar("RolloutOutput")

class AsyncGEPAAdapter(Protocol[DataInst, Trajectory, RolloutOutput]):
    """Async-first GEPA adapter protocol for ADK integration."""

    async def evaluate(
        self,
        batch: list[DataInst],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Trajectory, RolloutOutput]:
        """Execute candidate on batch - can await ADK calls directly."""
        ...

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Build reflective dataset - can await critic scoring."""
        ...

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Propose new instructions - can await ADK reflection agent."""
        ...
```

### Async Engine

```python
class AsyncGEPAEngine:
    """Async-first evolution engine."""

    async def run(self) -> GEPAState:
        state = await self._initialize_state()

        while not self._should_stop(state):
            # Async evaluation - no blocking!
            eval_batch = await self.adapter.evaluate(
                batch, candidate, capture_traces=True
            )

            # Async proposal via ADK reflection agent
            proposal = await self.reflective_proposer.propose(state)

            if proposal and self._should_accept(proposal):
                await self._run_full_eval_and_add(proposal, state)

        return state
```

### Concurrent Batch Evaluation (Key Performance Win)

```python
async def evaluate(self, batch: list[DataInst], candidate: dict[str, str], ...):
    """Evaluate batch with controlled concurrency."""
    semaphore = asyncio.Semaphore(self.config.max_concurrent_evals)  # e.g., 5

    async def eval_one(example: DataInst) -> tuple[RolloutOutput, float, Trajectory]:
        async with semaphore:
            result = await self.executor.execute_agent(
                agent_name=self.agent_name,
                input_text=example["input"],
                instruction_override=candidate.get("instruction"),
            )
            score, feedback = await self.critic_scorer.score(
                example["input"], result.output, result.session_id
            )
            return result.output, score, self._build_trajectory(result, feedback)

    # Parallel evaluation with rate limiting
    results = await asyncio.gather(*[eval_one(ex) for ex in batch])
    outputs, scores, trajectories = zip(*results)

    return EvaluationBatch(
        outputs=list(outputs),
        scores=list(scores),
        trajectories=list(trajectories),
    )
```

**Performance Impact**: For a batch of 10 examples with 30s per evaluation:
- Sequential (current): 10 × 30s = **300s**
- Concurrent (5 parallel): 2 × 30s = **60s** (5x faster)

### Async Reflection with ADK Agent

```python
async def propose_new_texts(
    self,
    candidate: dict[str, str],
    reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
    components_to_update: list[str],
) -> dict[str, str]:
    """Use ADK agent for reflection instead of raw litellm."""
    new_texts = {}

    for component_name in components_to_update:
        dataset = reflective_dataset.get(component_name, [])
        if not dataset:
            continue

        # Inject reflective dataset into session state
        session_state = {
            "current_instruction": candidate[component_name],
            "reflective_dataset": json.dumps(dataset),
        }

        # Execute ADK reflection agent (async!)
        result = await self.executor.execute_agent(
            agent_name=self.reflection_agent_name,
            input_text="Propose an improved instruction based on the feedback.",
            session_state=session_state,
        )

        new_texts[component_name] = result.extracted_value

    return new_texts
```

### Async LiteLLM (for non-ADK reflection fallback)

```python
# Current GEPA (sync)
completion = litellm.completion(model=model, messages=messages)

# gepa-adk (async)
completion = await litellm.acompletion(model=model, messages=messages)
```

### Public API

```python
# Simple async API
from gepa_adk import evolve

async def main():
    result = await evolve(
        agent=my_adk_agent,
        trainset=examples,
        critic=critic_agent,
        reflection_agent=reflection_agent,  # ADK-first!
        max_iterations=50,
    )
    print(f"Evolved: {result.evolved_instruction}")

asyncio.run(main())

# Or with sync wrapper for CLI convenience
from gepa_adk import evolve_sync

result = evolve_sync(agent, trainset, critic=critic)  # Wraps asyncio.run() once at top level
```

### Integration with agent-workflow-suite

After extracting `gepa-adk`, agent-workflow-suite becomes a consumer:

```python
# agent-workflow-suite/src/.../cli/gepa/evolve.py
from gepa_adk import evolve, EvolutionConfig, TrajectoryConfig

async def run_evolution(agent_name: str, ...):
    # Load agent from database (agent-workflow-suite specific)
    with uow:
        agent = uow.agents.get_by_name(agent_name)
        adk_agent = build_adk_agent(agent)  # Your existing builder

    # Use gepa-adk for evolution (generic)
    result = await evolve(
        agent=adk_agent,
        trainset=examples,
        critic=critic_agent,
        config=EvolutionConfig(max_iterations=50),
    )

    # Persist back to database (agent-workflow-suite specific)
    with uow:
        update_agent_field_atomically(agent, "instruction", result.evolved_instruction)
        uow.commit()
```

**Separation of Concerns**:
- `gepa-adk`: Generic async evolution engine for any ADK agent
- `agent-workflow-suite`: Database persistence, YAML loading, CLI commands

### Compatibility Layer

For users who need sync (scripts, notebooks without async):

```python
# gepa_adk/_compat.py
import asyncio
from functools import wraps

def evolve_sync(agent, trainset, **kwargs):
    """Synchronous wrapper for evolve().

    Use this in scripts/notebooks where async isn't convenient.
    For CLI commands, prefer the async version with proper event loop management.
    """
    return asyncio.run(evolve(agent, trainset, **kwargs))

# Also expose as top-level for convenience
# from gepa_adk import evolve_sync
```

---

## Testing Strategy (ADR-005)

Three-layer testing aligned with hexagonal architecture:

```
┌─────────────────────────────────────────────────────────┐
│ Contract Tests (tests/contracts/)                       │
│ • Verify protocols are correctly defined                │
│ • Ensure adapters implement ports                       │
│ • Mock ADK for speed                                    │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ Integration Tests (tests/integration/)                  │
│ • End-to-end evolution with real ADK agents             │
│ • Real LLM calls (marked @pytest.mark.slow)             │
│ • Verify async concurrency works                        │
└─────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────┐
│ Unit Tests (tests/unit/)                                │
│ • Engine logic with mock adapter                        │
│ • State guard, parsing utilities                        │
│ • No I/O, fastest execution                             │
└─────────────────────────────────────────────────────────┘
```

### Contract Tests

```python
# tests/contracts/test_adapter_protocol.py
from typing import runtime_checkable
from gepa_adk.ports import AsyncGEPAAdapter
from gepa_adk.adapters import ADKAdapter

def test_adk_adapter_implements_protocol():
    """ADKAdapter must implement AsyncGEPAAdapter protocol."""
    assert isinstance(ADKAdapter(...), AsyncGEPAAdapter)

def test_protocol_methods_are_async():
    """All adapter methods must be coroutines."""
    import inspect
    assert inspect.iscoroutinefunction(ADKAdapter.evaluate)
    assert inspect.iscoroutinefunction(ADKAdapter.make_reflective_dataset)
```

### Unit Tests (Mock Adapter)

```python
# tests/unit/test_engine.py
import pytest
from pytest_mock import MockerFixture
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.domain.models import EvaluationBatch

@pytest.fixture
def mock_adapter(mocker: MockerFixture):
    """Mock adapter for unit tests - no ADK dependency."""
    adapter = mocker.AsyncMock()
    adapter.evaluate.return_value = EvaluationBatch(
        outputs=["output1", "output2"],
        scores=[0.8, 0.9],
        trajectories=[{}, {}],
    )
    return adapter

@pytest.mark.asyncio
async def test_engine_accepts_improved_candidate(mock_adapter):
    """Engine accepts candidates with higher scores."""
    engine = AsyncGEPAEngine(adapter=mock_adapter, ...)
    state = await engine.run()
    assert state.best_score > 0.8
```

### Integration Tests

```python
# tests/integration/test_adk_evolution.py
import pytest
from google.adk.agents import LlmAgent
from gepa_adk import evolve

@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.asyncio
async def test_evolve_improves_instruction():
    """End-to-end: evolution improves agent instruction."""
    agent = LlmAgent(
        name="test_agent",
        model="gemini-2.5-flash",
        instruction="Answer the question.",
    )
    critic = LlmAgent(
        name="critic",
        model="gemini-2.5-flash",
        instruction="Rate the answer quality from 0 to 1.",
        output_schema={"type": "object", "properties": {"score": {"type": "number"}}}
    )

    result = await evolve(
        agent=agent,
        trainset=[{"input": "What is 2+2?", "expected": "4"}],
        critic=critic,
        max_iterations=5,
    )

    assert result.final_score >= result.original_score
    assert result.evolved_instruction != agent.instruction
```

### Test Markers

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Fast, isolated unit tests",
    "contract: Interface compliance tests",
    "integration: Real ADK/LLM tests",
    "slow: Tests taking >10s (LLM calls)",
]
addopts = "-m 'not slow'"  # Skip slow by default
```

### Test Directory Structure

```
tests/
├── conftest.py              # Shared fixtures (mock adapter, fake scorer)
├── contracts/
│   ├── test_adapter_protocol.py
│   ├── test_scorer_protocol.py
│   └── test_agent_provider_protocol.py
├── integration/
│   ├── conftest.py          # Real ADK fixtures
│   ├── test_adk_evolution.py
│   ├── test_concurrent_evaluation.py
│   └── test_multi_agent.py
└── unit/
    ├── test_engine.py
    ├── test_proposer.py
    ├── test_state_guard.py
    └── test_parsing.py
```

---

## Feature Prioritization

### Tier 1: Core Package (MVP)
These features are battle-tested in agent-workflow-suite and ready for extraction:

| Feature | Complexity | Value | Status |
|---------|------------|-------|--------|
| ADKGEPAAdapter (GEPA protocol) | Medium | Critical | ✅ Implemented |
| Critic agents with structured feedback | Medium | High | ✅ Implemented |
| ADK-first reflection agent | Low | High | ✅ Implemented |
| Trajectory capture from ADK sessions | Medium | High | ✅ Implemented |
| State key preservation | Low | Medium | ✅ Implemented |

### Tier 2: Advanced Features (Post-MVP)
Implemented but may need refinement for standalone package:

| Feature | Complexity | Value | Status |
|---------|------------|-------|--------|
| Multi-agent co-evolution | High | High | ✅ Implemented |
| Workflow-as-student detection | High | High | ✅ Implemented |
| Schema evolution (instruction + output_schema) | Medium | Medium | ✅ Implemented |
| Workflow critics (tool-using validators) | Medium | Medium | ✅ Implemented |

### Tier 3: Roadmap (Future)
Ideas validated in agent-workflow-suite but not yet implemented:

| Feature | Complexity | Value | Notes |
|---------|------------|-------|-------|
| **YAML agent definition evolution** | High | Very High | Evolve full ADK config (model, tools, sub_agents) not just instruction. YAML validator already exists. ADK supports YAML config natively. |
| Tool configuration evolution | Medium | Medium | Evolve MCP tool parameters alongside instructions |
| Sub-agent composition evolution | Very High | High | Evolve workflow structure (add/remove/reorder sub-agents) |
| Evolution checkpointing | Medium | Medium | Save/restore evolution state for long-running jobs |
| Distributed evolution | High | Medium | Run evaluations across multiple workers |

### Vision: Beyond Instruction Refinement

`gepa-adk` aims to evolve from a "system instruction prompt refiner" to a **full agent definition optimizer**:

```
Current (Tier 1-2):        Future (Tier 3):
┌─────────────────┐        ┌─────────────────────────────┐
│ Evolve:         │        │ Evolve:                     │
│ - instruction   │   ──>  │ - instruction               │
│ - output_schema │        │ - output_schema             │
└─────────────────┘        │ - model selection           │
                           │ - tool configurations       │
                           │ - sub_agent composition     │
                           │ - planner type              │
                           └─────────────────────────────┘
```

This is achievable because:
1. Agent-workflow-suite already has YAML validation infrastructure
2. ADK agents are defined declaratively (YAML/dict configs)
3. GEPA's text mutation approach works on any structured text (YAML, JSON)
4. Critic agents can evaluate any aspect of agent behavior

---

## Open Questions

### 1. Package Name
- `gepa-adk` - Clear, describes the bridge *(recommended)*
- `adk-evolution` - Focuses on ADK side
- `agent-evolver` - Generic, but less discoverable

### 2. Session Management
- Should the package manage ADK sessions internally? *(recommended: yes, with sensible defaults)*
- Or require users to provide session configuration?
- Default: `InMemorySessionService`, configurable to `DatabaseSessionService`

### 3. Model Configuration
- Reflection model configurable per-evolution via `EvolutionConfig.reflection_model`
- LiteLLM prefix handling (e.g., `ollama_chat/llama3`) - pass through as-is
- **Open**: Should we validate model availability before evolution starts?

### 4. Persistence Strategy
- **Decided**: Return results, let user persist (no auto-save)
- `AgentProvider` protocol for optional persistence integration
- **Open**: Should we provide a `FileAgentProvider` for simple YAML persistence?

### 5. GEPA Upstream Relationship
- **Decided**: Implement from scratch (not a fork), reference `.venv/gepa` for parity
- **Decided**: Credit GEPA prominently (Apache 2.0 attribution in LICENSE and README)
- **Open**: Should we contribute async learnings back to GEPA upstream later?
- **Open**: How to track GEPA algorithm changes for potential incorporation?

### 6. License
- GEPA is Apache 2.0, ADK is Apache 2.0
- **Recommended**: Apache 2.0 for gepa-adk (compatible with both)

---

## Success Metrics

1. **Adoption**: 100+ GitHub stars in first 6 months
2. **Integration**: Used by 3+ production ADK projects
3. **Contribution**: PRs from GEPA and ADK communities
4. **Documentation**: Complete API docs + 5 example notebooks
5. **Test Coverage**: >90% coverage on core modules

---

## Next Steps

1. [ ] Finalize this proposal (done - this document)
2. [ ] Create new `gepa-adk` repository with initial structure
3. [ ] Create GitHub issues for Phase 1 (Async Core Engine)
4. [ ] Implement core async engine with GEPA algorithm parity
5. [ ] Create GitHub issues for Phase 2 (ADK Integration)
6. [ ] Port ADK adapter, critic scorer from agent-workflow-suite
7. [ ] Validate: swap into agent-workflow-suite, run tests
8. [ ] Create GitHub issues for Phase 3+ (advanced features)
9. [ ] Write documentation and examples
10. [ ] Public release on PyPI
11. [ ] Announce to GEPA/ADK communities

---

## Appendix A: Code Reference Map

### Reference Sources

| Source | Location | Purpose |
|--------|----------|---------|
| GEPA algorithm | `.venv/lib/.../gepa/core/` | Algorithm parity reference |
| ADK integration | `src/.../adapters/gepa/` | Battle-tested ADK patterns |
| Evolution models | `src/.../domain/models/evolution.py` | DTO patterns |
| Port interface | `src/.../ports/services/evolution_interface.py` | Protocol patterns |

### Mapping to Hexagonal Structure (gepa-adk)

| Source (agent-workflow-suite) | Target (gepa-adk) | Layer | Notes |
|-------------------------------|-------------------|-------|-------|
| `domain/models/evolution.py` | `domain/models.py` | Domain | Keep DTOs, add async types |
| — (new) | `domain/exceptions.py` | Domain | EvolutionError hierarchy (ADR-009) |
| `ports/services/evolution_interface.py` | `ports/adapter.py` | Ports | Convert to async Protocol |
| — (new) | `ports/scorer.py` | Ports | Extract Scorer protocol |
| — (new) | `ports/agent_provider.py` | Ports | New protocol for persistence |
| `adapters/gepa/adapter.py` | `adapters/adk_adapter.py` | Adapters | Remove UoW, convert to async |
| `adapters/gepa/scoring.py` | `adapters/critic_scorer.py` | Adapters | Generalize, async |
| `adapters/gepa/workflow_student.py` | `adapters/workflow.py` | Adapters | Remove DB lookups |
| `adapters/gepa/optimizer.py` | `engine/async_engine.py` | Engine | Fork GEPA core, async |
| `adapters/gepa/proposal_factory.py` | `engine/proposer.py` | Engine | Async proposer |
| `adapters/gepa/reflection_agent.py` | `engine/proposer.py` | Engine | Merge ADK reflection |
| `adapters/gepa/event_extraction.py` | `utils/events.py` | Utils | Keep as-is |
| `adapters/gepa/state_key_preservation.py` | `utils/state_guard.py` | Utils | Keep as-is |
| `adapters/gepa/parsing.py` | `utils/parsing.py` | Utils | Keep as-is |
| `adapters/gepa/multi_agent.py` | `adapters/adk_adapter.py` | Adapters | Merge into adapter |

### Files to NOT Extract (agent-workflow-suite specific)

| File | Reason |
|------|--------|
| `adapters/gepa/async_utils.py` | `run_async()` bridge no longer needed |
| `cli/gepa/evolve.py` | CLI stays in agent-workflow-suite |
| Database models | agent-workflow-suite owns persistence |

---

## Appendix B: Competitive Landscape

| Tool | Strengths | Gaps |
|------|-----------|------|
| **DSPy** | Mature, many optimizers, GEPA integration | Not ADK-native, different paradigm |
| **PromptFoo** | Great eval framework | No evolutionary optimization |
| **LangSmith** | Excellent tracing | No automatic prompt improvement |
| **Raw GEPA** | Powerful optimization engine | Mechanical scoring, no ADK integration |
| **gepa-adk** (proposed) | ADK-native, critic agents with feedback, session state | New, smaller community |

### Key Differentiator: Critic Feedback Loop

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GEPA Default vs gepa-adk                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  GEPA Default:                                                          │
│  ┌──────────┐   execute    ┌──────────┐   score=0.7   ┌──────────────┐ │
│  │Generator │─────────────▶│ Output   │─────────────▶│ Reflection LM │ │
│  └──────────┘              └──────────┘   (that's it) └──────────────┘ │
│                                                                         │
│  gepa-adk (ADK-First):                                                  │
│  ┌──────────┐   execute    ┌──────────┐   structured  ┌──────────────┐ │
│  │Generator │─────────────▶│ Output   │──────────────▶│ Critic Agent │ │
│  │(ADK)     │              └──────────┘               │ (ADK + schema)│ │
│  └──────────┘                                         └───────┬──────┘ │
│                                                               │        │
│                                          {score: 0.7,         │        │
│                                           feedback: "...",    ▼        │
│  ┌────────────────┐   improved    ┌───────────────────────────────────┐│
│  │Evolved Agent   │◀──────────────│ Reflection Agent (ADK)            ││
│  └────────────────┘  instruction  │ with rich feedback context        ││
│                                   └───────────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix C: Example Evolved Instructions

### Before Evolution
```
Analyze the video and describe what you see.
```

### After 50 Iterations with Critic Feedback
```
Analyze the provided screen recording with focus on:
1. User interface elements and their state changes
2. User interactions (clicks, typing, scrolling)
3. System responses and feedback messages
4. Error states or validation failures
5. Workflow completion indicators

Structure your analysis as:
- **Action**: What the user did
- **Element**: UI component involved
- **Result**: System response
- **Timestamp**: Approximate time in video

Be precise about button labels, form fields, and error messages.
Use the exact text visible on screen when quoting UI elements.
```

---

## Sources

### GEPA
- [GEPA GitHub Repository](https://github.com/gepa-ai/gepa) - Official implementation
- [GEPA Paper (arXiv)](https://arxiv.org/abs/2507.19457) - "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning"
- [GEPA PyPI Package](https://pypi.org/project/gepa/)
- [DSPy GEPA Integration](https://dspy.ai/api/optimizers/GEPA/overview/)

### Google ADK
- [ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Python GitHub](https://github.com/google/adk-python)
- [ADK Python API Reference](https://google.github.io/adk-docs/api-reference/python/)
- [ADK PyPI Package](https://pypi.org/project/google-adk/)
- [Google Cloud ADK Overview](https://docs.cloud.google.com/agent-builder/agent-development-kit/overview)

### Related Work
- [DSPy Framework](https://dspy.ai/) - Declarative prompting framework with GEPA optimizer
- [Future AGI GEPA Documentation](https://docs.futureagi.com/future-agi/get-started/optimization/optimizers/gepa)

---

*This document is a living proposal. Feedback welcome.*
