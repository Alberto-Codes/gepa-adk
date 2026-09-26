# Delegate a Bounded Change

Use this procedure for supervised implementation in gepa-adk, whatever the model or harness.
The supervisor selects work, decides boundaries, verifies behaviour, commits and opens the pull request.
The worker implements a scoped change and returns evidence.
Apply the [bounded execution limits](https://github.com/Alberto-Codes/gepa-adk/blob/main/CLAUDE.md#bounded-execution) before dispatch.
Use one validation path. Do not add another harness to repeat required repository checks.

## Worker harnesses

gepa-adk has three worker harnesses.
The [worker run contract](../reference/worker-runs.md) records launch evidence for each.

- **pi** runs local models through the `delegate-to-pi` skill.
- **Claude sub agents** run through the Agent tool with definitions in `.claude/agents/`.
- **Cursor CLI** runs Cursor-pool models in print mode, guarded by `.cursor/cli.json`.

The Claude definitions are `builder.md`, `acceptance-reviewer.md` and `specifier.md`.

| Job | Harness and model |
|---|---|
| Lookups and file search | Agent tool, `haiku` |
| Research and documentation reads | Agent tool, `sonnet` |
| Implementation and gate repairs | Agent tool, `opus` with `builder`; pi with a local coder model; or Cursor CLI with a Cursor-pool model |
| Acceptance review | Agent tool, `opus` with `acceptance-reviewer` |
| Specification | Agent tool, `opus` with `specifier`; or pi with a local reasoning model |

The `delegate-to-pi` skill names the local models and their settings.
A fresh reviewer may inspect explicitly authorized supervisor contributions.
The implementer never supplies the independent verdict on their own changes.
The supervisor never asks a worker to double-check itself.
An acceptance review runs in a fresh agent, separate from the builder.

## 1. Make the task ready

The GitHub issue is the durable task record.
Its accepted specification lives in an issue comment, never on disk.
Pass the exact comment URL and its text in the brief. Never substitute the latest comment.
The builder and the Cursor worker never run `gh`, so the brief carries the contract text.

Request a read-only specification pass only when a concrete design question remains.
The `specifier` agent or a pi reasoning model can answer it.
Review its answer before implementation.
Skip that pass for a known defect with a decided fix and regression.

For behavioural changes, require a regression that fails before the fix.
Check that the failure shows missing behaviour, not a broken fixture.
Keep the test and implementation in the same deliverable and the same dispatch.

### Ownership, dependencies and evidence freshness

The issue contract names the supervisor, sole checkout writer, mechanical validation
owner and dependency issue/PR revisions. The supervisor owns release-round integration.
Independent work may proceed in separate worktrees. Shared-code rounds wait for their
dependency or name an integration boundary before implementation begins.

After repair, merge or conflict resolution, list the assertions affected by the diff.
Reuse evidence for unchanged assertions; independently exercise changed behaviour at
the integrated revision before acceptance. Prose-only repairs do not mandate a whole
new audit. Record finding → repair revision → independent command/result on the same
issue/PR. A builder's repair proof alone is not an independent verdict.

A review budget checkpoint returns **incomplete**, its verified and unverified
assertions, and the next owner. Never turn an unfinished review into a clean verdict.
For authorized supervisor implementation, use a fresh reviewer under the same rule.

Name one mechanical validation owner, normally the supervisor executing installed
pre-commit/pre-push hooks. Workers run assigned focused acceptance checks; reviewers
run independent probes and mutations. Reuse passing checks for unchanged revisions;
do not have every role repeat the gate table. Hook path filters govern applicability,
and an unrun required gate stays unverified. Verify both hook stages in each checkout.
Claude's PostToolUse hook is harness-specific; other harnesses must not claim it ran.

Cursor keeps its git/gh deny rules. Supply exact contract text, baseline HEAD, status,
diff and relevant history in its brief; the supervisor captures the final diff after
the worker stops. Harness limitations do not waive evidence requirements.

Issue-only work uses the issue and PR, with no required story ID or new ledger.
Optional story workflows remain available. Promote reusable lessons to shared guidance;
keep local memory as pointers to durable issue/PR evidence.

## 2. Size by behaviour

Start with one behaviour across two to four production files, plus tests and documentation.
Treat this range as an initial tuning rule, not a measured worker capability.
Split independent behaviours even when they fit in one file.
Keep an invariant together when a split would leave an unsafe intermediate state.

| Task shape | Dispatch |
|---|---|
| Decided behaviour with a failing acceptance test | Implement directly |
| Several independent behaviours or acceptance commands | Split into named slices |
| Unresolved port, adapter or ADR decision | Resolve the decision first |
| Small mechanical correction with an obvious proof | Use a short repair brief |
| Broad failure after repeated repairs | Reassess the contract and split again |

One GitHub issue need not equal one worker task.
Name the parent issue and slice in every dispatch.

## 3. Launch with a bounded brief

Use the template below. Replace every placeholder before dispatch.
Keep task context short. Link precise files and evidence instead of copying history.

Use one writer per checkout.
The supervisor creates the branch before dispatch, named under `.claude/rules/pull-requests.md`.
Record the branch, base revision and existing modifications before launch.
Keep temporary files outside the checkout, in the session scratchpad directory.

For pi, inspect the installed harness help before choosing options.
For a Claude sub agent, pass `model` on every Agent call and name the agent definition.
For Cursor, paste the full contract into the brief, because `gh` is denied to the worker.
Planning and review stay read-only. Implementation needs local edit and test permissions.

```text
Role: bounded implementation worker. The supervisor owns acceptance, the commit and the pull request.
Supervisor / worker / harness: <actual assignments; requested model or alias>
Issue and slice: <issue number, one behaviour>
Branch, base revision and existing modifications: <exact values>
Accepted specification: <exact issue comment URL and its text>
Decision and reason: <settled shape and why>
Read first: <targeted files and cited source URLs>
Allowed edits: <production, test and documentation paths>
Out of scope: <adjacent work and tempting incorrect fixes>

Acceptance:
- <observable invariant, exact command, expected result>
- <regression that must stay unchanged>
Run the acceptance test before implementation. Preserve its red output.
Do not weaken the acceptance test to obtain green output.
Validation owner: <one named owner; default supervisor through hooks>.
Run assigned focused checks during edits; leave mechanical gates to that owner.
Report required checks you did not run.

Skip session bookkeeping and backlog sweeps.
Do not edit CLAUDE.md, .claude/rules/, .claude/hooks/ or other policy files.
Do not run gh, commit, push, open a pull request, pass --no-verify or add a gate suppression.
Do not run pytest -m api unless this brief authorizes it.
Preserve unrelated changes. Do not reset, clean, stash or restore them.
If required edits exceed the allowed scope, return the missing scope.

Return: changed paths, red/green commands and output, unrun checks,
remaining gaps and your model identity. Leave the diff for review and stop.
```

## 4. Accept behaviour and finish

Read the diff against the agreed scope.
Run an independent probe of the defining behaviour.
Test real production behaviour, not a fake's own return values.
Confirm that the regression can detect the original defect.

The gate inventory is the gate table in the [repository rules](https://github.com/Alberto-Codes/gepa-adk/blob/main/CLAUDE.md#gates) and `.pre-commit-config.yaml`.
Never weaken a gate or report an unrun gate as green.

Return a failed assertion and a narrow correction brief when review finds a defect.
Default to one implementation, one independent review and one repair dispatch per behaviour.
Before another dispatch, report the unresolved assertion and why it can resolve it.
Reassess the contract when the same repair fails again.
Preserve the useful diff and evidence during reassessment.

The supervisor commits on the branch and opens a draft pull request per `.claude/rules/pull-requests.md`.
The pull request body follows `.github/PULL_REQUEST_TEMPLATE.md` and passes through `--body-file`.
The commit carries worker trailers from the worker's reported identity.
The authoritative API squash recipe in the PR rules preserves those trailers,
because the squash replaces the branch commits.
The pre-commit and pre-push hooks and CI are the gate before `main`.
Passing tests do not authorize a real LLM call.

## 5. Record outcomes and tune

Record proof and remaining work on the issue or the pull request.
Keep one record per slice. Link the commit instead of copying its evidence.

| Field | Evidence |
|---|---|
| Identity | Issue, slice, base revision, supervisor, worker model, harness and session identifier |
| Input | Accepted specification, planning or implementation |
| Size | Behaviour count, production files, tests and documentation |
| Cost | Elapsed time, reported tokens if available, supervisor repair time |
| Outcome | Accepted unchanged, accepted after repair, rejected or externally blocked |
| Proof | Red and green output, independent probe, gate results, accepted commit |
| Lesson | Specification, implementation, test, harness, environment or external failure |

Compare accepted behaviour and supervisor repair time, not lines written or worker confidence.
Group measurements by model, harness, reasoning setting, task type and size.
Treat unavailable measurements as unknown. Do not combine unlike token counters.
Separate external blocking from implementation failure.
Persist recurring rules here. Keep task facts in the accepted contract.
