# Tasks: MkDocs Glossary Integration

**Input**: Design documents from `/specs/036-glossary-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: No automated tests required - this is a documentation infrastructure feature. Verification via `mkdocs build` and manual inspection.

**Documentation**: This IS a documentation feature - all tasks are documentation-related.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Documentation infrastructure**: `mkdocs.yml`, `pyproject.toml`, `docs/` at repository root
- No source code (`src/`) or test (`tests/`) changes required

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies and configure plugin infrastructure

- [ ] T001 Add mkdocs-ezglossary-plugin>=2.1.0 to dev dependencies in pyproject.toml
- [ ] T002 Run `uv sync` to install the new dependency
- [ ] T003 Add def_list to markdown_extensions in mkdocs.yml

---

## Phase 2: Foundational (Plugin Configuration)

**Purpose**: Configure ezglossary plugin with all required settings

**⚠️ CRITICAL**: Plugin must be configured before glossary content can be converted

- [ ] T004 Add ezglossary plugin entry to plugins section in mkdocs.yml
- [ ] T005 Configure `strict: true` for section validation in mkdocs.yml
- [ ] T006 Configure `sections:` list with core, trial, evolution, model, abbr in mkdocs.yml

**Checkpoint**: Plugin infrastructure ready - glossary content migration can begin

---

## Phase 3: User Story 1 - Auto-Linked Glossary Terms (Priority: P1) 🎯 MVP

**Goal**: Glossary terms automatically become clickable links when they appear in documentation

**Independent Test**: View any documentation page containing glossary terms (e.g., getting-started.md) and verify terms are automatically converted to clickable links pointing to the glossary

### Implementation for User Story 1

- [ ] T007 [US1] Configure `ignore_case: true` for case-insensitive matching in mkdocs.yml
- [ ] T008 [US1] Convert "Core Concepts" section terms to definition list format in docs/reference/glossary.md
  - Terms: component, component_text, evolved_component_text, evolved_components
  - Format: `core:term_name` followed by `:   Definition text`
- [ ] T009 [US1] Convert "Trial Data Structures" section terms to definition list format in docs/reference/glossary.md
  - Terms: trial, trials, feedback, trajectory
  - Format: `trial:term_name` followed by `:   Definition text`
- [ ] T010 [US1] Convert "Evolution Process" section terms to definition list format in docs/reference/glossary.md
  - Terms: evolution, mutation, merge, reflection, proposed_component_text
  - Format: `evolution:term_name` followed by `:   Definition text`
- [ ] T011 [US1] Convert "Data Model Types" section terms to definition list format in docs/reference/glossary.md
  - Terms: Candidate, IterationRecord, EvolutionResult, MultiAgentEvolutionResult
  - Format: `model:term_name` followed by `:   Definition text`
- [ ] T012 [US1] Convert "Abbreviations" section terms to definition list format in docs/reference/glossary.md
  - Terms: ADK, GEPA, LLM
  - Format: `abbr:term_name` followed by `:   Definition text`
- [ ] T013 [US1] Verify `uv run mkdocs build` succeeds without glossary-related warnings
- [ ] T014 [US1] Verify auto-linking works by running `uv run mkdocs serve` and checking a doc page

**Checkpoint**: User Story 1 complete - glossary terms are auto-linked across all documentation pages

---

## Phase 4: User Story 2 - Tooltip Definitions on Hover (Priority: P2)

**Goal**: Hovering over linked glossary terms displays their definition in a tooltip

**Independent Test**: Hover over any auto-linked term and verify the tooltip displays the correct definition text

### Implementation for User Story 2

- [ ] T015 [US2] Configure `tooltip: short` for hover definitions in mkdocs.yml
- [ ] T016 [US2] Verify tooltips appear by running `uv run mkdocs serve` and hovering over linked terms

**Checkpoint**: User Story 2 complete - tooltips display definitions on hover

---

## Phase 5: User Story 3 - Centralized Glossary Summary Page (Priority: P3)

**Goal**: A dedicated glossary page displays all terms organized by section

**Independent Test**: Navigate to the Glossary page and verify all five sections display their terms with definitions

### Implementation for User Story 3

- [ ] T017 [US3] Configure `inline_refs: short` for backlinks to term usage in mkdocs.yml
- [ ] T018 [US3] Replace manual term listings with `<glossary::core>` summary directive in docs/reference/glossary.md
- [ ] T019 [US3] Add `<glossary::trial>` summary directive for Trial section in docs/reference/glossary.md
- [ ] T020 [US3] Add `<glossary::evolution>` summary directive for Evolution section in docs/reference/glossary.md
- [ ] T021 [US3] Add `<glossary::model>` summary directive for Model section in docs/reference/glossary.md
- [ ] T022 [US3] Add `<glossary::abbr>` summary directive for Abbreviations section in docs/reference/glossary.md
- [ ] T023 [US3] Verify glossary summary page renders correctly with `uv run mkdocs serve`

**Checkpoint**: User Story 3 complete - glossary page shows all terms organized by section

---

## Phase 6: User Story 4 - Plural and Variant Form Support (Priority: P4)

**Goal**: Plural forms of terms (e.g., "components") automatically link to singular definitions

**Independent Test**: In any doc page, write plural forms like "components", "trials", "mutations" and verify they link to their singular definitions

### Implementation for User Story 4

- [ ] T024 [US4] Configure `plurals: en` for English plural recognition in mkdocs.yml
- [ ] T025 [US4] Verify plural linking by running `uv run mkdocs serve` and checking pluralized terms link correctly

**Checkpoint**: User Story 4 complete - plural forms auto-link to singular definitions

---

## Phase 7: Verification & Final Polish

**Purpose**: Final verification and cleanup

### Documentation Build Verification (REQUIRED)

- [ ] T026 Verify `uv run mkdocs build` passes without any warnings
- [ ] T027 Preview docs with `uv run mkdocs serve` and verify all glossary features work
- [ ] T028 Verify terms in code blocks are NOT auto-linked (preserve code readability)
- [ ] T029 Verify case-insensitive matching works (both "Component" and "component" link correctly)
- [ ] T030 Remove any deprecated/commented content from docs/reference/glossary.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - plugin must be installed first
- **User Story 1 (Phase 3)**: Depends on Foundational - plugin config must exist before content migration
- **User Story 2 (Phase 4)**: Depends on US1 - needs linked terms to show tooltips
- **User Story 3 (Phase 5)**: Depends on US1 - needs term definitions for summary directives
- **User Story 4 (Phase 6)**: Depends on US1 - needs base terms to recognize plurals
- **Verification (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```text
Setup (Phase 1)
    ↓
Foundational (Phase 2)
    ↓
User Story 1 - Auto-Linking (Phase 3) 🎯 MVP
    ↓
    ├── User Story 2 - Tooltips (Phase 4)
    ├── User Story 3 - Summary Page (Phase 5)
    └── User Story 4 - Plurals (Phase 6)
           ↓
    Verification (Phase 7)
```

### Parallel Opportunities

**Within Phase 3 (US1 - Content Migration)**:
```text
# These can run in parallel - different sections of the same file:
T008 [US1] Convert Core Concepts terms
T009 [US1] Convert Trial terms
T010 [US1] Convert Evolution terms
T011 [US1] Convert Model terms
T012 [US1] Convert Abbreviations terms
```

**After US1 completes, US2/US3/US4 are nearly parallel**:
- US2 and US4 only require mkdocs.yml changes (different config keys)
- US3 requires both mkdocs.yml and glossary.md changes

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T006)
3. Complete Phase 3: User Story 1 (T007-T014)
4. **STOP and VALIDATE**: Test auto-linking independently
5. Deploy/demo if ready - core value delivered!

### Incremental Delivery

1. Setup + Foundational → Plugin infrastructure ready
2. User Story 1 → Auto-linking works → **MVP deployed!**
3. User Story 2 → Tooltips appear → Enhanced UX
4. User Story 3 → Summary page → Reference hub complete
5. User Story 4 → Plurals work → Polish complete
6. Each story adds value without breaking previous functionality

### Recommended Execution

Since this is a documentation-only feature with file dependencies:

1. **Single developer, sequential**: Execute tasks T001-T030 in order
2. **Content migration parallelization**: Tasks T008-T012 can be done in parallel (different sections of glossary.md)
3. **Configuration tasks**: T015, T017, T024 modify different keys in mkdocs.yml and can be batched

---

## Notes

- All tasks modify only 3 files: `pyproject.toml`, `mkdocs.yml`, `docs/reference/glossary.md`
- No source code (`src/`) changes required
- No automated tests required - manual verification via `mkdocs serve`
- Constitution Section VI applies - this IS the documentation update
- Verification depends on visual inspection in local docs preview
- Commit after each phase or logical group of tasks
- Run `uv run mkdocs build` before PR to verify clean build
