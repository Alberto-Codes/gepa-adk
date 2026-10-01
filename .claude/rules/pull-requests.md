# Pull Request Rules

When creating a pull request, you MUST follow these rules exactly.

## Branch Naming Convention

Issue-only branches use `type/issue-description` (for example
`chore/470-workflow-ownership`); no sprint artifact is required.
When a story workflow is selected, branches follow `type/story-key`.

- **Story pattern**: `type/story-key`, where the key includes the epic, story and description (e.g., `feat/2-1-scorer-protocol`)
- **Type**: Matches conventional commit types: `feat | fix | docs | refactor | test | chore | perf`
- **Story key**: Taken directly from sprint-status.yaml (e.g., `2-1-scorer-protocol`)
- The branch name carries the story ID — no need to repeat it in commit messages or PR titles

Examples:
- `feat/2-1-scorer-protocol` (feature story)
- `fix/3-2-reflection-timeout` (bug fix story)
- `refactor/4-1-engine-extraction` (refactoring story)
- `chore/1-1-project-scaffold` (infrastructure story)

The `dev-story` workflow creates branches automatically using this convention.

## Always Draft

Always create PRs as **draft** using `--draft` flag. Ready PRs trigger automated code review, so a PR stays draft until the publication cycle under **Ready, Review and Merge** marks it ready with `gh pr ready`.

```bash
gh pr create --draft --body-file <path> ...
```

`.claude/hooks/pr_guard.py` enforces the mechanical half of these rules: `gh pr create` without `--draft` or without `--body-file` is refused. It only refuses those two; `gh pr ready` and `gh pr merge` run without a prompt and receive the review reminder as context. Write the PR body to a file and pass `--body-file`; a `--body` string bypasses the template silently.

## Always Use the PR Template

Read `.github/PULL_REQUEST_TEMPLATE.md` before composing the PR body. The body MUST follow the template structure exactly:

1. **Remove all HTML comments** from the template — keep only visible content
2. **PR title** follows conventional commits: `type(scope): description`
   - Types: `feat | fix | docs | refactor | test | chore | perf`
   - Scope: a noun describing a section of the codebase (NOT spec/issue numbers)
   - Breaking changes: add `!` after scope
3. **Body structure** (in order):
   - Why paragraph (problem solved, contrast with previous behavior)
   - What changed (2-4 bullets, imperative mood)
   - `Test:` line (command, manual steps, or "CI only")
   - `Closes #` trailer (if applicable)
   - Multi-commit footer blocks for release-please (if PR has multiple logical changes)
   - `---` separator
   - `## PR Review` section with Checklist, Review Focus, and Related subsections

## Ready, Review and Merge

Within existing user authorization, the supervisor drives publication and review.
Hook reminders do not confer permission. Ask only when scope or authority is missing.
GitHub Copilot review complements the issue contract's independent acceptance:

1. After `gh pr create --draft`, use `gh pr checks <N> --watch` in a tracked
   foreground session. Resume yielded handles; do not launch duplicate watchers.
2. When every check passes, run `gh pr ready <N>`. Inspect the PR timeline
   (`gh api repos/{owner}/{repo}/issues/<N>/timeline`) for a `review_requested`
   event whose reviewer login contains `opilot`. If none exists, request review
   once with `gh pr edit <N> --add-reviewer "@copilot"`. Never repeat the request:
   a `201` response is not proof that it registered.
   Then watch `pulls/<N>/reviews` for `copilot-pull-request-reviewer[bot]` and
   the timeline for the `review_requested` event in a tracked bounded wait of
   five minutes. Copilot normally reviews within that window.
   **Copilot blocker (#524):** when five minutes pass without a Copilot
   review, whether or not the `review_requested` event registered, the
   external blocker is established. Record it in one PR comment, posted with
   `gh pr comment <N> --body-file <path>`, that names what did not arrive,
   the wait, the acceptance record (reviewer role, resolved model id, verdict,
   reviewed revision) and the green checks. Then continue at step 5. Do not
   wait longer and do not repeat the request. Retest on the next PR and note
   the outcome on #524; retire this clause there when reviews arrive again.
3. Triage every inline finding under `.claude/rules/pr-review-comments.md`.
   Fix what is real, push, and reply on each thread. Push back on the rest
   with a reason. Resolve every thread through GraphQL
   `resolveReviewThread`, adopted or not. Do not merge over an open thread.
4. A push after the review re-runs CI. Wait for it to pass again.
5. When CI is green and either no thread is open or the Copilot blocker of
   step 2 is recorded, squash-merge through the API request file under
   **Squash and Merge** below: `sha` pinned to the accepted head, trailers preserved, no
   `Co-Authored-By`. The local checkout stays on the feature branch; GitHub
   deletes the remote branch on merge.

Publication requires authorized scope, complete independent acceptance, fresh
integration evidence, passing checks and resolved review threads. A recorded
Copilot blocker satisfies the review-thread requirement; it never replaces the
independent acceptance. Repair failures within the accepted contract; keep
missing evidence explicit until verified.

## Base Branch

- PRs target `main` unless explicitly told otherwise
- Always run `git diff main..HEAD` and `git log --oneline main..HEAD` to understand the full scope before writing the PR body

## Diff Before PR

Before creating a PR, always:

1. `git diff --stat main..HEAD` — understand file scope
2. `git log --oneline main..HEAD` — understand commit history
3. Read ALL commits (not just the latest) to write an accurate description

## No Co-Authored-By

Never add `Co-Authored-By` trailers (or any variation) to commit messages or PR descriptions. Commits and PRs should not attribute authorship to Claude.

## Hash References Are GitHub-Only

The `#N` syntax (e.g., `#180`, `Closes #42`) is **reserved for GitHub issues and PRs**. GitHub auto-links any `#N` to the corresponding item, so using it for non-GitHub references creates incorrect links.

- **Correct**: `Closes #180` (real GitHub issue), `feat(ci): add hook definition` (no story ref needed)
- **Wrong**: `feat(ci): add hook definition (#23.4)` — GitHub links `#23` to issue/PR 23
- BMAD story IDs (e.g., 23.4) must NOT appear with `#` prefix in commit messages, PR titles, or PR bodies
- The branch name already carries the story ID (e.g., `feat/ci-23-4-pre-commit-hook-definition`) — no need to repeat it in the commit subject
- If a story reference is needed in the PR body, use plain text: `Story 23.4` (no `#`)

## Push Before PR

Ensure the branch is pushed to remote with `-u` before creating the PR:

```bash
git push -u origin <branch-name>
```

## Squash and Merge

Use only the API squash endpoint. It leaves the local checkout with its owner.
Before merging, verify the accepted head, all required checks and resolved threads
at that head; check integration freshness under the delegation procedure.

Create a JSON request file outside the checkout with:

- `merge_method`: `squash`
- `sha`: the full accepted PR head SHA (reject a concurrent head change)
- `commit_title`: the conventional PR title
- `commit_message`: the PR body above `---`, including closing references,
  release-please footer blocks and all actual `Generated-By`/`Specified-By` trailers

Exclude the PR Review section and never add `Co-Authored-By`. Use a structured JSON
writer so newlines and literal text survive; do not interpolate the body into shell code.

```bash
gh api --method PUT repos/{owner}/{repo}/pulls/<N>/merge --input <request.json>
```

Verify `merged: true` and record the resulting SHA. A successful HTTP request alone
is insufficient. GitHub's repository setting handles remote branch deletion; do not
switch or delete the local branch while its checkout is owned. No alternate
`gh pr merge --delete-branch` recipe applies.
