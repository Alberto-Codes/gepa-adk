<!--
AI: Remove all HTML comments when filling this template. Keep only visible content.

PR Title → squash commit subject (50 chars, imperative)
Format: type(scope): description
Types: feat | fix | docs | refactor | test | chore | perf
Scope: (XXX-feature-name) from specs/ -or- (component) e.g., engine, adapter
Breaking: add ! after scope → feat(engine)!: remove deprecated method
-->
<!--
Why this change? Problem solved? Contrast with previous behavior.
e.g., "Evolution relied solely on mutation. This adds crossover to combine strengths from different branches."
-->

<!--
What changed? 2-4 bullets, imperative mood.
e.g., - Add MergeProposer for genetic crossover
      - Extend ParetoState with parent tracking
-->
-

<!-- How to verify: command, manual steps, or "CI only" -->
Test: `uv run pytest -v`

<!--
Git trailers (one per line):
  Closes #123
  BREAKING CHANGE: remove deprecated foo() method
  Co-authored-by: Name <email>
-->
Closes #

---

## PR Review

### Checklist
- [ ] Self-reviewed my code
- [ ] Tests pass (`uv run pytest`)
- [ ] Lint passes (`uv run ruff check .`)
- [ ] Breaking changes use `!` in title and `BREAKING CHANGE:` in body

### Review Focus
<!-- Where should reviewers concentrate? Known limitations? -->

### Related
<!-- Other PRs, issues, ADRs for context -->
