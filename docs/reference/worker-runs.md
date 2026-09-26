# Worker Run Contract

This contract separates project requirements from the model and harness that run them.
The [delegation procedure](../contributing/delegate-work.md) holds the task sequence and acceptance rules.

## Roles

| Role | Responsibility |
|---|---|
| Supervisor | Select work, settle decisions, own acceptance, commit on a branch and open the draft pull request |
| Specifier, when needed | Propose a bounded decision and executable contract; report uncertainty and evidence |
| Worker | Implement the assigned contract within its allowed paths and return evidence |
| Reviewer | Check the actual diff and independently exercise the defining behaviour |

Roles need not use different model families. A model name alone does not establish independent review.
The reviewer uses production evidence and independent probes, not the worker's completion claim.
A fresh reviewer may independently inspect explicitly authorized supervisor contributions;
the implementer cannot provide their own independent verdict.
Changing models never expands permissions or authorizes a real LLM call.

## Harness boundary

gepa-adk has three worker harnesses.
pi runs local models through the `delegate-to-pi` skill.
Claude Code sub agents run through the Agent tool with definitions in `.claude/agents/`.
The Cursor CLI runs Cursor-pool models in print mode.
Choose the worker independently from the supervisor.

| Harness | Required launch evidence |
|---|---|
| pi | Installed version, provider/model, effective `--thinking` setting, instruction loading, tool permissions, session identifier |
| Claude sub agent | Requested alias (`haiku`, `sonnet` or `opus`), resolved model ID from the agent's return or `unknown`, effort, allowed tools, agent definition name |
| Cursor CLI | Installed version, requested model ID, identity the worker reports or `unknown`, `session_id` and usage from the JSON receipt, `.cursor/cli.json` deny list |
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
| Configuration | Harness and version, requested and resolved model, effort or reasoning setting, tool permissions |
| Observation | Session or agent identifier, start and end times, output location and final exit state |
| Outcome | Acceptance disposition, tested revision, independent evidence, repairs and remaining blockers |
| Cost | Elapsed time, supervisor repair time, and reported tokens with their source |

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

Use one tracked foreground wait (for example `gh pr checks N --watch`) whose completion
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
