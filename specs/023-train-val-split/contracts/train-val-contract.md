# Contract: Trainset and Valset Separation

**Feature**: 023-train-val-split
**Date**: 2026-01-14
**Type**: Behavioral Contract

## Overview

Defines the required behavior for separating trainset (reflection) and valset (scoring) during evolution. This contract ensures acceptance decisions and candidate selection are based on valset scores, while reflection uses trainset traces.

---

## Contract Rules

### Preconditions
| Condition | Description |
|-----------|-------------|
| `trainset` provided | Trainset must be supplied and non-empty |
| `valset` optional | When omitted, valset defaults to trainset |
| Schema compatibility | Trainset and valset share the same example schema |

### Behavioral Requirements
| Requirement | Description |
|-------------|-------------|
| Reflection dataset source | Reflection data uses trainset only (trace capture enabled) |
| Scoring dataset source | Baseline/proposal scoring uses valset only (trace capture disabled) |
| Acceptance decisions | Accept/reject is based on valset scores only |
| Candidate selection | Pareto and selector scores derive from valset only |
| Defaulting behavior | If `valset` is None, use `trainset` for scoring |
| Reporting | Results expose valset-based scores separately from reflection metrics |

### Postconditions
| Condition | Description |
|-----------|-------------|
| No dataset mixing | Reflection traces are not generated from valset |
| Scoring integrity | Valset scores do not include trainset-only data |
| Backward compatibility | Results match prior behavior when valset is omitted |

---

## Acceptance Scenarios

1. **Given** trainset=10 examples and valset=50 examples, **When** evolution runs, **Then** reflection uses trainset while scoring uses valset.
2. **Given** only trainset, **When** evolution runs, **Then** trainset is used for both reflection and scoring.
3. **Given** candidate selection enabled and valset provided, **When** candidates are evaluated, **Then** selection uses valset scores.

---

## Contract Tests (Planned)

```python
# tests/contracts/test_train_val_contract.py

import pytest

class TestTrainValContract:
    def test_reflection_uses_trainset(self, engine, trainset, valset):
        result = engine.run(trainset=trainset, valset=valset)
        assert result.reflection_source == "trainset"

    def test_scoring_uses_valset(self, engine, trainset, valset):
        result = engine.run(trainset=trainset, valset=valset)
        assert result.scoring_source == "valset"

    def test_default_valset(self, engine, trainset):
        result = engine.run(trainset=trainset, valset=None)
        assert result.scoring_source == "trainset"
```
