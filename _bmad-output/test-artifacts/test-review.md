---
stepsCompleted: ['step-01-load-context', 'step-02-discover-tests', 'step-03-quality-criteria', 'step-04-score-calculation', 'step-05-report-generation']
lastStep: 'step-05-report-generation'
lastSaved: '2026-03-07'
workflowType: 'testarch-test-review'
inputDocuments:
  - '_bmad/tea/testarch/knowledge/test-quality.md'
  - '_bmad/tea/testarch/knowledge/data-factories.md'
  - '_bmad/tea/testarch/knowledge/test-levels-framework.md'
  - '_bmad/tea/testarch/knowledge/test-healing-patterns.md'
  - '_bmad/tea/testarch/knowledge/selective-testing.md'
  - 'pyproject.toml'
  - 'tests/conftest.py'
  - 'tests/fixtures/adapters.py'
---

# Test Quality Review: Full Suite

**Quality Score**: 80/100 (A - Good)
**Review Date**: 2026-03-07
**Review Scope**: suite (all tests)
**Reviewer**: TEA Agent

---

Note: This review audits existing tests; it does not generate tests.
Coverage mapping and coverage gates are out of scope here. Use `trace` for coverage decisions.

## Executive Summary

**Overall Assessment**: Good

**Recommendation**: Approve with Comments

### Key Strengths

- 2101 tests pass in ~7s - fast, fully deterministic suite
- 100% bare `assert` usage across all tiers - zero unittest-style assertions
- Excellent fixture architecture with centralized MockScorer, MockAdapter, MockExecutor factories
- Module-level `pytestmark` compliance is strong across unit and integration tiers
- All random usage is seeded (`random.Random(42)`) - zero non-deterministic data
- Clean async test patterns leveraging `asyncio_mode = "auto"` correctly
- New `test_critic_preset_factory.py` is exemplary: 87 lines, 4 focused test classes, module-level pytestmark

### Key Weaknesses

- 19 test files exceed 300 lines (test_models.py at 2528 lines is extreme) - corrected from 11 in prior review
- Contract tests only ~3% follow the three-class template (RuntimeCheckable/Behavior/NonCompliance)
- 10 integration files use raw `unittest.mock.patch` instead of pytest-mock's `mocker` fixture (up from 6)
- ~12 individual integration tests exceed 50 lines
- 6 contract files missing module-level `pytestmark` (up from 4)

### Summary

The gepa-adk test suite maintains production-grade quality with excellent fundamentals: fast execution, deterministic data, proper isolation, and consistent pytest conventions. The unit tier is exemplary. Since the last review (2026-03-06), 12 new tests were added with the well-structured `test_critic_preset_factory.py`. However, minor regressions appeared: 4 new integration files introduced `unittest.mock` imports, and 2 new contract files lack module-level `pytestmark`. The file-size count was corrected from 11 to 19 files exceeding 300 lines. The contract three-class template adoption remains the largest structural gap.

---

## Quality Criteria Assessment

| Criterion                            | Status  | Violations | Notes                                                    |
| ------------------------------------ | ------- | ---------- | -------------------------------------------------------- |
| Determinism (no conditionals)        | PASS    | 0          | All random seeded, no flow-control conditionals          |
| Isolation (cleanup, no shared state) | PASS    | 0          | Function-scoped fixtures, no shared mutable state        |
| Fixture Patterns                     | PASS    | 0          | Centralized factories, proper scoping                    |
| Data Factories                       | PASS    | 0          | MockScorer, MockAdapter, create_mock_adapter() factories |
| Explicit Assertions                  | PASS    | 0          | 100% bare assert, pytest.raises, pytest.approx           |
| Hard Waits (sleep, waitForTimeout)   | PASS    | 0          | No time.sleep() anywhere in test code                    |
| Test Length (<=300 lines)            | WARN    | 19         | 19 files exceed 300 lines (corrected from 11)            |
| Flakiness Patterns                   | PASS    | 0          | No timing-dependent or env-dependent assertions          |
| Test Tier Markers                    | WARN    | 6          | 6 contract files missing module-level pytestmark          |
| Contract Three-Class Template        | FAIL    | ~33        | Only ~1 of 36 protocol contract files follows template   |
| Mocker vs unittest.mock              | WARN    | 10         | 10 integration files use raw unittest.mock (up from 6)   |
| Individual Test Length (<=50 lines)  | WARN    | ~12        | ~12 integration tests exceed 50 lines                    |

**Total Violations**: 0 Critical, 1 High, 4 Medium, 10 Low

---

## Quality Score Breakdown

```
Starting Score:          100
Critical Violations:     -0 x 10 = -0
High Violations:         -1 x 5 = -5     (contract template non-compliance pattern)
Medium Violations:       -4 x 2 = -8     (file size, marker gaps, long tests, mock style)
Low Violations:          -10 x 1 = -10   (individual unittest.mock.patch files, up from 6)

Bonus Points:
  Comprehensive Fixtures: +5              (MockScorer, MockAdapter, create_mock_adapter)
  Perfect Isolation:      +5              (function scope, no shared state)
  Deterministic Data:     -2 (custom)     (file size count correction from prior review)
                          --------
Total Bonus:             +8

Final Score:             80/100 (slight decline from 82 due to mock/marker regression)
Grade:                   A (Good)
```

---

## Critical Issues (Must Fix)

No critical issues detected.

---

## Recommendations (Should Fix)

### 1. Contract Tests: Adopt Three-Class Template

**Severity**: P1 (High)
**Location**: `tests/contracts/` (33+ files)
**Criterion**: Contract Three-Class Template
**Knowledge Base**: [test-quality.md](../../_bmad/tea/testarch/knowledge/test-quality.md)

**Issue Description**:
Per the project's testing conventions (`.claude/rules/testing.md`), every Protocol contract file should follow a three-class template:
1. `TestXxxProtocolRuntimeCheckable` - positive compliance (`isinstance` checks)
2. `TestXxxProtocolBehavior` - behavioral expectations (return types, state transitions)
3. `TestXxxProtocolNonCompliance` - negative cases (missing methods -> `not isinstance`)

Only `test_stopper_protocol.py` fully follows this template with both `RuntimeCheckable` and `NonCompliance` classes. The remaining ~35 files use single-class or module-function approaches.

**Compliant Example** (`test_stopper_protocol.py`):

```python
# GOOD: Three-class template
class TestStopperProtocolRuntimeCheckable:
    def test_satisfies_stopper_protocol(self) -> None:
        stopper = SignalStopper()
        assert isinstance(stopper, StopperProtocol)

class TestStopperProtocolBehavior:
    def test_call_returns_bool(self) -> None:
        stopper = SignalStopper()
        result = stopper(default_state)
        assert isinstance(result, bool)

class TestStopperProtocolNonCompliance:
    def test_missing_call_method(self) -> None:
        class BadStopper:
            pass
        assert not isinstance(BadStopper(), StopperProtocol)
```

**Non-compliant Example** (`test_scorer_protocol.py`):

```python
# BAD: Single class bundles all concerns
class TestScorerProtocol:
    # RuntimeCheckable, behavior, AND non-compliance all mixed together
    def test_isinstance_check(self): ...
    def test_score_returns_tuple(self): ...
    def test_missing_method_fails(self): ...
```

**Priority**: Address during next contract test touch. Not blocking - existing tests still validate protocols.

---

### 2. Split Large Test Files

**Severity**: P2 (Medium)
**Location**: Multiple files
**Criterion**: Test Length
**Knowledge Base**: [test-quality.md](../../_bmad/tea/testarch/knowledge/test-quality.md)

**Files exceeding 300 lines** (corrected count - 19 files):

| File | Lines | Recommendation |
| ---- | ----- | -------------- |
| `tests/unit/domain/test_models.py` | 2528 | Split by model class (Candidate, EvolutionConfig, etc.) |
| `tests/unit/adapters/test_adk_adapter.py` | 1579 | Split by adapter method (evaluate, propose, reflect) |
| `tests/unit/utils/test_events.py` | 1371 | Split by event type |
| `tests/contracts/test_adk_adapter_contracts.py` | 1164 | Split contract vs behavior tests |
| `tests/unit/test_api.py` | 846 | Split by API function |
| `tests/unit/test_api_state_guard.py` | 844 | Split by guard type |
| `tests/unit/test_workflow.py` | 819 | Split by workflow type |
| `tests/unit/adapters/test_multi_agent_adapter.py` | 765 | Split by adapter concern |
| `tests/unit/test_encoding.py` | 695 | Split by encoding scenario |
| `tests/unit/adapters/test_agent_executor.py` | 678 | Split by executor method |
| `tests/unit/adapters/test_component_handlers.py` | 672 | Split by handler type |
| `tests/unit/test_api_app_runner.py` | 635 | Split by runner concern |
| `tests/unit/test_pre_flight_validation.py` | 626 | Split by validation type |
| `tests/integration/test_component_handler_integration.py` | 579 | Split by handler scenario |
| `tests/unit/engine/test_proposer.py` | 550 | Split by proposer behavior |
| `tests/unit/engine/test_async_engine.py` | 546 | Split by engine concern |
| `tests/integration/adapters/test_adk_adapter_integration.py` | 513 | Split by adapter path |
| `tests/unit/domain/test_exceptions.py` | 492 | Split by exception category |
| `tests/contracts/test_reflection_example_metadata.py` | 491 | Split by metadata concern |

**Priority**: P2 - address incrementally when touching these files. The 300-line guideline is a readability heuristic, not a hard gate.

---

### 3. Migrate unittest.mock.patch to mocker Fixture

**Severity**: P2 (Medium)
**Location**: 10 integration test files (up from 6)
**Criterion**: Mocking style consistency
**Knowledge Base**: [test-quality.md](../../_bmad/tea/testarch/knowledge/test-quality.md)

**Affected files** (6 from prior review + 4 new):
- `tests/integration/test_api_state_guard_logging.py`
- `tests/integration/test_encoding_integration.py`
- `tests/integration/test_unified_execution.py`
- `tests/integration/test_executor_wiring_integration.py`
- `tests/integration/test_critic_reflection_metadata.py`
- `tests/integration/test_stopper_integration.py`
- `tests/integration/engine/test_reasoning_capture.py` *(new)*
- `tests/integration/test_multimodal_evolution.py` *(new)*
- `tests/integration/test_trajectory_capture.py` *(new)*
- `tests/integration/adapters/test_adk_adapter_integration.py` *(new)*

**Current Code**:

```python
# BAD: Raw unittest.mock.patch
from unittest.mock import patch, MagicMock

def test_something():
    with patch("gepa_adk.module.func") as mock_func:
        mock_func.return_value = "value"
        ...
```

**Recommended Fix**:

```python
# GOOD: pytest-mock's mocker fixture
def test_something(mocker):
    mock_func = mocker.patch("gepa_adk.module.func", return_value="value")
    ...
```

**Benefits**: Automatic cleanup, consistent with unit test patterns, better pytest integration.

**Priority**: P2 - address when touching these files. Trend is worsening (+4 files since last review).

---

### 4. Contract Files Missing Module-Level pytestmark

**Severity**: P3 (Low)
**Location**: 6 contract files (up from 4)
**Criterion**: Test Tier Markers

**Affected files**:
- `tests/contracts/test_agent_executor_protocol.py` (uses class-level marks)
- `tests/contracts/test_component_handler_protocol.py` (mixed module + class marks)
- `tests/contracts/test_multi_agent_executor_contract.py` (missing entirely)
- `tests/contracts/test_workflow_contracts.py` (missing entirely)
- `tests/contracts/test_schema_constraints_contract.py` *(new - missing entirely)*
- `tests/contracts/test_schema_utils_contract.py` *(new - missing entirely)*

**Fix**: Add `pytestmark = pytest.mark.contract` at module level in each file.

**Priority**: P3 - quick fix, low risk.

---

### 5. Refactor Long Individual Integration Tests

**Severity**: P3 (Low)
**Location**: ~12 integration tests
**Criterion**: Individual Test Length

**Longest offenders**:
- `test_unified_execution.py::test_critic_accesses_generator_session_state` (96 lines)
- `test_frontier_evolution.py::test_objective_frontiers_produce_more_unique_candidates` (89 lines)
- `test_frontier_evolution.py::test_subset_evaluation_reduces_cost` (79 lines)
- `test_adk_adapter_integration.py::test_parallel_batch_evaluation_with_real_adk` (72 lines)
- `test_async_engine_failure.py::test_multi_component_evolution_tracks_all_components` (71 lines)

**Fix**: Extract setup into fixtures, split multi-assertion tests, or use parametrize.

**Priority**: P3 - address when touching these files.

---

## Best Practices Found

### 1. Centralized Mock Factory Architecture

**Location**: `tests/conftest.py`, `tests/fixtures/adapters.py`
**Pattern**: Factory fixtures with configurable behavior

**Why This Is Good**:
The `create_mock_adapter()` factory with `AdapterConfig` dataclass eliminates mock duplication across 80+ test files. Every test configures behavior declaratively (scores, output modes, tracking) without reimplementing mock logic.

**Code Example**:

```python
# Excellent: Configurable factory replaces ~9 duplicate MockScorer implementations
adapter = create_mock_adapter(
    scores=[0.5, 0.6, 0.7],
    objective_scores={"accuracy": 0.9},
    output_mode=OutputMode.CANDIDATE_TEXT,
    track_calls=True,
)
```

**Use as Reference**: This pattern should be extended for any new mock types.

---

### 2. Lazy API Probe in conftest.py

**Location**: `tests/conftest.py:103-134`
**Pattern**: Lazy evaluation of expensive checks

**Why This Is Good**:
The `pytest_collection_modifyitems` hook only probes Ollama/Gemini availability when the collected test set actually contains items with matching markers. Default runs (`-m 'not api'`) never trigger a network call. This keeps the suite fast.

```python
# Probes only fire when needed
ollama_items = [i for i in items if i.get_closest_marker("requires_ollama")]
if ollama_items and _ollama_result is None:
    _ollama_result = _is_ollama_available()
```

---

### 3. Protocol Method Signature Drift Detection

**Location**: `tests/contracts/test_protocol_method_signatures.py`
**Pattern**: Inspect-based contract guard

**Why This Is Good**:
Uses `inspect` module to verify that mock implementations match Protocol method signatures exactly. This catches signature drift between Protocol definitions and their mock/real implementations that `isinstance` alone cannot detect (due to `runtime_checkable` limitations).

**Use as Reference**: Every new Protocol should have a corresponding entry in this file.

---

### 4. Deterministic Seeded Randomness

**Location**: `tests/unit/engine/test_determinism.py`, `test_candidate_selectors.py`, `test_async_engine_merge.py`
**Pattern**: `random.Random(seed)` instead of module-level `random`

**Why This Is Good**:
All randomness in tests uses instance-level `random.Random(42)` (or similar explicit seed), never the global `random` module. This guarantees reproducibility across runs and environments.

---

### 5. New: Exemplary Test File Structure (test_critic_preset_factory.py)

**Location**: `tests/unit/adapters/scoring/test_critic_preset_factory.py`
**Pattern**: Small, focused test file with class-per-concern

**Why This Is Good**:
At 87 lines, this new file is a model for test organization:
- Module-level `pytestmark = pytest.mark.unit`
- 4 focused test classes: `TestCreateCriticPresets`, `TestCreateCriticErrorHandling`, `TestCreateCriticModelOverride`, `TestCriticPresetsDict`
- Clear docstrings on every test method
- Tests one public API (`create_critic()`) with presets, errors, overrides, and re-exports

**Use as Reference**: New test files should follow this structure.

---

## Test File Analysis

### Suite Metadata

- **Total Test Files**: 146 (test_*.py) - up from 145
- **Total Lines of Test Code**: 44,876 - up from 44,764
- **Test Framework**: pytest 8.4.2+ with pytest-asyncio, pytest-mock, pytest-xdist
- **Language**: Python 3.12

### Test Structure

- **Unit Tests**: ~74 files, ~28,000 lines
- **Contract Tests**: ~36 files, ~8,100 lines
- **Integration Tests**: ~36 files, ~12,000 lines
- **Average Test Length**: ~15 lines per test method
- **Fixtures**: Centralized in `tests/conftest.py` and `tests/fixtures/adapters.py`

### Test Scope

- **Collected Tests**: 2,169 total (2,102 non-API)
- **Passed**: 2,101
- **Skipped**: 1 (placeholder: `test_async_engine_integration.py`)
- **Deselected**: 67 (API-tier tests requiring Ollama/Gemini)
- **Execution Time**: ~7s

### Priority Distribution

- P0 (Critical): N/A (no explicit priority markers - Python backend)
- Tier markers: `unit`, `contract`, `integration`, `api`, `slow`

### Assertions Analysis

- **Assertion Style**: 100% bare `assert` (pytest native)
- **Exception Testing**: `pytest.raises` used consistently
- **Float Comparison**: `pytest.approx` used where needed
- **Protocol Compliance**: `isinstance(obj, Protocol)` pattern throughout

---

## Context and Integration

### Related Artifacts

- **Testing Conventions**: `.claude/rules/testing.md` (comprehensive tier/fixture/naming rules)
- **Python Conventions**: `.claude/rules/python.md` (structlog, dataclass, async patterns)
- **Project Config**: `pyproject.toml` (markers, filterwarnings, asyncio settings)

---

## Knowledge Base References

This review consulted the following knowledge base fragments:

- **[test-quality.md](../../_bmad/tea/testarch/knowledge/test-quality.md)** - Definition of Done for tests (no hard waits, <300 lines, <1.5 min, self-cleaning)
- **[data-factories.md](../../_bmad/tea/testarch/knowledge/data-factories.md)** - Factory functions with overrides, API-first setup
- **[test-levels-framework.md](../../_bmad/tea/testarch/knowledge/test-levels-framework.md)** - Unit vs Integration vs E2E appropriateness
- **[test-healing-patterns.md](../../_bmad/tea/testarch/knowledge/test-healing-patterns.md)** - Common failure patterns and fixes
- **[selective-testing.md](../../_bmad/tea/testarch/knowledge/selective-testing.md)** - Tag-based execution, diff-based runs

For coverage mapping, consult `trace` workflow outputs.

See [tea-index.csv](../../_bmad/tea/testarch/tea-index.csv) for complete knowledge base.

---

## Next Steps

### Immediate Actions (Before Merge)

None required - suite is healthy.

### Follow-up Actions (Future PRs)

1. **Standardize contract three-class template** - Refactor ~35 contract files to use RuntimeCheckable/Behavior/NonCompliance class structure
   - Priority: P1
   - Target: Next sprint touching contract tests

2. **Split large test files** - Break up 19 files exceeding 300 lines (corrected from 11)
   - Priority: P2
   - Target: Incremental, when files are touched

3. **Migrate unittest.mock to mocker** - Update 10 integration files (growing trend)
   - Priority: P2
   - Target: Next sprint touching those files

4. **Add missing pytestmark** - Fix 6 contract files (up from 4)
   - Priority: P3
   - Target: Quick PR

### Re-Review Needed?

No re-review needed - approve as-is. The findings are incremental improvements, not blocking issues. Monitor the unittest.mock trend.

---

## Decision

**Recommendation**: Approve with Comments

**Rationale**:
Test quality remains good at 80/100 (slight decline from 82). The suite is fast (~7s for 2101 tests), fully deterministic, well-isolated, and uses pytest conventions consistently. New test additions (`test_critic_preset_factory.py`) are exemplary. The primary gaps remain structural: contract tests should adopt the three-class template, large files should be split, and the unittest.mock usage trend should be monitored. The file-size violation count was corrected from 11 to 19. None of these issues impact test reliability or correctness.

> Test quality is good with 80/100 score. Minor structural regressions noted (unittest.mock trend +4 files, pytestmark gaps +2 files). File-size count corrected to 19. New test files are well-structured. Production-ready and reliable.

---

## Appendix

### Violation Summary by Location

| Location | Severity | Criterion | Issue | Fix |
| -------- | -------- | --------- | ----- | --- |
| tests/contracts/ (35 files) | P1 | Contract Template | Single-class instead of three-class | Refactor to RuntimeCheckable/Behavior/NonCompliance |
| tests/unit/domain/test_models.py | P2 | File Length | 2528 lines | Split by model class |
| tests/unit/adapters/test_adk_adapter.py | P2 | File Length | 1579 lines | Split by adapter method |
| tests/unit/utils/test_events.py | P2 | File Length | 1371 lines | Split by event type |
| tests/contracts/test_adk_adapter_contracts.py | P2 | File Length | 1164 lines | Split contract vs behavior |
| tests/unit/test_api.py | P2 | File Length | 846 lines | Split by API function |
| tests/unit/test_api_state_guard.py | P2 | File Length | 844 lines | Split by guard type |
| tests/unit/test_workflow.py | P2 | File Length | 819 lines | Split by workflow type |
| tests/unit/adapters/test_multi_agent_adapter.py | P2 | File Length | 765 lines | Split by adapter concern |
| tests/unit/test_encoding.py | P2 | File Length | 695 lines | Split by encoding scenario |
| tests/unit/adapters/test_agent_executor.py | P2 | File Length | 678 lines | Split by executor method |
| tests/unit/adapters/test_component_handlers.py | P2 | File Length | 672 lines | Split by handler type |
| tests/unit/test_api_app_runner.py | P2 | File Length | 635 lines | Split by runner concern |
| tests/unit/test_pre_flight_validation.py | P2 | File Length | 626 lines | Split by validation type |
| tests/integration/test_component_handler_integration.py | P2 | File Length | 579 lines | Split by handler scenario |
| tests/unit/engine/test_proposer.py | P2 | File Length | 550 lines | Split by proposer behavior |
| tests/unit/engine/test_async_engine.py | P2 | File Length | 546 lines | Split by engine concern |
| tests/integration/adapters/test_adk_adapter_integration.py | P2 | File Length | 513 lines | Split by adapter path |
| tests/unit/domain/test_exceptions.py | P2 | File Length | 492 lines | Split by exception category |
| tests/contracts/test_reflection_example_metadata.py | P2 | File Length | 491 lines | Split by metadata concern |
| tests/integration/test_api_state_guard_logging.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_encoding_integration.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_unified_execution.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_executor_wiring_integration.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_critic_reflection_metadata.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_stopper_integration.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/engine/test_reasoning_capture.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_multimodal_evolution.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/test_trajectory_capture.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/integration/adapters/test_adk_adapter_integration.py | P3 | Mock Style | unittest.mock.patch | Use mocker fixture |
| tests/contracts/test_workflow_contracts.py | P3 | Tier Marker | Missing pytestmark | Add module-level mark |
| tests/contracts/test_multi_agent_executor_contract.py | P3 | Tier Marker | Missing pytestmark | Add module-level mark |
| tests/contracts/test_agent_executor_protocol.py | P3 | Tier Marker | Class-level marks only | Move to module level |
| tests/contracts/test_component_handler_protocol.py | P3 | Tier Marker | Mixed marking | Standardize to module level |
| tests/contracts/test_schema_constraints_contract.py | P3 | Tier Marker | Missing pytestmark | Add module-level mark |
| tests/contracts/test_schema_utils_contract.py | P3 | Tier Marker | Missing pytestmark | Add module-level mark |

### Quality Trends

| Review Date | Score | Grade | Critical Issues | Trend |
| ----------- | ----- | ----- | --------------- | ----- |
| 2026-03-06  | 82/100 | A    | 0               | Baseline |
| 2026-03-07  | 80/100 | A    | 0               | Slight decline (-2) |

### Delta Summary (2026-03-06 to 2026-03-07)

| Metric | Previous | Current | Change |
| ------ | -------- | ------- | ------ |
| Test files | 145 | 146 | +1 |
| Tests passed | 2,089 | 2,101 | +12 |
| Total lines | 44,764 | 44,876 | +112 |
| Execution time | 2.75s | ~7s | +4.25s |
| Files > 300 lines | 11 (reported) | 19 (corrected) | +8 (correction) |
| pytestmark missing | 4 | 6 | +2 |
| unittest.mock files | 6 | 10 | +4 |

---

## Review Metadata

**Generated By**: BMad TEA Agent (Test Architect)
**Workflow**: testarch-test-review v5.0
**Review ID**: test-review-suite-20260307
**Timestamp**: 2026-03-07
**Version**: 2.0 (update/merge from v1.0)
