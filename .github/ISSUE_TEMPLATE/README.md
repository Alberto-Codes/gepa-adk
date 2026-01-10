# GitHub Issue Templates Guide

This directory contains issue templates for the Agent Workflow Suite project.

## Available Templates

| # | Template | Use When | Labels |
|---|----------|----------|--------|
| 1 | **Bug Report** | Something isn't working correctly | `bug` |
| 2 | **Tech Debt / Maintenance** | ADR violations, cleanup, refactoring, test gaps | `tech-debt` |
| 3 | **Feature Idea (Spec-Kit)** | Parking ideas for spec-kit workflow | `idea`, `needs-spec` |
| 4 | **Feature Request** | Full features with implementation details | `enhancement` |

---

### 1. Bug Report - `01-bug-report.yml`

**Purpose**: Report bugs, crashes, or unexpected behavior

**When to use**:
- Something that used to work is now broken
- Unexpected errors or crashes
- Behavior differs from documentation

**What it captures**:
- Bug description and reproduction steps
- Expected vs actual behavior
- Environment details (OS, Python version)
- Severity and frequency
- Relevant logs/screenshots

**What happens next**:
1. Issue created with `bug` label
2. Team triages based on severity
3. Fix implemented and PR created

---

### 2. Tech Debt / Maintenance - `02-tech-debt.yml`

**Purpose**: Track technical debt, ADR violations, and maintenance work

**When to use**:
- Code violates an ADR (Architecture Decision Record)
- Legacy/dead code needs removal
- Missing test coverage
- Code quality issues (duplication, complexity)
- Outdated dependencies
- Performance bottlenecks

**What it captures**:
- Type of debt (ADR violation, legacy code, test coverage, etc.)
- Location (files, line numbers)
- Impact assessment
- Proposed solutions
- Priority and effort estimates

**What happens next**:
1. Issue created with `tech-debt` label
2. May also get `adr-violation` label if applicable
3. Addressed during maintenance sprints or alongside related work

**Example**: See issue #220 (AgentConverter ADR violation)

---

### 3. Feature Idea (Spec-Kit Ready) - `03-feature-idea.yml`

**Purpose**: Park feature ideas for later spec-kit workflow processing

**When to use**:
- You have a feature idea but haven't worked out implementation details yet
- You want to capture user needs and business value before diving into code
- You plan to use the spec-kit workflow (`/speckit.specify`, `/speckit.plan`, `/speckit.tasks`)

**What it captures**:
- Problem statement (what pain point does this solve?)
- Desired outcome (what should be possible?)
- User stories (who benefits and why?)
- High-level acceptance criteria (key scenarios)
- Scope boundaries (what's in/out for MVP)
- Success metrics (how do we measure success?)
- Business value and urgency

**What happens next**:
1. Issue created with `idea`, `needs-spec` labels
2. Team reviews for clarity and feasibility
3. When ready: Run `/speckit.specify` using this issue as input
4. Spec-kit generates full `spec.md` with detailed requirements
5. Continue with spec-kit workflow: plan → tasks → implement

**Example**: See issue #113 (Task Context Loading with Sauce Demo)

---

### 4. Feature Request - `04-feature-request.yml`

**Purpose**: Full-featured request with implementation details

**When to use**:
- You know exactly what needs to be built AND how to build it
- You have technical implementation details ready
- You want to track development tasks in the issue itself
- You're NOT using the spec-kit workflow

**What it captures**:
- User stories
- Acceptance criteria (Gherkin)
- Technical implementation plan (tech stack, files, approach)
- Priority and effort estimation
- Development checklist
- Developer task list (checkboxes to track progress)
- Additional context

**What happens next**:
1. Issue created with `enhancement` label
2. Developer picks up issue and implements directly
3. Tasks tracked via checkboxes in the issue
4. PR created referencing the issue

---

## Which Template Should I Use?

```
What kind of issue are you reporting?
│
├─ Something is broken ────────────────→ Bug Report
│
├─ Code quality / cleanup needed ──────→ Tech Debt / Maintenance
│   (ADR violations, dead code,
│    missing tests, refactoring)
│
└─ New feature or improvement
   │
   ├─ Do you have implementation
   │  details figured out?
   │  │
   │  ├─ No ──────────────────────────→ Feature Idea (Spec-Kit)
   │  │   (Will use spec-kit workflow)
   │  │
   │  └─ Yes ─────────────────────────→ Feature Request
   │      (Skip spec-kit, implement directly)
```

## Template Comparison

| Aspect | Bug Report | Tech Debt | Feature Idea | Feature Request |
|--------|------------|-----------|--------------|-----------------|
| **Focus** | What's broken | What needs cleanup | What & Why | What & How |
| **Detail** | Reproduction steps | Impact & location | High-level | Implementation-ready |
| **Labels** | `bug` | `tech-debt` | `idea`, `needs-spec` | `enhancement` |
| **Next Step** | Fix it | Plan cleanup | `/speckit.specify` | Start coding |

## Spec-Kit Workflow Integration

The **Feature Idea (Spec-Kit Ready)** template is designed to integrate with the spec-kit workflow:

```
1. Feature Idea Issue (template)
   ↓
2. /speckit.specify
   → Generates specs/###-feature-name/spec.md
   ↓
3. /speckit.plan
   → Generates specs/###-feature-name/plan.md
   ↓
4. /speckit.tasks
   → Generates specs/###-feature-name/tasks.md
   ↓
5. /speckit.implement
   → Executes implementation tasks
```

---

## Tips for Writing Good Issues

### Bug Reports
- **Be specific**: "Crashes when processing agents with empty adk_config" > "It crashes"
- **Include reproduction steps**: Numbered steps that anyone can follow
- **Attach error logs**: Use code blocks for stack traces
- **Note environment**: OS, Python version, package version

### Tech Debt
- **Identify location**: File paths and line numbers
- **Explain impact**: Why this matters, what could go wrong
- **Suggest solutions**: At least one approach to fix it
- **Reference ADRs**: Link the violated ADR if applicable

### Feature Ideas
- **Focus on the problem**: What pain point does this solve?
- **Paint success**: What should users be able to do?
- **Use user stories**: As a [role], I want [feature], so that [benefit]
- **Define scope**: What's in vs out for MVP

---

## Questions?

- See [docs/PROJECT_ROADMAP.md](../../docs/PROJECT_ROADMAP.md) for spec-kit workflow details
- See [docs/PROJECT_ARCHITECTURE.md](../../docs/PROJECT_ARCHITECTURE.md) for technical patterns
- See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines

---

**Last Updated**: December 14, 2025
