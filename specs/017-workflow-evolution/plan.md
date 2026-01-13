# Implementation Plan: Workflow Agent Evolution

**Branch**: `017-workflow-evolution` | **Date**: 2026-01-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/017-workflow-evolution/spec.md`

## Summary

Implement `evolve_workflow()` function to evolve ADK workflow agents (SequentialAgent, LoopAgent, ParallelAgent) by recursively finding all nested LlmAgents and evolving them together while preserving the workflow structure. This builds on the existing `evolve_group()` function and integrates with the multi-agent adapter architecture.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: google-adk 1.22.0 (SequentialAgent, LoopAgent, ParallelAgent, LlmAgent, BaseAgent)  
**Reference**: gepa 0.0.24 (dev dependency for architectural patterns)  
**Storage**: N/A (in-memory evolution)  
**Testing**: pytest with three-layer testing (contract, unit, integration)  
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: Single project (hexagonal architecture)  
**Performance Goals**: Workflow traversal adds <10% overhead to evolution time  
**Constraints**: Max recursion depth configurable (default: 5), no modification to workflow structure  
**Scale/Scope**: Workflows with up to 100 nested agents, 5 levels deep

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Hexagonal Architecture** | ✅ PASS | Workflow utilities go in `adapters/workflow.py`, public API in `api.py`. ADK imports isolated to adapters layer only. |
| **II. Async-First Design** | ✅ PASS | `evolve_workflow()` is async, delegates to async `evolve_group()`. No sync/async bridging needed. |
| **III. Protocol-Based Interfaces** | ✅ PASS | No new protocols needed—reuses existing `Scorer` protocol and `evolve_group()` infrastructure. |
| **IV. Three-Layer Testing** | ✅ PASS | Contract tests for type detection, unit tests for `find_llm_agents()`, integration tests for full workflow evolution. |
| **V. Observability & Documentation** | ✅ PASS | Google-style docstrings, structlog logging for workflow traversal, exception hierarchy for errors. |

**Pre-Phase 0 Gate**: ✅ PASSED

## Project Structure

### Documentation (this feature)

```text
specs/017-workflow-evolution/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── gepa_adk/
│   ├── api.py           # Add evolve_workflow() public function
│   ├── adapters/
│   │   ├── workflow.py  # NEW: Workflow detection and traversal utilities
│   │   └── multi_agent.py  # Existing (reused via evolve_group)
│   ├── domain/
│   │   ├── exceptions.py   # Add WorkflowEvolutionError
│   │   └── models.py       # Existing (EvolutionResult, EvolutionConfig)
│   └── ports/
│       └── scorer.py       # Existing (Scorer protocol)

tests/
├── contracts/
│   └── test_workflow_contract.py  # Type detection contracts
├── integration/
│   └── test_workflow_integration.py  # Real ADK workflow tests
└── unit/
    └── test_workflow.py           # Unit tests for traversal
```

**Structure Decision**: Single project following existing hexagonal architecture. Workflow utilities are added to a new `adapters/workflow.py` file to isolate ADK-specific imports while maintaining the established layer boundaries.

## Complexity Tracking

> No violations identified. All constitution principles are satisfied by the design.
