# Contract: Frontier Tracking

**Feature**: 027-frontier-eval-policy
**Date**: 2026-01-15

## Overview

This contract defines the behavior of ParetoFrontier and ParetoState for all frontier types.

---

## FrontierType Behavior Matrix

| FrontierType | Required Data | Updated Structures | Key Type |
|--------------|---------------|-------------------|----------|
| INSTANCE | `scores: dict[int, float]` | example_leaders, best_scores | `int` |
| OBJECTIVE | `objective_scores: dict[str, float]` | objective_leaders, objective_best_scores | `str` |
| HYBRID | Both of above | All instance + objective fields | `tuple[str, int]` or `tuple[str, str]` |
| CARTESIAN | Both + per-example objective | cartesian_leaders, cartesian_best_scores | `tuple[str, int, str]` |

---

## Contract: ParetoState.add_candidate

### Input Validation

```gherkin
Scenario: INSTANCE frontier type accepts scores without objective_scores
  Given frontier_type is INSTANCE
  And candidate has scores {0: 0.8, 1: 0.6}
  And objective_scores is None
  When add_candidate is called
  Then candidate is added successfully
  And example_leaders is updated

Scenario: OBJECTIVE frontier type requires objective_scores
  Given frontier_type is OBJECTIVE
  And candidate has scores {0: 0.8, 1: 0.6}
  And objective_scores is None
  When add_candidate is called
  Then ConfigurationError is raised
  And message contains "objective_scores required for frontier_type=OBJECTIVE"

Scenario: HYBRID frontier type requires objective_scores
  Given frontier_type is HYBRID
  And objective_scores is None
  When add_candidate is called
  Then ConfigurationError is raised

Scenario: CARTESIAN frontier type requires objective_scores
  Given frontier_type is CARTESIAN
  And objective_scores is None
  When add_candidate is called
  Then ConfigurationError is raised
```

### Frontier Updates

```gherkin
Scenario: INSTANCE updates example leaders
  Given frontier_type is INSTANCE
  And existing best_scores = {0: 0.7}
  And new candidate scores = {0: 0.8}
  When add_candidate is called
  Then best_scores[0] == 0.8
  And example_leaders[0] == {new_candidate_idx}

Scenario: OBJECTIVE updates objective leaders
  Given frontier_type is OBJECTIVE
  And existing objective_best_scores = {"accuracy": 0.7}
  And new candidate objective_scores = {"accuracy": 0.9}
  When add_candidate is called
  Then objective_best_scores["accuracy"] == 0.9
  And objective_leaders["accuracy"] == {new_candidate_idx}

Scenario: HYBRID updates both instance and objective
  Given frontier_type is HYBRID
  When add_candidate is called with scores and objective_scores
  Then example_leaders is updated
  And objective_leaders is updated

Scenario: CARTESIAN updates per (example, objective) pairs
  Given frontier_type is CARTESIAN
  And new candidate has:
    - scores = {0: 0.8, 1: 0.6}
    - per_example_objective_scores = {
        0: {"accuracy": 0.9, "latency": 0.7},
        1: {"accuracy": 0.8, "latency": 0.9}
      }
  When add_candidate is called
  Then cartesian_best_scores[(0, "accuracy")] == 0.9
  And cartesian_best_scores[(0, "latency")] == 0.7
  And cartesian_best_scores[(1, "accuracy")] == 0.8
  And cartesian_best_scores[(1, "latency")] == 0.9
```

---

## Contract: ParetoFrontier.get_pareto_front_mapping

```gherkin
Scenario: INSTANCE returns example-keyed mapping
  Given frontier_type is INSTANCE
  And example_leaders = {0: {1, 2}, 1: {2, 3}}
  When get_pareto_front_mapping(INSTANCE) is called
  Then result == {0: {1, 2}, 1: {2, 3}}
  And all keys are int

Scenario: OBJECTIVE returns objective-keyed mapping
  Given frontier_type is OBJECTIVE
  And objective_leaders = {"accuracy": {1}, "latency": {2}}
  When get_pareto_front_mapping(OBJECTIVE) is called
  Then result == {"accuracy": {1}, "latency": {2}}
  And all keys are str

Scenario: HYBRID returns combined mapping with type tags
  Given frontier_type is HYBRID
  And example_leaders = {0: {1}}
  And objective_leaders = {"accuracy": {2}}
  When get_pareto_front_mapping(HYBRID) is called
  Then result == {
    ("val_id", 0): {1},
    ("objective", "accuracy"): {2}
  }
  And all keys are tuples with type tag

Scenario: CARTESIAN returns (example, objective) keyed mapping
  Given frontier_type is CARTESIAN
  And cartesian_leaders = {(0, "accuracy"): {1}, (1, "latency"): {2}}
  When get_pareto_front_mapping(CARTESIAN) is called
  Then result == {
    ("cartesian", 0, "accuracy"): {1},
    ("cartesian", 1, "latency"): {2}
  }
```

---

## Contract: Tie Handling

```gherkin
Scenario: Equal scores add to existing leader set
  Given existing best_scores[0] = 0.8
  And existing example_leaders[0] = {1}
  And new candidate scores = {0: 0.8}
  When add_candidate is called
  Then best_scores[0] == 0.8 (unchanged)
  And example_leaders[0] == {1, new_candidate_idx} (both leaders)

Scenario: Lower scores do not update frontier
  Given existing best_scores[0] = 0.9
  And new candidate scores = {0: 0.7}
  When add_candidate is called
  Then best_scores[0] == 0.9 (unchanged)
  And new_candidate_idx not in example_leaders[0]
```

---

## Contract: Backward Compatibility

```gherkin
Scenario: Default frontier_type is INSTANCE
  When ParetoState is created without frontier_type parameter
  Then frontier_type == FrontierType.INSTANCE

Scenario: INSTANCE works without objective_scores
  Given frontier_type is INSTANCE (default)
  And add_candidate called with scores only
  Then operation succeeds
  And objective_* fields remain empty

Scenario: Existing tests pass unchanged
  Given tests that use frontier_type=INSTANCE implicitly
  When run against new implementation
  Then all tests pass
```

---

## Implementation Checklist

### ParetoFrontier

- [ ] Add `objective_leaders: dict[str, set[int]]` field
- [ ] Add `objective_best_scores: dict[str, float]` field
- [ ] Add `cartesian_leaders: dict[tuple[int, str], set[int]]` field
- [ ] Add `cartesian_best_scores: dict[tuple[int, str], float]` field
- [ ] Implement `update_objective()` method
- [ ] Implement `update_cartesian()` method
- [ ] Implement `get_pareto_front_mapping(frontier_type)` method

### ParetoState

- [ ] Remove INSTANCE-only restriction in `__post_init__`
- [ ] Add `candidate_objective_scores: dict[int, dict[str, float]]` field
- [ ] Modify `add_candidate()` to accept optional `objective_scores`
- [ ] Validate objective_scores presence for OBJECTIVE/HYBRID/CARTESIAN
- [ ] Route updates to appropriate frontier methods based on frontier_type
