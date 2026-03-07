# Story 3.2: Fill Contract Test Gaps

Status: done

## Story

As a contributor,
I want every public Protocol contract test to cover all 4 minimum test types,
so that the protocol coverage CI check passes and new implementations are validated with consistent coverage.

## Acceptance Criteria

1. `scripts/check_protocol_coverage.py` passes with zero missing Protocols (already true -- verify it stays green)
2. Every protocol contract test file has at minimum 4 test types: isinstance check, method signature verification (async where applicable), happy-path behavioral, and non-compliance (missing methods -> `not isinstance`)
3. `test_candidate_selector_protocol.py` is upgraded from 4 bare functions to three-class template with non-compliance tests
4. `test_component_selector_protocol.py` is upgraded from 4 bare functions to three-class template (already has non-compliance test -- preserve it)
5. `test_multi_agent_adapter_protocol.py` is upgraded from 3 minimal methods to three-class template with non-compliance tests
6. Non-compliance tests added to: `test_proposer_protocol.py`, `test_merge_proposer_protocol.py`, `test_video_blob_service_protocol.py`
7. All contract tests pass: `uv run pytest tests/contracts/ -x` completes green
8. No regressions in existing test count (currently 430 contract tests -- count must not decrease)
9. Three-class template (`RuntimeCheckable`, `Behavior`, `NonCompliance`) is the standard for new protocol test files going forward (established by the 3 upgraded files as exemplars alongside `test_stopper_protocol.py`)

## Tasks / Subtasks

- [x] Task 1: Audit and baseline (AC: 1, 8)
  - [x] 1.1 Run `python scripts/check_protocol_coverage.py` -- confirm 12/12 covered
  - [x] 1.2 Run `uv run pytest tests/contracts/ --co -q` -- record baseline test count (430)

- [x] Task 2: Upgrade `test_candidate_selector_protocol.py` (AC: 2, 3)
  - [x] 2.1 Read existing file -- currently 4 bare functions, no test classes, no non-compliance
  - [x] 2.2 Refactor into three-class template:
    - `TestCandidateSelectorProtocolRuntimeCheckable` -- isinstance checks for all implementations
    - `TestCandidateSelectorProtocolBehavior` -- return type, empty state edge case
    - `TestCandidateSelectorProtocolNonCompliance` -- missing `select_candidate` method -> `not isinstance`
  - [x] 2.3 Preserve all existing test coverage while adding non-compliance tests

- [x] Task 3: Upgrade `test_component_selector_protocol.py` (AC: 2, 4)
  - [x] 3.1 Read existing file -- currently 4 bare functions (1 is already non-compliance), no test classes
  - [x] 3.2 Refactor into three-class template:
    - `TestComponentSelectorProtocolRuntimeCheckable` -- isinstance checks
    - `TestComponentSelectorProtocolBehavior` -- return type contracts, method signature
    - `TestComponentSelectorProtocolNonCompliance` -- move existing non-compliance test here
  - [x] 3.3 Preserve all existing test coverage (including existing non-compliance assertion at line 45)

- [x] Task 4: Upgrade `test_multi_agent_adapter_protocol.py` (AC: 2, 5)
  - [x] 4.1 Read existing file -- currently 3 methods in 1 class, no non-compliance
  - [x] 4.2 Expand to three-class template:
    - `TestMultiAgentAdapterProtocolRuntimeCheckable` -- isinstance with `AsyncGEPAAdapter`
    - `TestMultiAgentAdapterProtocolBehavior` -- async method verification, return type contracts
    - `TestMultiAgentAdapterProtocolNonCompliance` -- missing methods -> `not isinstance`
  - [x] 4.3 Add behavioral tests: verify async method signatures for `evaluate()`, `make_reflective_dataset()`, `propose_new_texts()`

- [x] Task 5: Add non-compliance tests to 3 files missing them (AC: 2, 6)
  - [x] 5.1 `test_proposer_protocol.py` -- add non-compliance test (class missing `propose()` -> `not isinstance`)
  - [x] 5.2 `test_merge_proposer_protocol.py` -- add non-compliance test (class missing `propose()` -> `not isinstance`)
  - [x] 5.3 `test_video_blob_service_protocol.py` -- add non-compliance test (class missing `prepare_video_parts()` -> `not isinstance`)
  - [x] 5.4 Do NOT restructure these files into three classes -- they already have solid behavioral coverage; only add non-compliance tests

- [x] Task 6: Final verification (AC: 1, 7, 8)
  - [x] 6.1 Run `python scripts/check_protocol_coverage.py` -- still 12/12
  - [x] 6.2 Run `uv run pytest tests/contracts/ -x` -- all green
  - [x] 6.3 Run `uv run pytest tests/contracts/ --co -q` -- count >= 430
  - [x] 6.4 Run full suite `uv run pytest` -- no regressions

## Dev Notes

### Current State (2026-03-07)

The epics.md AC originally stated `ProposerProtocol` and `VideoBlobServiceProtocol` lacked contract tests. Both now have comprehensive tests (10 and 14 tests respectively) added during prior work. The CI coverage check (`scripts/check_protocol_coverage.py`) passes 12/12.

The real gaps are two-fold:
1. **Structural**: 3 files use bare functions or minimal classes instead of the three-class template
2. **Coverage**: 3 files (beyond those being upgraded) lack non-compliance tests entirely

### Exemplar: test_stopper_protocol.py

The stopper protocol test is the gold standard -- follow its pattern:
```
TestStopperProtocolRuntimeCheckable  (6 tests) -- isinstance checks, multiple implementations
TestStopperProtocolBehavior          (4 tests) -- return types, state transitions
TestStopperProtocolEdgeCases         (7 tests) -- boundary conditions
TestStopperProtocolNonCompliance     (2 tests) -- missing methods, wrong signatures
```
[Source: tests/contracts/test_stopper_protocol.py]

### Three-Class Template (from testing.md)

1. `TestXxxProtocolRuntimeCheckable` -- positive compliance (`isinstance` checks)
2. `TestXxxProtocolBehavior` -- behavioral expectations (return types, state transitions)
3. `TestXxxProtocolNonCompliance` -- negative cases (missing methods -> `not isinstance`)

### Weakest Files Requiring Upgrade

| File | Tests | Classes | Issue |
|------|-------|---------|-------|
| `test_candidate_selector_protocol.py` | 4 | 0 (bare functions) | No classes, no non-compliance |
| `test_component_selector_protocol.py` | 4 | 0 (bare functions) | No classes, no non-compliance |
| `test_multi_agent_adapter_protocol.py` | 4 | 1 | Only 3 basic method-existence checks |

### Files Missing Non-Compliance Tests (verified)

Only 3 files with good behavioral coverage lack non-compliance tests:

| File | Tests | Has NonCompliance | Action |
|------|-------|-------------------|--------|
| `test_proposer_protocol.py` | 10 | **No** | Add non-compliance test |
| `test_merge_proposer_protocol.py` | 6 | **No** | Add non-compliance test |
| `test_video_blob_service_protocol.py` | 14 | **No** | Add non-compliance test |

### Files Already With Non-Compliance (no work needed)

| File | Tests | Non-compliance line(s) |
|------|-------|----------------------|
| `test_scorer_protocol.py` | 12 | line 213 |
| `test_adapter_protocol.py` | 9 | line 99 |
| `test_agent_provider_protocol.py` | 13 | lines 217, 230, 243 |
| `test_evolution_result_protocol.py` | 7 | line 192 |
| `test_component_selector_protocol.py` | 4 | line 45 |

### Non-Compliance Test Pattern

```python
class TestXxxProtocolNonCompliance:
    """Negative cases: objects missing required methods are not instances."""

    def test_missing_method_not_isinstance(self):
        class Incomplete:
            pass  # Missing required method(s)

        assert not isinstance(Incomplete(), XxxProtocol)

    def test_runtime_checkable_limitation_documented(self):
        """@runtime_checkable only checks method existence, not signatures."""
        class WrongSignature:
            def required_method(self):  # Wrong signature (missing params)
                ...

        # isinstance passes because runtime_checkable doesn't check signatures
        assert isinstance(WrongSignature(), XxxProtocol)
```
[Source: tests/contracts/test_stopper_protocol.py -- NonCompliance pattern]

### Architecture Compliance

- **Layer**: `tests/contracts/` -- contract test tier
- **Marker**: `pytestmark = pytest.mark.contract` at module level (all existing files have this)
- **Convention**: One test file per Protocol (not per implementation)
- **Import**: Always import Protocol from `gepa_adk.ports` (not from internal module)

### Existing Code to Reuse (DO NOT REINVENT)

- `test_stopper_protocol.py` -- exemplar three-class template with all 4 test types
- `test_component_handler_protocol.py` -- exemplar multi-implementation compliance testing
- `test_evaluation_policy_protocol.py` -- exemplar parametrized testing across implementations
- Existing mock implementations in each test file (e.g., `MockProposer`, `FixedScorer`) -- extend, don't replace
- `MockScorer` / `mock_scorer_factory` in root conftest -- reuse for scorer-related testing

### Refactoring Rules

- **PRESERVE all existing tests** -- this is additive, not rewrite
- When moving bare functions into classes, keep the same test names and assertions
- For the 3 upgraded files (Tasks 2-4): use three-class template as these are exemplars
- For the 3 files in Task 5: add non-compliance tests only -- do NOT restructure existing class layout
- Don't change test logic that already passes -- only restructure and add
- `pytestmark = pytest.mark.contract` must remain at module level

### Party Mode Consensus (2026-03-07)

Story scope was refined after team discussion (SM, Architect, Dev, TEA):
- **AC relaxed**: Three-class template is MUST for new/upgraded files, not retroactively forced on existing files with good coverage
- **Task 5 scope verified**: Only 3 files actually lack non-compliance tests (not 6 as originally estimated)
- **Key principle**: Coverage of all 4 test types matters more than class structure conformity
- **Forward standard**: Three-class template is the standard for new protocol test files going forward

### Protocol Reference (all 12 in ports/)

| Protocol | File | Key Methods |
|----------|------|-------------|
| `Scorer` | `ports/scorer.py` | `score()`, `async_score()` |
| `ProposerProtocol` | `ports/proposer.py` | `propose()` |
| `AsyncGEPAAdapter` | `ports/adapter.py` | `evaluate()`, `make_reflective_dataset()`, `propose_new_texts()` |
| `StopperProtocol` | `ports/stopper.py` | `__call__()` |
| `AgentProvider` | `ports/agent_provider.py` | `get_agent()`, `save_instruction()`, `list_agents()` |
| `VideoBlobServiceProtocol` | `ports/video_blob_service.py` | `prepare_video_parts()`, `validate_video_file()` |
| `CandidateSelectorProtocol` | `ports/candidate_selector.py` | `select_candidate()` |
| `ComponentSelectorProtocol` | `ports/component_selector.py` | `select_components()` |
| `EvaluationPolicyProtocol` | `ports/evaluation_policy.py` | `get_eval_batch()`, `get_best_candidate()`, `get_valset_score()` |
| `AgentExecutorProtocol` | `ports/agent_executor.py` | `execute_agent()` |
| `ComponentHandler` | `ports/component_handler.py` | `serialize()`, `apply()`, `restore()` |
| `EvolutionResultProtocol` | `ports/evolution_result.py` | Data attrs + `improvement`, `improved` properties |

### Documentation Impact

No documentation impact (confirmed). Contract tests are internal quality infrastructure -- no user-facing docs change.

### Project Structure Notes

- All modifications in `tests/contracts/test_*_protocol.py` files (existing files)
- No new files needed -- all protocol test files already exist
- No changes to `src/` -- this is purely test-side work
- `scripts/check_protocol_coverage.py` unchanged -- verify it still passes

### References

- [Source: tests/contracts/test_stopper_protocol.py -- exemplar three-class template]
- [Source: .claude/rules/testing.md -- contract test three-class template and conventions]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Pattern 2: New Protocol Definition Recipe, minimum 4 tests]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3, Story 3.2]
- [Source: scripts/check_protocol_coverage.py -- CI enforcement of Protocol-to-test mapping]
- [Source: _bmad-output/implementation-artifacts/3-1-implement-critic-preset-factory.md -- previous story learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

No issues encountered during implementation.

### Completion Notes List

- Task 1: Baseline confirmed -- 12/12 protocol coverage, 430 contract tests
- Task 2: Upgraded `test_candidate_selector_protocol.py` from 4 bare functions to three-class template (RuntimeCheckable, Behavior, NonCompliance). Added `test_select_candidate_returns_int` behavioral test and 2 non-compliance tests. Preserved all existing parametrized test coverage across 3 selector implementations. Test count: 10 -> 15
- Task 3: Upgraded `test_component_selector_protocol.py` from 4 bare functions to three-class template. Added `RoundRobinComponentSelector` and `AllComponentSelector` isinstance checks, behavioral tests for return types. Preserved existing non-compliance test. Test count: 4 -> 9
- Task 4: Upgraded `test_multi_agent_adapter_protocol.py` from 1 class with 4 tests to three-class template. Split existing tests across RuntimeCheckable and Behavior classes, added 4 non-compliance tests (missing all methods, missing evaluate, missing propose, wrong signature). Test count: 4 -> 10
- Task 5: Added `TestProposerProtocolNonCompliance` (2 tests), `TestMergeProposerProtocolNonCompliance` (2 tests), `TestVideoBlobServiceProtocolNonCompliance` (3 tests) to respective files without restructuring existing class layout
- Task 6: Final verification -- 12/12 protocol coverage, 453 contract tests (was 430), all green, full suite 2124 passed / 1 skipped / 67 deselected
- Code Review Fixes: (1) Fixed shared mutable RNG state in candidate_selector fixture with factory lambdas, (2) Removed constructor validation test from contract tier (already covered in unit tier), (3) Added missing make_reflective_dataset non-compliance test to multi_agent_adapter

### AC-to-Test Mapping

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 | Task 6.1: `check_protocol_coverage.py` -> 12/12 | Pass |
| AC2 | All 6 modified files now have isinstance, async/signature, behavioral, and non-compliance tests | Pass |
| AC3 | `test_candidate_selector_protocol.py` -> 3 classes, 15 tests | Pass |
| AC4 | `test_component_selector_protocol.py` -> 3 classes, 9 tests (non-compliance preserved) | Pass |
| AC5 | `test_multi_agent_adapter_protocol.py` -> 3 classes, 10 tests | Pass |
| AC6 | Non-compliance added to proposer (2), merge_proposer (2), video_blob (3) | Pass |
| AC7 | `uv run pytest tests/contracts/ -x` -> 453 passed | Pass |
| AC8 | 453 >= 430 baseline | Pass |
| AC9 | 3 upgraded files + test_stopper_protocol.py serve as exemplars | Pass |

### File List

- `tests/contracts/test_candidate_selector_protocol.py` (modified -- restructured to three-class template)
- `tests/contracts/test_component_selector_protocol.py` (modified -- restructured to three-class template)
- `tests/contracts/test_multi_agent_adapter_protocol.py` (modified -- restructured to three-class template)
- `tests/contracts/test_proposer_protocol.py` (modified -- added NonCompliance class)
- `tests/contracts/test_merge_proposer_protocol.py` (modified -- added NonCompliance class)
- `tests/contracts/test_video_blob_service_protocol.py` (modified -- added NonCompliance class)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified -- status ready-for-dev -> review)
- `_bmad-output/implementation-artifacts/3-2-fill-contract-test-gaps.md` (modified -- task checkboxes, dev agent record)

## Change Log

- 2026-03-07: Implemented Story 3.2 -- upgraded 3 protocol test files to three-class template, added non-compliance tests to 3 additional files. Contract test count increased from 430 to 453 with zero regressions.
- 2026-03-07: Code review fixes -- fixed shared mutable RNG state (M1), moved constructor test to unit tier (M2), added missing non-compliance test (L2). Test count unchanged at 453.
