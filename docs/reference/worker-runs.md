# Worker Run Contract

This contract separates project requirements from the model and harness that run them.
The [delegation procedure](../contributing/delegate-work.md) holds the task sequence and acceptance rules.

## Shared roles

This section is the one copy of each role's duties. The agent definitions in
`.claude/agents/` point here and do not restate them.

Every harness loads `CLAUDE.md`, the matching role below and the accepted issue
contract before work starts. Record which instructions were loaded and how:
inherited context, explicit reads or supplied text. When a harness denies
`git` or `gh`, the supervisor supplies the
[restricted-worker evidence](#restricted-worker-evidence). Keep those denials.
Missing context is a blocker, not permission to bypass them.

Roles need not use different model families. A model name alone does not establish independent review.
The reviewer uses production evidence and independent probes, not the worker's completion claim.
No author accepts their own work. Every change needs a fresh reviewer who authored none of it,
including supervisor contributions.
Changing models never expands permissions or authorizes a real LLM call.

### Supervisor

Select work, settle decisions and accept results. Preserve one writer per checkout.
Commit on a branch and open the draft pull request under `.claude/rules/pull-requests.md`.
The accepted contract must name any supervisor implementation exception.
Such an exception still needs fresh independent acceptance; supervisor self-review is not independent evidence.
Do not dispatch a duplicate review merely to repeat valid evidence.

### Specifier

Read the issue, the cited files and the relevant sources. Return one bounded contract under 150 words.
Name the decision, acceptance command and expected red output, allowed paths, exclusions and stopping condition.
For research or documentation, name an observable acceptance check instead of a code test.
Name one behaviour. Split the issue if it holds more than one.
Separate instruction conflicts, missing requirements and failures to follow existing rules.
Report unresolved evidence. Do not silently select a disputed source.
Cite the source URL for each external API detail. Write `#N` only for a GitHub issue or pull request.
Do not edit tracked files. Post only when the brief authorizes posting, with the
`Specified-By` byline on the first line.

### Builder

Record the baseline and preserve unrelated work. Edit only the allowed paths.
For behaviour changes, run the acceptance test before production edits. Preserve the command and red output.
Confirm that the missing behaviour, not a broken fixture, causes the failure. Implement, then preserve the green output.
Never weaken, skip or delete a test, and never suppress a gate.
Run the assigned focused checks under the [gate evidence](#gate-evidence) rules; leave the hook stages to the named validation owner.
Return changed paths, red and green evidence, gate accounting, remaining gaps and the [run receipt](#run-receipt) fields.
Do not commit, push, open a pull request or change policy unless the brief assigns it.

### Acceptance-reviewer

Use a fresh session, separate from the builder and from any supervisor implementation session.
Inspect the actual submitted revision and diff. Record their identity, including uncommitted changes.
Check allowed paths, preserved behaviour, weakened or removed tests and gate suppressions.
Challenge both the accepted contract and the parent outcome. A faithful implementation can expose an
inadequate contract; report that as a specification finding.
Read the contract before the builder summary. Treat that summary as a claim.
Run an independent positive probe and a relevant counterexample through the real entry point.
Prove the acceptance check detects the missing behaviour under the
[isolated failure proof](../contributing/delegate-work.md#isolated-failure-proof) rules.
A test that cannot fail is a blocking finding.
Check the three blind spots in `CLAUDE.md`: a test that passes whether or not the behaviour happens,
a helper that raises where the specification said return, and an unwrapped secret bound to a local
that `--showlocals` would print.
Report every finding with claim, evidence, impact and correction.

Review leaves the checkout, submitted code and tracked fixtures unchanged.
Mutations run only in a scratch copy the brief names. Without that permission, return the probe as unverified.
Scratch permission never authorizes live LLM calls, commits, pushes or edits to submitted files.

### Review completion

Verdicts are **accept**, **repair**, **reject** and **incomplete**.
Accept only when every required assertion has current evidence and no blocking finding remains.
Repair names a bounded correction. Reject explains why the submitted approach cannot satisfy the contract.
Incomplete names verified and unverified assertions, the next command, the evidence location and the reviewed revision.
Start with eight tool calls or three minutes, whichever comes first.
A budget limit is a checkpoint, never acceptance.
Resume an unchanged review in the same session, or pass its evidence to another fresh reviewer.
After a repair or integration, revalidate affected assertions on the new revision; reuse unaffected
evidence under the [gate evidence](#gate-evidence) rules. Record the continuation or repair on the issue or pull request.

## Gate evidence

The gate table in `CLAUDE.md` and the installed hooks are the one validation path.
Record each required command, its result, the tested revision or diff and the relevant inputs.
Reuse a passing result only when those inputs are unchanged, and name the earlier receipt.
Mark every gate as run, reused, deferred to a normal hook, or unrun with a reason.
Deferral is not a pass. Never narrow or silence a required gate.

## Harness boundary

gepa-adk has three worker harnesses.
pi runs local models through the `delegate-to-pi` skill.
Claude Code sub agents run through the Agent tool with definitions in `.claude/agents/`.
The Cursor CLI runs Cursor-pool models in print mode.
Choose the worker independently from the supervisor, and choose the model weight
(light, medium or heavy) independently from the harness.
A `pi-fit` issue authorizes any verified worker harness; it does not select one.

Codex and the Copilot CLI have no gepa-adk receipts yet.
Start either one under [change a model or harness with evidence](#change-a-model-or-harness-with-evidence)
and record the rows below.

User-scope configuration (global Claude Code, Cursor, Codex, Copilot or pi settings,
skills, hooks and model defaults) may already exist on the operator machine.
Record the effective harness in the receipt. Project files are the floor for a
clean checkout, not the only place a harness may be configured.

| Harness | Required launch evidence |
|---|---|
| pi | Installed version, provider/model, effective `--thinking` setting, instruction loading, tool permissions, session identifier |
| Claude sub agent | Requested alias (`haiku`, `sonnet` or `opus`; never Fable), resolved model ID from the agent's return or `unknown`, effort, allowed tools, agent definition name |
| Cursor CLI | Installed version, requested model ID, identity the worker reports or `unknown`, `session_id` and usage from the JSON receipt, `.cursor/cli.json` deny list |
| Copilot CLI | Installed version, requested model (must be `auto`), `--auto-tier` if set, resolved identity if shown or `unknown`, print-mode flags |
| Codex | Installed version, loaded instructions and their source, tool permissions, session identifier, requested and resolved identity or `unknown`, effort and usage when available |
| Any other harness | The same role, context, isolation, observation and return requirements |

Read installed help and configuration before constructing a pi launch command.
Do not copy flags, approval modes or token limits between harnesses.
Keep planning and review read-only.
Implementation needs only the permissions its assigned edits and checks require.

Launch a Cursor worker from the checkout root with the brief as the prompt:

```bash
cursor-agent -p --force --trust --output-format json \
  --model cursor-grok-4.6-medium "$(cat brief.md)" > receipt.json
```

Keep `brief.md` and `receipt.json` outside the checkout.
`--force` applies edits without prompting, so `.cursor/cli.json` is the only guard.
It denies `git`, `gh`, `rm`, the policy files and the credential files.
Pass only `cursor-grok-*`, `grok-*`, `composer-*` or `gemini-*` IDs.
Other IDs and `auto` bill the Anthropic and OpenAI pool instead.
A `resource_exhausted` error before any edit is a service failure. Retry once.

A requested alias such as `opus` is not a resolved model identity.
Record both the requested alias and the resolved identity the agent reports.
If the harness does not expose the identity, record `unknown` rather than guessing.

## Restricted-worker evidence

The Cursor CLI cannot run `git` or `gh` under `.cursor/cli.json`.
Before dispatch, the supervisor supplies this packet in the brief:

- The exact accepted issue comment URL and its full text.
- The branch, base revision and staged, unstaged and relevant untracked state.
- The relevant source and diff, with paths, for the tested snapshot.
- The named validation owner and any existing command output with its revision.

The issue comment stays authoritative; the embedded copy only transports it.
Record when the supervisor captured the packet and which revision it describes.
The worker compares the files it can read with the packet before relying on it.
Missing or stale inputs mean an incomplete return that names the required evidence.
Do not broaden permissions or remove deny rules to obtain evidence.
If a denied action is necessary, the supervisor performs it within the authorized scope,
and captures the final diff after the worker stops.

Every harness reports its actual instruction loading and effective tool permissions.
A role prompt is not a sandbox. Do not claim isolation the harness does not enforce.
Record the harness actually used, even when a role definition came from another harness.

## Worker trailers

Worker trailers are evidence. They record which worker model produced the code or the specification, so the workers can be evaluated.

- A pi-written commit carries `Generated-By: <model> (local, via pi)`.
- A Claude sub agent commit carries `Generated-By: <resolved model id> (via Claude Code Agent tool, <agent name>)`.
- A Claude sub agent specification carries `Specified-By: <resolved model id> (via Claude Code Agent tool, specifier)`.
- A Cursor worker commit carries `Generated-By: <requested model id> (via Cursor CLI <version>, print mode)`.
- The supervisor's own commits carry no worker trailer.
- Never invent a resolved ID. The ID comes from the agent's return, never from the requested alias.
- The API squash recipe in `.claude/rules/pull-requests.md` keeps the trailers, because the squash replaces the branch commits.

`.claude/rules/pull-requests.md` forbids `Co-Authored-By`, and that rule stands.
`Co-Authored-By` claims authorship for Claude in commits and pull requests.
`Generated-By` and `Specified-By` claim no authorship. They record the worker as evaluation evidence.
Both worker trailers are allowed. `Co-Authored-By` stays forbidden.

## Run receipt

Keep this information in the issue or pull request acceptance record.
Do not introduce a second ledger that duplicates it.

| Field | Meaning |
|---|---|
| Assignment | Issue, slice, accepted comment, supervisor, worker role and allowed paths |
| Baseline | Branch, base revision, existing modifications and acceptance-test revision |
| Configuration | Actual harness and version, requested and resolved model, weight class, effort or reasoning setting |
| Instructions and permissions | Instructions actually loaded and how, and the effective tool permissions observed; a role prompt is not a sandbox |
| Observation | Session or agent identifier, start and end times, output location and final exit state |
| Outcome | Acceptance disposition, tested revision, independent evidence, repairs and remaining blockers |
| Cost | Duration, supervisor repair time, and each usage counter with its source; `unknown` when unavailable |

Record factual contributions separately when different models specify and implement a change.
Do not attribute supervisor corrections to the worker.
Store concise redacted evidence. Raw logs stay local unless checked and authorized for publication.
Never include API keys, `.env` contents or environment dumps in briefs, receipts or issue comments.

## Preserve the baseline

Use one writer per checkout. Record HEAD and staged and unstaged changes before dispatch.
Record untracked task files the worker could overwrite.

After the worker stops, compare the baseline and the returned diff.
A clean final tree does not prove safety.
A worker can discard an earlier uncommitted change and leave no diff.
Investigate missing or unexpectedly restored files before accepting the run.
Check for an unexpected HEAD change, including a commit the brief forbade.
Do not restore files automatically while another actor may be editing them.

## Observe completion and classify failure

A launch command, live process, idle log or zero exit code alone does not prove completed work.
Confirm the final output, changed files and acceptance evidence.
Do not terminate another session or launch a competing writer because a log is silent.

| Failure class | Supervisor action |
|---|---|
| Specification | Correct the accepted contract; do not blame faithful implementation |
| Implementation | Return the failing input and expected behaviour as a bounded repair |
| Acceptance test | Repair the fixture or oracle without weakening the intended behaviour |
| Harness or configuration | Diagnose launch, model resolution, permissions, reasoning setting and completion state |
| Environment | Name the unavailable dependency or service and repair it within scope |
| External dependency | Record the blocking event and continue independent authorized work |

Do not shrink every task in response to a harness fault.
Do not call a tool failure a model-quality failure, or a missing metric a zero-cost run.
A regression needs a demonstrated failure on the defect or a deliberate local mutation.

### Completion and release ownership

Use one tracked foreground wait (for example `gh pr checks <N> --watch`) whose completion
returns to the supervisor. If a tool yields a live session handle, resume that handle;
observation timeout or silence does not authorize a restart. Background waits are allowed
only when the harness guarantees a completion notification to the same supervisor.
Recheck authoritative PR head/check/review state after any wait before acting.

The supervisor records implementation accepted, integrated revision accepted, artifact
built, installed artifact exercised and published as separate milestones on the existing
release issue/PR. A round whose CI is pending is not integrated acceptance. Dependent
rounds wait or use isolated worktrees and an explicit integration boundary.
Consumer-behaviour claims identify the exact artifact and installed package path.
A working installation or completed evolution loop does not prove candidate quality;
report measured results separately. Reuse the existing release procedure and relevant
public-interface smoke; this adds neither live calls nor a separate release gate.

## Change a model or harness with evidence

Start a replacement on one small slice with a known acceptance oracle.
Check that it loads instructions, uses permitted tools, preserves the baseline and reports completion.
Run the same acceptance contract and required gates used for the current worker.
Record repairs and configuration before expanding its scope.
One successful slice establishes compatibility for that slice, not general reliability.

Reuse existing tests and real issue slices. Do not build a benchmark project first.
Update the launch recipe when a recurring failure is specific to the harness.
Update shared policy only when the lesson applies across tasks and models.
Keep machine-specific paths, credentials and process identifiers out of shared policy.
