# ADR-014: Adapter Layer Reorganization into Sub-Packages

> **Status**: Accepted
> **Date**: 2026-03-02
> **Deciders**: gepa-adk maintainers

## Context

The `adapters/` directory grew to 11 modules (plus the `stoppers/` sub-package) in a flat layout. Contributors had to scan the entire directory to find the right module, and the single-level structure gave no hint about which modules were related. As more adapters are planned (critic presets, additional selection strategies, media handlers), the flat layout would only get worse.

## Decision

Reorganize `adapters/` into 7 concern-based sub-packages while preserving full backward compatibility through re-exports in `adapters/__init__.py`:

```
adapters/
├── __init__.py          # Re-exports preserving old import paths
├── execution/           # AgentExecutor, TrialBuilder
├── scoring/             # CriticScorer, schemas, normalize_feedback
├── evolution/           # ADKAdapter, MultiAgentAdapter
├── selection/           # Candidate selectors, component selectors, evaluation policies
├── components/          # ComponentHandlerRegistry, built-in handlers
├── workflow/            # is_workflow_agent, find_llm_agents, clone utilities
├── media/               # VideoBlobService
└── stoppers/            # (unchanged — already a sub-package)
```

Each sub-package has an `__init__.py` with:

- A docstring explaining purpose and anticipated growth
- Imports and re-exports of its public symbols via `__all__`

The root `adapters/__init__.py` re-exports all 33 previously-importable symbols from their new sub-package locations, ensuring `from gepa_adk.adapters import X` continues to work.

## Rationale

- **Cognitive load**: Grouping by concern (execution, scoring, selection, etc.) makes it obvious where to find or add an adapter
- **Scalability**: New adapters have a clear target directory (e.g., a new scorer goes in `scoring/`)
- **Architecture alignment**: Sub-packages mirror the domain concepts (evaluation, selection, execution) rather than implementation details
- **Zero breakage**: Re-exports in `adapters/__init__.py` mean existing code using `from gepa_adk.adapters import X` works unchanged

## Consequences

### Positive

- **Navigation**: 7 focused sub-packages vs 11 flat modules
- **Discoverability**: New contributors can find the right package by concern
- **Growth path**: Each sub-package can grow independently without polluting siblings
- **Pattern 1 alignment**: The New Adapter Recipe from the architecture doc now targets `adapters/{concern}/` paths

### Negative

- **Deeper paths**: Direct imports are longer (e.g., `from gepa_adk.adapters.selection.candidate_selector import ...`)
- **One-time migration**: All internal and test imports were updated in this change

### Neutral

- **Re-export maintenance**: `adapters/__init__.py` must be updated when adding new public symbols to sub-packages

## Migration

- **Backward-compatible**: `adapters/__init__.py` re-exports every previously-importable symbol
- **Deprecation tests**: `tests/unit/adapters/test_adapter_reexports.py` verifies all 33 re-exports resolve to the same objects as their sub-package counterparts
- **Stoppers untouched**: The existing `stoppers/` sub-package was not modified
