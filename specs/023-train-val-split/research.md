# Research: Train/Val Split for Evolution Scoring

**Feature**: 023-train-val-split
**Date**: 2026-01-14

## Research Summary

This research captures how the upstream GEPA implementation separates reflection (trainset) from scoring (valset) and maps those patterns to gepa-adk's async, hexagonal architecture.

---

## 1. Upstream Dataset Split Behavior

### Decision
Use trainset for reflection (trace capture and reflective dataset building) and valset for all scoring decisions (baseline/proposal scoring, acceptance, and Pareto scoring). Default valset to trainset when omitted.

### Rationale
- Upstream GEPA normalizes datasets by defaulting valset to trainset in `gepa.api.optimize`.
- `ReflectiveMutationProposer` uses `trainset` for reflection minibatches and trace capture.
- `GEPAEngine` evaluates candidates on the `valset` for scoring and frontier tracking.

### Alternatives Considered
1. **Single shared dataset for everything**: Rejected - encourages overfitting and diverges from upstream behavior.
2. **Random split inside gepa-adk**: Rejected - unexpected data manipulation; user should control dataset boundaries.
3. **Post-hoc valset scoring only**: Rejected - acceptance decisions would still be trainset-based.

### References
- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/api.py
- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/proposer/reflective_mutation/reflective_mutation.py
- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/core/engine.py

---

## 2. Scoring and Acceptance Source of Truth

### Decision
Treat valset-based scores as the authoritative basis for acceptance decisions and candidate selection. Trainset scores are for reflection-only diagnostics.

### Rationale
- Acceptance decisions should reflect generalization performance (valset).
- Upstream GEPA uses valset scores for frontier selection and logging.
- Keeping reflection scores separate avoids mixing trace data with evaluation data.

### Alternatives Considered
1. **Use reflection minibatch scores for acceptance**: Rejected - biased to trainset subset.
2. **Blend trainset and valset scores**: Rejected - ambiguous interpretation and harder to test.

### References
- /var/home/Alberto-Codes/Projects/gepa-adk/.venv/lib/python3.12/site-packages/gepa/core/engine.py

---

## 3. Reporting and Result Semantics

### Decision
Expose valset-based scoring outcomes in evolution results and logs, distinct from reflection metrics.

### Rationale
- Clarity for users interpreting acceptance and Pareto decisions.
- Aligns with success criteria requiring valset-based decisions.
- Maintains backward compatibility by preserving existing result fields where possible.

### Alternatives Considered
1. **Keep existing result fields unchanged**: Rejected - hides critical distinction between train/val scoring.
2. **Replace all scores with valset scores**: Rejected - would remove useful reflection diagnostics.

---

## 4. Testing Strategy Alignment

### Decision
Add contract, unit, and integration tests that explicitly verify dataset split behavior and defaulting logic.

### Rationale
- Constitution mandates three-layer testing.
- Dataset split is a behavior change with regression risk.
- Tests should verify acceptance uses valset and reflection uses trainset.

### Alternatives Considered
1. **Unit tests only**: Rejected - lacks end-to-end validation.
2. **Integration tests only**: Rejected - slow feedback and insufficient isolation.

---

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| What dataset should drive acceptance decisions? | Valset scores only; trainset used for reflection only. |
| What happens when valset is omitted? | Default valset to trainset for backward compatibility. |
| Where should trace capture occur? | Trainset reflection evaluation only. |
