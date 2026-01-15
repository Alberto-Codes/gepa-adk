# Research: Align Acceptance Scoring with Upstream GEPA

## Decision 1: Acceptance uses sum aggregation on iteration batch

**Decision**
Use the sum of per-example scores from the iteration evaluation batch to drive
acceptance decisions, matching upstream GEPA.

**Rationale**
Upstream GEPA accepts proposals based on the sum of subsample scores. In
`.venv/lib/python3.12/site-packages/gepa/core/engine.py`, acceptance compares
`sum(proposal.subsample_scores_after)` against
`sum(proposal.subsample_scores_before)`. Aligning to this behavior preserves
comparability with upstream runs and benchmarks.

**Alternatives considered**
- Keep mean-only acceptance (current behavior). Rejected because it diverges
  from upstream acceptance semantics.
- Switch to sum-only without a compatibility option. Rejected because it would
  break existing experiments relying on mean-based acceptance.

## Decision 2: Valset tracking remains mean-based

**Decision**
Track validation-set performance using the mean of per-example scores.

**Rationale**
Mean-based reporting is stable across different valset sizes and aligns with
current reporting expectations in gepa-adk. Upstream uses mean-like aggregation
for valset tracking (see `gepa/core/state.py` valset score calculations).

**Alternatives considered**
- Track valset via sum for consistency with acceptance. Rejected due to
  sensitivity to valset size and reduced interpretability.

## Decision 3: Backward compatibility via configurable acceptance metric

**Decision**
Introduce a configuration option to choose acceptance aggregation: "sum" for
upstream parity, "mean" for legacy behavior.

**Rationale**
Allows existing users to preserve historical baselines while enabling upstream
comparability. This also enables A/B evaluation of acceptance modes.

**Alternatives considered**
- Introduce a separate API or flag outside EvolutionConfig. Rejected to keep
  configuration centralized and consistent with existing patterns.

## Decision 4: Error handling for invalid score lists

**Decision**
Treat empty score lists or non-finite values as invalid inputs for acceptance,
returning clear configuration/validation errors.

**Rationale**
Acceptance aggregation is undefined for empty batches, and NaN/inf values can
silently corrupt evolution decisions. Explicit errors improve debuggability.

**Alternatives considered**
- Silently skip acceptance on invalid scores. Rejected because it can mask
  evaluation failures and lead to inconsistent state.
