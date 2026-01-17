# Project Management Workflow

This document describes the GitHub-native project management approach for gepa-adk, using labels, native issue dependencies, and GitHub Projects views.

## Philosophy

- **Labels as metadata** - Priority and track labels drive all views
- **Native dependencies** - Use GitHub's `blocked by` relationships, not labels
- **Views as filters** - Project views slice existing data, no manual board management
- **Release-driven** - Work high priorities until empty, then release and re-prioritize
- **Zero ceremony** - No sprints, no timeboxes, just continuous flow

## Label Schema

### Priority Labels (Required for "Groomed" Status)

| Label | Description | View |
|-------|-------------|------|
| `priority:high` | Must be done before next release | High Priority |
| `priority:medium` | Important, next after highs | Medium Priority |
| `priority:low` | Someday/maybe, icebox | Icebox |

**No priority label = Ungroomed** - Appears in Needs Grooming view

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
| **Ungroomed** | No `priority:*` label |
| **Ready** | Has `priority:*` + not assigned + not blocked |
| **In Progress** | Assigned to someone |
| **Blocked** | Has GitHub dependency (use `is:blocked` filter) |
| **Done** | Issue closed |

## GitHub Project Views

| View | Filter | Purpose |
|------|--------|---------|
| **High Priority** | `is:open label:priority:high -is:blocked` | Actionable work for next release |
| **Blocked** | `is:open is:blocked` | Waiting on dependencies |
| **Medium Priority** | `is:open label:priority:medium -is:blocked` | Ready to pull when highs done |
| **Needs Grooming** | `is:open -label:priority:high -label:priority:medium -label:priority:low` | Untriaged issues |
| **Icebox** | `is:open label:priority:low` | Low priority / future |
| **Done** | `is:closed` | Completed work |

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
   - Add priority label (high/medium/low)
   - Add track labels (core, adk, etc.)
   - Add dependencies if blocked by other issues
   - Issue automatically moves to appropriate view

### Release Cycle

1. Work until **High Priority** is empty (except epics)
2. Release
3. Re-evaluate **Medium Priority**:
   - Promote important items to `priority:high`
   - Demote less important to `priority:low`
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
- Priority label mapping from template dropdowns
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
- **High Priority empty** - Time for release or re-prioritize
- **Blocked growing** - Check if blockers are being worked

## References

- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [Creating Issue Dependencies](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies)
