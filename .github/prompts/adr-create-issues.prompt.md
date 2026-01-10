````prompt
---
description: Create GitHub issues for ADR violations using gh CLI and project templates
tools: ['runInTerminal']
---

# Create GitHub Issues for ADR Violations

Create GitHub issues for each ADR violation from an audit report using the `gh` CLI and the project's issue templates.

## Available Issue Templates

This project has issue templates in `.github/ISSUE_TEMPLATE/`:

| Template | File | Labels | Use For |
|----------|------|--------|---------|
| Feature Request | `feature_request.yml` | `enhancement` | Clear ADR fixes with known implementation |
| Feature Idea | `feature-idea-parking.yml` | `idea`, `needs-spec` | Complex violations needing design discussion |

## gh CLI Commands

### For implementation-ready fixes (most ADR violations):

```bash
gh issue create \
  --template "feature_request.yml" \
  --title "[ADR-XXX] Fix: <brief description>" \
  --label "enhancement,adr-violation" \
  --body "## User Story
**As a** developer, **I want** code to comply with ADR-XXX (<ADR Title>), **so that** we maintain architectural consistency.

## Acceptance Criteria (Gherkin)
\`\`\`gherkin
Scenario: Code complies with ADR-XXX
  Given the violation in \`<file:line>\`
  When the fix is applied
  Then the code follows the pattern specified in ADR-XXX
\`\`\`

## Technical Implementation Plan
**Tech Stack:**
- Existing project patterns per ADR-XXX

**Files:**
- \`<path/to/file.py>\` (modify)

**Approach:**
<specific remediation steps from audit>

## Priority
Medium - Nice to have

## Estimated Effort
Small (1-2 days)"
```

### For complex violations needing design:

```bash
gh issue create \
  --template "feature-idea-parking.yml" \
  --title "[Idea] ADR-XXX compliance: <description>" \
  --label "idea,needs-spec,adr-violation" \
  --body "## Problem Statement
<describe the architectural drift or violation pattern>

## Desired Outcome
Code in \`<file/directory>\` should comply with ADR-XXX patterns.

## User Stories
**As a** developer, **I want** consistent ADR-XXX compliance, **so that** the codebase remains maintainable.

## High-Level Acceptance Criteria
\`\`\`gherkin
Scenario: ADR-XXX compliance achieved
  Given the current violation pattern
  When refactoring is complete
  Then all code follows ADR-XXX guidelines
\`\`\`"
```

## Instructions

1. **Parse the audit report** from the conversation above (look for the ADR Compliance Audit Report)

2. **Group related violations** - Create one issue per distinct violation type, not per occurrence

3. **Choose the right template**:
   - `feature_request.yml` → Straightforward fixes (most cases)
   - `feature-idea-parking.yml` → Needs architectural discussion

4. **Always add `adr-violation` label** for tracking

5. **Include in each issue**:
   - ADR number in title prefix: `[ADR-XXX]`
   - Specific file:line locations
   - Code snippets showing wrong vs correct patterns
   - Link to the ADR doc

6. **Run the gh commands** to create the issues

## Example Workflow

If the audit found:
- 2 violations of ADR-007 (CLI pattern) in `input_cli.py`
- 1 violation of ADR-001 (Unit of Work) in `service.py`

Create 2 issues (grouped by ADR), not 3:

```bash
# Issue 1: ADR-007 violations
gh issue create --template "feature_request.yml" \
  --title "[ADR-007] Fix CLI pattern violations in input_cli.py" \
  --label "enhancement,adr-violation" \
  --body "..."

# Issue 2: ADR-001 violation  
gh issue create --template "feature_request.yml" \
  --title "[ADR-001] Fix Unit of Work pattern in service.py" \
  --label "enhancement,adr-violation" \
  --body "..."
```

## User Input

```text
$ARGUMENTS
```

If no arguments, look for the most recent ADR audit report in this conversation and create issues for all violations found.

````
