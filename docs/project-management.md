# Project Management Workflow

This document describes the GitHub-native project management approach for gepa-adk, using labels, native issue dependencies, and GitHub Projects views.

## Philosophy

- **Labels as metadata** - Priority, fit, size and track labels drive all views
- **Native dependencies** - Use GitHub's `blocked by` relationships between issues; the `blocked` label is only for blockers that are not issues
- **Views as filters** - Project views slice existing data, no manual board management
- **Release-driven** - Work P1 and P2 until empty, then release and re-prioritize
- **Zero ceremony** - No sprints, no timeboxes, just continuous flow

## Label Schema

### Priority Labels (Required for "Groomed" Status)

Priority measures impact, not urgency. The scale is shared with judgevet.

| Label | Description |
|-------|-------------|
| `P1` | Wrong output, a leaked secret, or a claim the repo cannot support |
| `P2` | An output a session or the maintainer reads and acts on is wrong |
| `P3` | The record, the process, a gate, or a capability |
| `P4` | Drift and nits |

**No `P` label = Ungroomed** - Appears in Needs Grooming view.

The former `priority:high`, `priority:medium` and `priority:low` labels were
retired on 2026-09-25. They remain on closed issues for history and must not
be applied to new ones.

### Fit and Size Labels (Required for "Groomed" Status)

Fit says who does the work. Size says whether it can be dispatched whole.
Both follow the sizing rule in
[Delegate a bounded change](contributing/delegate-work.md#2-size-by-behaviour).

| Label | Description |
|-------|-------------|
| `pi-fit` | Mechanical and machine-checkable: delegate to any worker harness |
| `judgment` | Needs the orchestrating model: design, verdicts, done-ness |
| `size-S` | One file, one gate. A worker run under ~10 min |
| `size-M` | A few files behind one acceptance check. ~10-25 min |
| `size-L` | Too big to delegate whole. Split before assigning |

### Workflow Labels

| Label | Description |
|-------|-------------|
| `needs-triage` | Filed, not yet read by the maintainer |
| `ready` | An accepted definition of ready and done sits in an issue comment |
| `blocked` | Waits on a named commit, key, release or date; the body names it |

`ready` is the definition of ready. An issue earns it when a comment records
the decision, the necessary evidence, the allowed repairs and the stopping
condition, under 150 words, as the repository's bounded-execution rule in
`CLAUDE.md` requires. The `specifier`
agent writes that comment when the brief authorizes posting. A `P` label alone
does not make an issue ready.

`blocked` is a label because GitHub's native `is:blocked` filter only sees
issue-to-issue dependencies. Use both: the label for a dependency on a release,
a credential or a date, and the native relationship for another issue.

### Track Labels (Context/Category)

| Label | Description |
|-------|-------------|
| `core` | Core evolution engine functionality |
| `adk` | Google ADK integration |
| `track:tech-debt` | Code quality / architectural debt |
| `track:docs` | Documentation or examples |
| `track:nice-to-have` | Non-blocking enhancement |
| `track:gepa-alignment` | Parity with upstream GEPA |
| `track:adk-extension` | ADK-specific extension |

### Type Labels (Auto-applied by templates)

| Label | Template |
|-------|----------|
| `bug` | Bug Report |
| `enhancement` | Feature Request |
| `idea`, `needs-spec` | Feature Idea |
| `tech-debt` | Tech Debt |
| `adr-violation` | Tech Debt (ADR type) |

### Status (Inferred, Not Labeled)

| Status | How It's Determined |
|--------|---------------------|
| **Ungroomed** | No `P` label, or `needs-triage` |
| **Triaged** | Has `P`, fit and size labels, no `ready` comment yet |
| **Ready** | Has `ready` + not assigned + not blocked |
| **In Progress** | Assigned to someone |
| **Blocked** | Has `blocked` label or a GitHub dependency (`is:blocked`) |
| **Done** | Issue closed |

## GitHub Project Views

| View | Filter | Purpose |
|------|--------|---------|
| **Ready** | `is:open label:ready -label:blocked -is:blocked no:assignee` | Dispatchable now |
| **P1 / P2** | `is:open label:P1,P2 -label:blocked -is:blocked` | Wrong outputs and wrong records, specify next |
| **Delegable** | `is:open label:pi-fit -label:size-L -label:blocked -is:blocked` | Work a worker harness can take whole |
| **Needs Split** | `is:open label:size-L` | Split before assigning |
| **Blocked** | `is:open label:blocked,is:blocked` | Waiting on a named blocker |
| **Needs Grooming** | `is:open -label:P1 -label:P2 -label:P3 -label:P4` | Untriaged issues |
| **Icebox** | `is:open label:P4` | Drift and nits |
| **Done** | `is:closed` | Completed work |

From the CLI:

```bash
# what is ready to be worked
gh issue list --search "is:open label:ready -label:blocked -is:blocked no:assignee"
# wrong records a worker can fix now
gh issue list --search "is:open label:P2 label:pi-fit -label:blocked -is:blocked"
# what needs splitting (inventory, so blocked issues stay in)
gh issue list -l size-L
```

`-l` alone cannot see GitHub-native dependencies, so every actionable query
goes through `--search` with `-is:blocked`.

### Optional Views

| View | Filter | Purpose |
|------|--------|---------|
| **Bugs** | `is:open label:bug -is:blocked` | All open bugs |
| **Tech Debt** | `is:open label:track:tech-debt` | Cleanup work |
| **Docs** | `is:open label:track:docs` | Documentation tasks |

## Workflow

### Daily Work

1. Look at **High Priority** view
2. Pick an unassigned issue
3. Assign yourself (now "In Progress")
4. Work on it
5. Close when done (moves to "Done")
6. Repeat

### Grooming

1. Open **Needs Grooming** view
2. For each issue:
   - Read and understand
   - Add one `P` label by impact, one fit label and one size label
   - Add track labels (core, adk, etc.)
   - Add `blocked` and name the blocker in the body, or add a GitHub dependency
   - Issue automatically moves to appropriate view
3. To make a triaged issue **Ready**, post the definition of ready and done as
   a comment, then add `ready`

### Release Cycle

1. Work until **P1 / P2** is empty (except epics)
2. Release
3. Re-read the open **P3** issues:
   - Promote any whose impact grew to `P2`
   - Demote any that turned into drift to `P4`
4. Check **Needs Grooming** for anything missed
5. Repeat

## Dependencies

GitHub supports native issue dependencies (GA August 2025).

### Adding a Dependency

**Via UI:**
1. Open the issue that is blocked
2. In right sidebar, find **Relationships**
3. Click "Mark as blocked by"
4. Select the blocking issue(s)

**Via CLI (GraphQL):**
```bash
# Get issue node IDs first
gh api graphql -f query='{
  repository(owner: "Alberto-Codes", name: "gepa-adk") {
    issue(number: ISSUE_NUMBER) { id title }
  }
}'

# Add dependency
gh api graphql -f query='
mutation {
  addBlockedBy(input: {
    issueId: "BLOCKED_ISSUE_NODE_ID"
    blockingIssueId: "BLOCKING_ISSUE_NODE_ID"
  }) { issue { number } }
}'
```

### Filtering Blocked Issues

- `is:blocked` - All blocked issues
- `-is:blocked` - All unblocked issues
- Use `-is:blocked` in High/Medium views to show only actionable work

## Issue Templates

| Template | Use When | Auto Labels |
|----------|----------|-------------|
| **Bug Report** | Something is broken | `bug` |
| **Feature Request** | New capability needed, ready to implement | `enhancement` |
| **Feature Idea** | Parking an idea for later spec-kit workflow | `idea`, `needs-spec` |
| **Tech Debt** | Code cleanup, ADR violations, refactoring | `tech-debt` |

All templates include invisible maintainer/AI guidance comments with:
- Priority, fit and size label guidance
- Track label hints
- Dependency setup instructions via GraphQL

## Maintenance

### Regular Tasks

| Task | Frequency |
|------|-----------|
| Groom new issues | As needed |
| Review blocked issues | Weekly |
| Archive old Done items | Monthly |
| Re-prioritize after release | Per release |

### Health Checks

- **Needs Grooming not empty too long** - Schedule grooming
- **Ready empty while P1 / P2 is not** - Run a specification pass
- **P1 / P2 empty** - Time for release or re-prioritize
- **Blocked growing** - Check if blockers are being worked

## References

- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [Creating Issue Dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies)
