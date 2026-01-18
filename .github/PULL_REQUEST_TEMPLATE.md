<!--
AI: Remove all HTML comments when filling this template. Keep only visible content.

PR Title → squash commit subject (50 chars, imperative)
Format: type(scope): description
Types: feat | fix | docs | refactor | test | chore | perf

Scope: A noun describing a section of the codebase (per conventionalcommits.org).
  ✓ feat(engine): add ADK reflection agents
  ✓ feat(adapter): support Ollama models
  ✗ feat(034-feature): ...  ← NOT spec/issue numbers (breaks release-please)

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

<!--
═══════════════════════════════════════════════════════════════════════════════
MULTI-COMMIT PRs (release-please)
═══════════════════════════════════════════════════════════════════════════════
When a PR contains multiple logical changes that would normally be separate
commits, add additional conventional commit blocks as FOOTERS at the bottom
of the body (above this checklist section). Release-please parses these to
generate proper changelog entries.

Format: blank line, then type(scope): description, then details

Example PR body structure:
─────────────────────────────────────────────────────────────────────────────
Primary change description (associated with PR title).

- Bullet points for primary change

Test: `uv run pytest -v`

Closes #123

feat(models)!: rename field for consistency

BREAKING CHANGE: `OldName` → `NewName` in SomeClass

docs(reference): add glossary

- Define canonical terminology
─────────────────────────────────────────────────────────────────────────────

The PR title becomes the first changelog entry. Each footer block (starting
with a conventional commit type) becomes an additional entry.

Ref: https://github.com/googleapis/release-please#what-if-my-pr-contains-multiple-fixes-or-features
-->

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
