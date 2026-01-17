---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
handoffs: 
  - label: Create Tasks
    agent: speckit.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: speckit.checklist
    prompt: Create a checklist for the following domain...
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `.specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Phase 1: Update agent context by running the agent script
   - Re-evaluate Constitution Check post-design
   - Phase 2: Generate architecture.md (conditional - see criteria below)

4. **Stop and report**: Command ends after Phase 2. Report branch, IMPL_PLAN path, and generated artifacts:
   - Phase 0: research.md
   - Phase 1: data-model.md, contracts/, quickstart.md
   - Phase 2: architecture.md (or "skipped: [reason]")

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Agent context update**:
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
   - These scripts detect which AI agent is in use
   - Update the appropriate agent-specific context file
   - Add only new technology from current plan
   - Preserve manual additions between markers

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

### Phase 2: Architecture (Conditional)

**Prerequisites:** `research.md`, `data-model.md` complete

**When to generate architecture.md:**
- Feature touches 3+ layers (domain, api, adapters, engine)
- Feature has external system integrations
- Feature involves complex data flow
- Constitution Check references multiple ADRs

**Skip architecture.md when:**
- Simple config-only changes
- Single-file modifications
- Documentation-only features

1. **Generate architecture.md** using `.specify/templates/architecture-template.md`:
   - Section 1-2: Extract from spec.md (purpose, scope, constraints)
   - Section 3-5: C4 diagrams (Context → Container → Component → Code)
   - Section 6: Code diagram from data-model.md entities
   - Section 7: Hexagonal view showing affected layers from plan.md
   - Section 8: Sequence diagrams for key flows from spec.md scenarios
   - Section 9: ERD from data-model.md
   - Section 10-14: Quality attributes, testing, risks, ADRs from plan.md

2. **Validate diagrams**:
   - Ensure all diagrams follow color scheme in template
   - Include legends on C4 diagrams
   - Verify mermaid syntax at [mermaid.live](https://mermaid.live)

**Output**: architecture.md (or skip with justification)

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
- Architecture is conditional - document why skipped if not generated
