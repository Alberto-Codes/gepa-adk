# gepa-adk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-10

## Start here

For issue-driven work, read the accepted issue comment and its dependency pointers,
then [the delegation procedure](docs/contributing/delegate-work.md) and
[PR rules](.claude/rules/pull-requests.md). The issue/PR is authoritative;
optional story artifacts apply only when that workflow is selected. Local memory
is an index to those records, not a competing task contract.

Current policy follows. The generated technology inventory is retained below as
historical context; feature specifications remain in their existing locations.

<!-- MANUAL ADDITIONS START -->

## Model Identifiers

Docs, examples, and docstrings default to local open-source models (`ollama_chat/...`)
rather than hosted ones, so published examples cannot be retired by a vendor.
`docs/reference/model-selection.md` is authoritative: it names the two standard models,
the surfaces that must still use a Gemini string and why, and the update procedure when
Google announces a retirement. `tests/fixtures/models.py` holds the single model the
`requires_gemini` tier uses plus the deprecation rule the guard tests read.

## Supervised workers

Roles describe responsibility, not model brands. Record the actual supervisor,
worker and harness for each dispatch.

gepa-adk has three worker harnesses: pi, through the `delegate-to-pi` skill;
Claude Code sub agents, through the Agent tool and the definitions in
`.claude/agents/`; and the Cursor CLI in print mode, guarded by
`.cursor/cli.json`.

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
  dispatch could resolve it.
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
| dependencies | `uv run uv-secure` |

The default test run excludes the `api` tier. `uv run pytest -m api` makes
real LLM calls. Run it only when the brief authorizes it.

### Gates run themselves

A `PostToolUse` hook in `.claude/settings.json` runs `scripts/vet_file.sh`
after every `Write`, `Edit` or `Bash` call. It runs ruff format, ruff check and
docvet on each changed Python file and returns their findings as context. A
clean file returns nothing. Read what the hook reports instead of re-running
those three by hand. The hook does not run `ty`, `lint-imports`, `pytest`,
`uv-secure` or the coverage floor. The pre-commit and pre-push hooks and the
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

<details>
<summary>Historical generated technology inventory (2026-01-10)</summary>

## Active Technologies
- N/A (protocol definition only) (005-scorer-protocol)
- Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (010-adk-reflection-agent)
- N/A (in-memory session state via ADK's InMemorySessionService) (010-adk-reflection-agent)
- Python 3.12 + `re` (stdlib only - no new dependencies) (015-state-guard-tokens)
- N/A (string manipulation utility) (015-state-guard-tokens)
- Python 3.12 + google-adk 1.22.0 (SequentialAgent, LoopAgent, ParallelAgent, LlmAgent, BaseAgent) (017-workflow-evolution)
- N/A (in-memory evolution) (017-workflow-evolution)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0, dataclasses (stdlib) (019-critic-metadata-passthrough)
- N/A (in-memory data flow) (019-critic-metadata-passthrough)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0 (existing); no new dependencies (022-pareto-frontier)
- N/A (in-memory evolution state) (022-pareto-frontier)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0 (existing - no new deps) (024-component-selector)
- N/A (in-memory evolution state via ParetoState) (028-merge-proposer)
- Python 3.12 + google-adk>=1.22.0, structlog>=25.5.0, typing (stdlib) (029-agent-provider-protocol)
- N/A (protocol definition only - implementations choose storage) (029-agent-provider-protocol)
- Python 3.12 + google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (existing - no new deps) (031-wire-reflection-model)
- N/A (in-memory configuration passthrough) (031-wire-reflection-model)
- N/A (in-memory event processing) (033-event-output-extraction)
- Python 3.12 + google-adk >= 1.22.0, litellm >= 1.80.13, structlog >= 25.5.0 (034-adk-ollama-reflection)
- Python 3.12 (MkDocs plugin ecosystem) + mkdocs-ezglossary-plugin>=2.1.0, Material for MkDocs (existing) (036-glossary-integration)
- N/A (static site generation) (036-glossary-integration)
- Python 3.12 + structlog>=25.5.0 (existing), stdlib `sys` and `codecs` (001-cross-platform-encoding)
- N/A (logging infrastructure only) (001-cross-platform-encoding)
- Python 3.12 + google-adk >= 1.22.0 (Runner, Session, Event), structlog >= 25.5.0 (124-unified-agent-executor)
- Python 3.12 + google-adk >= 1.22.0, dataclasses (stdlib) (126-evolved-components)
- N/A (in-memory domain models) (126-evolved-components)
- Python 3.12 + google-adk >= 1.22.0, structlog >= 25.5.0 (existing - no new deps) (141-critic-feedback-schema)
- N/A (in-memory normalization) (141-critic-feedback-schema)
- Python 3.12 + google-adk >= 1.22.0, pydantic >= 2.0, structlog >= 25.5.0 (142-component-aware-reflection)
- N/A (in-memory registry) (162-component-handlers)
- N/A (in-memory component handling) (163-component-handler-migration)
- Python 3.12 + google-adk >= 1.22.0 (GenerateContentConfig from google.genai.types), PyYAML (stdlib yaml), structlog >= 25.5.0 (164-config-evolution)
- N/A (in-memory candidate/component state) (166-multi-agent-routing)
- Python 3.12 + structlog>=25.5.0 (existing - no new deps), pathlib (stdlib) (197-optional-stoppers)
- N/A (in-memory stopper state) (197-optional-stoppers)
- N/A (in-memory validation during evolution) (198-schema-field-preservation)
- Python 3.12 + google-adk >= 1.22.0 (SequentialAgent, LoopAgent, ParallelAgent, LlmAgent) (215-workflow-structure)
- N/A (in-memory workflow cloning) (215-workflow-structure)
- N/A (uses user-provided services or InMemorySessionService default) (227-app-runner-pattern)
- Python 3.12 + google-adk >= 1.22.0 (Part, Content types), structlog >= 25.5.0, pathlib (stdlib), mimetypes (stdlib) (235-multimodal-input)
- N/A (local filesystem video files, no persistent storage) (235-multimodal-input)

- Python 3.12 + None (stdlib only for ports layer per ADR-000) (004-async-gepa-adapter)

## Project Structure

```text
src/
tests/
```

## Commands

```bash
uv run pytest                 # run test suite (API tests excluded by default)
uv run pytest -m api          # run API-tier tests (real LLM calls)
uv run ruff check .           # lint
uv run ruff format --check .  # format check
uv run ty check src tests     # type check
uv run lint-imports           # architecture boundary check
```

## Code Style

Python 3.12: Follow standard conventions

## Recent Changes
- 235-multimodal-input: Added Python 3.12 + google-adk >= 1.22.0 (Part, Content types), structlog >= 25.5.0, pathlib (stdlib), mimetypes (stdlib)
- 227-app-runner-pattern: Added Python 3.12 + google-adk >= 1.22.0, structlog >= 25.5.0
- 215-workflow-structure: Added Python 3.12 + google-adk >= 1.22.0 (SequentialAgent, LoopAgent, ParallelAgent, LlmAgent)



</details>
