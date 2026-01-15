# Research: MergeProposer Implementation

## 1. GEPA MergeProposer Analysis

### Decision: Adapt upstream GEPA MergeProposer pattern for async-first gepa-adk

**Rationale**: The upstream GEPA implementation (gepa/proposer/merge.py) provides a well-tested merge algorithm that:
1. Finds common ancestors between candidates
2. Identifies which components each descendant modified
3. Combines the best components from each parent

**Alternatives considered**:
- Custom merge algorithm: Rejected because GEPA's algorithm has been proven effective in production
- Simple random crossover: Rejected because it doesn't leverage genealogy information

### Key Patterns from Upstream GEPA

1. **Parent Tracking**: `parent_program_for_candidate: list[list[ProgramIdx | None]]`
   - Each candidate stores a list of parent indices
   - Seed candidates have `[None]`
   - Mutated candidates have single parent `[parent_idx]`
   - Merged candidates have two parents `[parent1_idx, parent2_idx]`

2. **Common Ancestor Algorithm**: `find_common_ancestor_pair()`
   - Recursively traverses parent chains to find all ancestors
   - Identifies common ancestors between two candidates
   - Filters ancestors by merge viability (score constraints, predictor differences)

3. **Component Merging Logic**: `sample_and_attempt_merge_programs_by_common_predictors()`
   - For each component (predictor):
     - If one parent has ancestor's value and other has different → take different
     - If both parents differ from ancestor → take higher-scoring parent's value
     - If both parents have same value → take either (they're identical)

4. **Merge Scheduling**: `schedule_if_needed()` + `merges_due` counter
   - Engine triggers merge after successful mutation
   - Prevents merge spam by limiting invocations

## 2. Genealogy Tracking Design

### Decision: Extend ParetoState with parent tracking

**Rationale**: The existing `ParetoState` class already tracks candidates and their scores. Adding parent tracking here keeps genealogy co-located with candidate metadata.

**Alternatives considered**:
- Separate GenealogyState class: Rejected to avoid state synchronization complexity
- Track in Candidate.metadata: Rejected because metadata is unstructured

### Implementation Approach

1. **Candidate Model Extension**:
   ```python
   @dataclass
   class Candidate:
       components: dict[str, str]
       generation: int = 0
       parent_id: str | None = None  # Existing - single parent for mutation
       parent_ids: list[int] | None = None  # NEW - multi-parent for merge
   ```

2. **ParetoState Extension**:
   ```python
   @dataclass
   class ParetoState:
       parent_indices: dict[int, list[int | None]] = field(default_factory=dict)
       # Maps candidate_idx → [parent_idx, ...] or [None] for seeds
   ```

## 3. Common Ancestor Algorithm

### Decision: BFS-based ancestor traversal

**Rationale**: Breadth-first search efficiently finds all ancestors without recursion depth issues for deep genealogies.

**Algorithm**:
```python
def get_ancestors(candidate_idx: int, parent_indices: dict) -> set[int]:
    """Return all ancestor indices for a candidate."""
    ancestors = set()
    queue = deque([candidate_idx])
    while queue:
        current = queue.popleft()
        for parent in parent_indices.get(current, []):
            if parent is not None and parent not in ancestors:
                ancestors.add(parent)
                queue.append(parent)
    return ancestors

def find_common_ancestor(idx1: int, idx2: int, parent_indices: dict) -> int | None:
    """Find most recent common ancestor of two candidates."""
    ancestors1 = get_ancestors(idx1, parent_indices)
    ancestors2 = get_ancestors(idx2, parent_indices)
    common = ancestors1 & ancestors2
    if not common:
        return None
    # Return most recent (highest index) common ancestor
    return max(common)
```

## 4. ProposerProtocol Design

### Decision: Create ProposerProtocol in ports/ layer

**Rationale**: Following hexagonal architecture, the proposer interface should be a protocol in ports/ that engine/ depends on, with implementations in engine/ or adapters/.

**Protocol Definition**:
```python
@runtime_checkable
class ProposerProtocol(Protocol):
    """Protocol for candidate proposal strategies."""

    async def propose(
        self,
        state: ParetoState,
        eval_batch: EvaluationBatch | None = None,
    ) -> ProposalResult | None:
        """Propose a new candidate or return None if no proposal possible."""
        ...
```

**ProposalResult**:
```python
@dataclass(frozen=True)
class ProposalResult:
    """Result of a successful proposal operation."""
    candidate: Candidate
    parent_indices: list[int]
    tag: str  # "mutation" or "merge"
    metadata: dict[str, Any] = field(default_factory=dict)
```

## 5. Merge Candidate Selection

### Decision: Use find_dominator_programs from upstream GEPA

**Rationale**: The dominator selection ensures only Pareto-optimal candidates are considered for merging, preventing merges between low-quality candidates.

**Selection Criteria**:
1. Both candidates must be on Pareto frontier (dominator programs)
2. Candidates must have common ancestor (not from separate seed lineages)
3. Candidates must have different component values to make merge worthwhile
4. Previous merge attempts with same triplet (id1, id2, ancestor) are skipped

## 6. Engine Integration

### Decision: Add MergeProposer as optional proposer in AsyncGEPAEngine

**Rationale**: Merge should be an optional optimization strategy that can be enabled/disabled via configuration.

**Integration Points**:
1. `EvolutionConfig`: Add `use_merge: bool = False` and `max_merge_invocations: int = 10`
2. `AsyncGEPAEngine.__init__`: Accept optional `merge_proposer: ProposerProtocol`
3. `AsyncGEPAEngine.run()`: After successful mutation, attempt merge if scheduled

**Scheduling Logic** (from upstream):
- After mutation finds new program → schedule merge
- Merge attempts are rate-limited by `max_merge_invocations`
- Merge only attempted when `merges_due > 0`

## 7. Component Comparison for Merging

### Decision: Use string equality for component comparison

**Rationale**: Components are stored as `dict[str, str]` where values are instruction text. Simple string equality determines if a component changed from ancestor to descendant.

**Merge Logic per Component**:
```python
def merge_components(
    ancestor: dict[str, str],
    parent1: dict[str, str],
    parent2: dict[str, str],
    scores1: float,
    scores2: float,
) -> dict[str, str]:
    """Merge components from two parents based on changes from ancestor."""
    merged = {}
    for key in ancestor.keys():
        anc_val = ancestor[key]
        p1_val = parent1[key]
        p2_val = parent2[key]

        if p1_val == p2_val:
            # Both same - take either
            merged[key] = p1_val
        elif p1_val == anc_val and p2_val != anc_val:
            # P1 unchanged, P2 changed - take P2's innovation
            merged[key] = p2_val
        elif p2_val == anc_val and p1_val != anc_val:
            # P2 unchanged, P1 changed - take P1's innovation
            merged[key] = p1_val
        else:
            # Both changed differently - take higher scorer's value
            merged[key] = p1_val if scores1 >= scores2 else p2_val

    return merged
```

## 8. Error Handling

### Decision: Return None on merge failure rather than raising exceptions

**Rationale**: Merge is an optional optimization. Failures should not halt evolution - the engine falls back to mutation-only.

**Failure Cases**:
- No common ancestor found → return None
- No suitable merge candidates on frontier → return None
- All component values identical → return None
- Merge previously attempted → return None

Logging via structlog for all failure cases for debugging.
