# Data Model: MergeProposer

## Entities

### Candidate (Extended)

Extends the existing `Candidate` dataclass to support multi-parent tracking.

**Backward Compatibility**: The new `parent_ids` field extends (not replaces) the existing `parent_id` field. Existing code using `parent_id` continues to work unchanged.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| components | `dict[str, str]` | Component name → instruction text | Non-empty |
| generation | `int` | Generation number in evolution | >= 0 |
| parent_id | `str \| None` | Legacy single parent reference (retained for compatibility) | Optional |
| parent_ids | `list[int] \| None` | **NEW**: Multi-parent indices for merge | Optional, len 1-2 |
| metadata | `dict[str, Any]` | Extensible metadata | Optional |

**State Transitions**:
- Seed candidate: `parent_ids = None` or `[None]`
- Mutated candidate: `parent_ids = [single_parent_idx]`
- Merged candidate: `parent_ids = [parent1_idx, parent2_idx]`

### ParetoState (Extended)

Extends the existing `ParetoState` dataclass to track genealogy.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| candidates | `list[Candidate]` | All discovered candidates | Existing |
| candidate_scores | `dict[int, dict[int, float]]` | Per-example scores | Existing |
| frontier | `ParetoFrontier` | Current frontier | Existing |
| **parent_indices** | `dict[int, list[int \| None]]` | **NEW**: Genealogy map | Valid indices |

### ProposalResult

New frozen dataclass for proposal outcomes.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| candidate | `Candidate` | Proposed candidate | Required |
| parent_indices | `list[int]` | Parent candidate indices | 1-2 elements |
| tag | `str` | Proposal type ("mutation" or "merge") | Non-empty |
| metadata | `dict[str, Any]` | Additional proposal metadata | Optional |

### MergeAttempt

Type alias for merge attempt results.

```python
MergeAttempt = tuple[Candidate, int, int, int] | None
# (merged_candidate, parent1_idx, parent2_idx, ancestor_idx) or None
```

### AncestorLog

Type alias for tracking attempted merges.

```python
AncestorLog = tuple[int, int, int]
# (parent1_idx, parent2_idx, ancestor_idx)
```

## Relationships

```
ParetoState
    │
    ├── candidates: list[Candidate]
    │       │
    │       └── parent_ids → [candidate_idx, ...]
    │
    ├── parent_indices: dict[int, list[int | None]]
    │       │
    │       └── candidate_idx → [parent1_idx, parent2_idx] or [None]
    │
    └── frontier: ParetoFrontier
            │
            └── example_leaders → {candidate_idx, ...}
```

## Component Map

Instruction components that can be merged:

| Component Key | Description | Example |
|---------------|-------------|---------|
| `instruction` | Main agent instruction | "Be helpful and concise" |
| `system_instruction` | System-level prompt | "You are an expert assistant" |
| `task_instruction` | Task-specific guidance | "Analyze the code for bugs" |
| `output_schema` | Output format specification | JSON schema string |

## Validation Rules

### Candidate Validation

1. `components` must contain at least `instruction` key
2. `parent_ids` when set must contain valid candidate indices
3. `generation` must equal max(parent generations) + 1 for derived candidates

### ParetoState Validation

1. `parent_indices` keys must be valid candidate indices
2. Parent indices in values must reference existing candidates or be None
3. No circular ancestry (candidate cannot be its own ancestor)

### ProposalResult Validation

1. `tag` must be one of: "mutation", "merge"
2. `parent_indices` length must match tag (1 for mutation, 2 for merge)
3. All parent indices must be valid

## Evolution State Machine

```
[Seed Candidate]
      │
      ▼
[Mutation Proposal] ──────────────────────────┐
      │                                        │
      ▼                                        │
[Evaluated Candidate]                          │
      │                                        │
      ├── accepted ──► [New Best] ─────────────┤
      │                     │                  │
      │                     ▼                  │
      │               [Schedule Merge]         │
      │                     │                  │
      │                     ▼                  │
      │               [Merge Proposal]         │
      │                     │                  │
      │                     ▼                  │
      │               [Evaluated Merge]        │
      │                     │                  │
      │                     ├── accepted ──────┤
      │                     │                  │
      │                     └── rejected ──────┤
      │                                        │
      └── rejected ────────────────────────────┘
                            │
                            ▼
                    [Next Iteration]
```
