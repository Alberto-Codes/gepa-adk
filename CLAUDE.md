# gepa-adk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Start here

For issue-driven work, read the accepted issue comment and its dependency pointers,
then [the delegation procedure](docs/contributing/delegate-work.md) and
[PR rules](.claude/rules/pull-requests.md). The issue/PR is authoritative;
optional story artifacts apply only when that workflow is selected. Local memory
is an index to those records, not a competing task contract.

Current policy follows.

<!-- MANUAL ADDITIONS START -->

## Model Identifiers

Docs, examples, and docstrings default to local open-source models (`ollama_chat/...`)
rather than hosted ones, so published examples cannot be retired by a vendor.
`docs/reference/model-selection.md` is authoritative: it names the two standard models,
the surfaces that must still use a Gemini string and why, and the update procedure when
Google announces a retirement. `tests/fixtures/models.py` holds the single model the
`requires_gemini` tier uses plus the deprecation rule the guard tests read.

## Supervised workers

The [shared roles](docs/reference/worker-runs.md#shared-roles) govern every
harness. Roles describe responsibility, not model brands. Record the actual
supervisor, worker, harness and model weight for each dispatch.

Three choices stay independent:

| Choice | Meaning |
|---|---|
| Role | supervisor, specifier, builder, acceptance-reviewer |
| Harness | the program that runs the model (Claude Code, pi, Cursor CLI, Codex, Copilot CLI) |
| Weight | light, medium or heavy capacity for this job |

Issue labels keep their names. `pi-fit` is this repository's `worker-fit`
label: the contract is mechanical enough for any verified worker harness.
`pi-fit` does **not** mean "use pi" or "use a small model". `judgment` means
the work needs the supervisor. `size-S`, `size-M` and `size-L` size the work.
Pick the harness and the weight separately after the issue is ready.

gepa-adk has three worker harnesses: pi, through the `delegate-to-pi` skill;
Claude Code sub agents, through the Agent tool and the definitions in
`.claude/agents/`; and the Cursor CLI in print mode, guarded by
`.cursor/cli.json`. Any other harness meets the same role, isolation and
evidence bar in [the worker run contract](docs/reference/worker-runs.md).

**Fable is supervisor-only.** Never run a Claude Code sub agent, pi or any
worker on Fable; pass a model on every Agent call. Do not `fork` from a Fable
session, because a fork inherits its model.

Behaviour changes under `src/` follow the
[required chain](docs/contributing/delegate-work.md#required-chain-for-behaviour-changes):
accepted contract, builder, fresh acceptance-reviewer, then the supervisor
commit and draft pull request. A chat turn that edits behaviour without a
builder dispatch breaks this chain, unless the accepted contract names a
supervisor exception. No author accepts their own work, including the
supervisor.

- The supervisor selects work, decides boundaries and accepts the result.
- The supervisor commits on a branch and opens the draft pull request under
  `.claude/rules/pull-requests.md`.
- A worker follows its brief and skips session bookkeeping.
- A worker never commits, pushes, opens a pull request or edits policy.
- Each checkout has one writer, including the supervisor. Preserve unrelated changes.
- Name one mechanical validation owner in the issue/brief; use the existing hooks
  and gates. Independent reviewers exercise affected assertions, not a second gate suite.

Use [the delegation procedure](docs/contributing/delegate-work.md) for sizing,
acceptance, repairs and the brief. Use
[the worker run contract](docs/reference/worker-runs.md) for launch evidence
and worker trailers.

## Issues before agents

A research, port, design or implementation ask that will outlive one turn
belongs on a GitHub issue before a worker runs.

**Standing permission to file and groom.** The supervisor may file, label,
split and groom issues from research returns, bugs and gaps found while
coding, without waiting for chat approval. Search open and closed issues
first to avoid duplicates. Do not invent scope that contradicts an issue's
stated non-goals. Standing permission to file and groom issues is not
permission to bypass the required chain.

- **Parent** (`size-L`): the goal and the combined done-when. Never one
  builder dispatch; split before assigning.
- **Child** (`size-S` or `size-M`): one behaviour or one research deliverable
  with mechanical acceptance.
- **Labels:** `judgment` or `pi-fit`; one size label; `P1` to `P4`; `ready`
  once an accepted definition of ready and done sits in an issue comment.
- **Accepted contract:** a titled issue comment. The brief links that comment
  URL and pastes its text. Chat summaries are not the contract.

## Bounded execution

The supervisor owns the cost of the whole assignment, including workers and
repeated context. Explicit user scope and required gates still govern.

- **Define done first.** State the decision, necessary evidence, allowed
  repairs and stopping condition on the existing issue. Keep it under 150
  words. Link existing specifications instead of rewriting them.
- **Require a reason for each action.** Advance the decision, repair a
  demonstrated blocker, or satisfy a required gate. Skip other actions.
- **Bound delegation.** Default to one implementation dispatch, one
  independent acceptance review and one repair dispatch per behaviour. Before
  exceeding these limits, report the unresolved assertion and why another
  dispatch could resolve it. Do not retry an unavailable worker. Continue
  directly when the contract authorizes it, or report the outage. Do not turn
  a worker outage or harness failure into another project.
- **Red before green.** A behavioural dispatch proves the acceptance test
  fails for the missing behaviour before production edits. The return
  preserves both outputs.
- **Use one validation path.** The gate table and the hooks are that path. Do
  not add a second review pipeline. Reuse passing checks for unchanged
  revisions.
- **Keep delivery small.** Use the existing issue and one pull request. Create
  no extra report or dashboard unless the deliverable requires it.
- **Stop at the agreed outcome.** Report the result and remaining evidence
  gaps. Report unavailable usage counters as unknown.

## Gates

| gate | command |
|---|---|
| lint | `uv run ruff check .` |
| format | `uv run ruff format --check .` |
| types | `uv run ty check src tests` |
| layers | `uv run lint-imports` |
| docs | `uv run docvet check --all` |
| tests | `uv run pytest -q` |
| coverage | `uv run pytest --cov=src -q` (floor in `pyproject.toml`) |
| dependencies | `uv audit --locked` |
| module size | `uv run python scripts/check_loc.py src` |
| suppressions | `uv run python scripts/check_suppressions.py` |
| commit message | `uv run python scripts/check_commit_msg.py --range main..HEAD` |

The default test run excludes the `api` tier. `uv run pytest -m api` makes
real LLM calls. Run it only when the brief authorizes it.

### Gates run themselves

A `PostToolUse` hook in `.claude/settings.json` runs `scripts/vet_file.sh`
after every `Write`, `Edit` or `Bash` call. It runs ruff format, ruff check and
docvet on each changed Python file and returns their findings as context. A
clean file returns nothing. Read what the hook reports instead of re-running
those three by hand. The hook does not run `ty`, `lint-imports`, `pytest`,
`uv audit` or the coverage floor. The pre-commit and pre-push hooks and the
gate table run them.

### A summary is not evidence

Never report work complete while a gate is red. Report what is red and why you
think it should be accepted.

A green gate table is not an audit either. Gates cannot see a test that passes
whether or not the behaviour happens, a helper that raises where the
specification said return, or an unwrapped secret bound to a local that
`--showlocals` prints.

Prove a property with a command, not a sentence. "Confirm that X" is answered
by a claim. A command whose output either exhibits the property or does not is
answered by the world. For a test, the command is: break the precondition and
show it go red. A test that cannot be made to fail is not evidence.

## Worker trailers

`.claude/rules/pull-requests.md` forbids `Co-Authored-By`. That rule stands.
`Generated-By` and `Specified-By` are allowed. They are a different thing.
`Co-Authored-By` claims authorship for Claude. The worker trailers record
which worker model produced the code or the specification, as evidence for
evaluating those workers.

- A Claude sub agent's code carries `Generated-By: <resolved model id> (via
  Claude Code Agent tool, <agent name>)`.
- A Claude sub agent's specification carries `Specified-By: <resolved model id>
  (via Claude Code Agent tool, specifier)`.
- The resolved model ID comes from the agent's return, never from the
  requested alias. If the agent does not report it, record `unknown`.
- The supervisor's own commits carry no worker trailer.
- The supervisor preserves trailers through the API squash recipe in
  `.claude/rules/pull-requests.md`.

## Never destroy work you did not create

A delegated session does not run `git checkout`, `git restore`, `git reset`,
`git stash`, `git clean` or `rm -rf` against any path. It does not modify a
file its task did not name. Unrelated modifications belong to someone else.
Leave them and mention them in the summary. Every gate examines changed files.
Nothing notices a reverted file, because a revert leaves no diff.
<!-- MANUAL ADDITIONS END -->
