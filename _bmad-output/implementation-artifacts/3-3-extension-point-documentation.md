# Story 3.3: Extension Point Documentation

Status: review
Branch: docs/epic-3-3-extension-point-documentation

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want clear documentation for extending the system,
so that I can add new evolvable surfaces or agent providers without reading internal code.

## Acceptance Criteria

1. **Given** `ComponentHandler` Protocol (FR21) and `AgentProvider` Protocol (FR22) exist with mature contract tests, **When** extension documentation is created, **Then** each extension point has a dedicated guide page with: Protocol definition, step-by-step implementation recipe, registration process, runnable example, and common pitfalls
2. **And** contract test skeletons are provided as a starting point for new implementations
3. **And** the extension points are accessible using only public API imports -- no internal module imports required
4. **And** guide pages are added to MkDocs navigation under `Contributing > Extending` with a minimal index/landing page

## Tasks / Subtasks

- [x] Task 1: Verify and fix public API exports (AC: 3) -- MUST complete before writing guides
  - [x] 1.1 Confirm `ComponentHandler` is importable from `gepa_adk.ports` (check `__all__` in `ports/__init__.py`)
  - [x] 1.2 Confirm `AgentProvider` is importable from `gepa_adk.ports`
  - [x] 1.3 Add `ComponentHandler` and `AgentProvider` to `gepa_adk.__init__.__all__` (re-export from top-level package for import consistency with other public symbols)
  - [x] 1.4 Confirm `ComponentHandlerRegistry` (or `register_handler`/`get_handler`) is accessible from `gepa_adk.adapters`
  - [x] 1.5 Run `uv run pytest` -- verify no regressions from export changes

- [x] Task 2: Create ComponentHandler extension guide (AC: 1, 2, 3)
  - [x] 2.1 Create `docs/contributing/extending-surfaces.md`
  - [x] 2.2 Write "When to Use" section using `!!! tip` admonition -- when a contributor needs a new evolvable surface beyond instruction/output_schema/generate_content_config
  - [x] 2.3 Write Protocol definition section -- show `ComponentHandler` with `serialize()`, `apply()`, `restore()` signatures and explain the contract (no exceptions, graceful degradation)
  - [x] 2.4 Write step-by-step implementation recipe -- create a `TemperatureHandler` example that serializes/applies/restores `generate_content_config.temperature`. Use a plain class (NO Protocol inheritance -- structural subtyping per ADR-002)
  - [x] 2.5 Write registration section -- show `ComponentHandlerRegistry.register()` and how the engine discovers handlers via `get_handler()`
  - [x] 2.6 Write self-contained runnable example -- demonstrates the serialize/apply/restore cycle on an agent object without requiring an LLM API key. Show a separate config snippet for integration with `evolve()`
  - [x] 2.7 Write common pitfalls section using `!!! warning` admonition -- raising exceptions instead of returning defaults, forgetting restore, not handling `None` values, inheriting from Protocol instead of structural subtyping
  - [x] 2.8 Write contract test skeleton -- inline three-class template (RuntimeCheckable, Behavior, NonCompliance) for a custom handler, using only public imports. Add explicit reference: "This skeleton follows the pattern in `tests/contracts/test_component_handler_protocol.py` -- always check the latest exemplar before starting"

- [x] Task 3: Create AgentProvider extension guide (AC: 1, 2, 3)
  - [x] 3.1 Create `docs/contributing/extending-providers.md`
  - [x] 3.2 Write "When to Use" section using `!!! tip` admonition -- when a contributor needs custom agent persistence (database, file system, remote registry)
  - [x] 3.3 Write Protocol definition section -- show `AgentProvider` with `get_agent()`, `save_instruction()`, `list_agents()` signatures and error contracts (KeyError, ValueError, IOError)
  - [x] 3.4 Write step-by-step implementation recipe -- create a `JsonFileAgentProvider` example that reads/writes agent configs from JSON files. Use a plain class (NO Protocol inheritance)
  - [x] 3.5 Write registration/injection section -- show how to pass custom provider to evolution engine
  - [x] 3.6 Write self-contained runnable example -- demonstrates get_agent/save_instruction/list_agents cycle without requiring an LLM API key. Show a separate config snippet for integration with `evolve()`
  - [x] 3.7 Write common pitfalls section using `!!! warning` admonition -- missing validation on empty names, not persisting before returning updated agent, IOError handling, inheriting from Protocol
  - [x] 3.8 Write contract test skeleton -- inline three-class template for a custom provider with explicit exemplar reference to `tests/contracts/test_agent_provider_protocol.py`

- [x] Task 4: Update MkDocs navigation and create index page (AC: 4)
  - [x] 4.1 Create `docs/contributing/extending.md` -- minimal index/landing page (under 30 lines) with: one-paragraph intro to Protocol-based extension model, bullet list of available extension points with one-line descriptions, links to detailed guide pages
  - [x] 4.2 Add "Extending" subsection under Contributing in `mkdocs.yml` nav using `navigation.indexes`:
    ```
    Contributing:
      - Extending:
        - contributing/extending.md
        - Evolvable Surfaces: contributing/extending-surfaces.md
        - Agent Providers: contributing/extending-providers.md
      - Docstring Templates: contributing/docstring-templates.md
      - Releasing: contributing/releasing.md
    ```

- [x] Task 5: Final verification (AC: 1, 2, 3, 4)
  - [x] 5.1 Run `uv run mkdocs build --strict` -- verify docs build with no warnings (2 pre-existing cross-ref warnings in unrelated files; no new warnings from this story)
  - [x] 5.2 Verify all code examples are syntactically valid Python
  - [x] 5.3 Verify all imports in examples use `from gepa_adk import ComponentHandler` (top-level) -- NOT `from gepa_adk.ports import ...`
  - [x] 5.4 Verify contract test skeletons follow three-class template from Story 3.2
  - [x] 5.5 Run `uv run pytest` -- no regressions

- [ ] [TEA] Testing maturity: verify that ComponentHandlerRegistry.register/get_handler have unit tests for edge cases (duplicate registration, unknown handler name) (cross-cutting, optional)

## Dev Notes

### Guide Style and Structure

Follow the pattern established in `docs/guides/stoppers.md` (the exemplar extension guide):
- Start with a `!!! tip` admonition callout for context ("When to Use")
- Use `!!! warning` for common pitfalls sections
- Use `!!! note` for contract details and important behavioral constraints
- "Available X" table for built-in implementations
- "Basic Usage" section with minimal code examples
- All code blocks use `python` syntax highlighting with `from gepa_adk import ...` public imports (top-level, not `gepa_adk.ports`)

### Structural Subtyping (ADR-002) -- Critical for Examples

All implementation examples in guide pages MUST use plain classes with matching method signatures. Do NOT inherit from the Protocol:
- **Correct**: `class TemperatureHandler:` (plain class, structural subtyping)
- **Wrong**: `class TemperatureHandler(ComponentHandler):` (inheritance -- misleads contributors)
ADR-002 mandates structural subtyping. If docs show inheritance, contributors will think it's required.

### Example Runnability (Party Mode Consensus)

Guide examples must be **self-contained** (level 2 runnability):
- Demonstrate the protocol contract (serialize/apply/restore or get_agent/save_instruction/list_agents) without requiring an LLM API key, trainset, or external services
- Show the handler/provider working against a real or minimal agent object
- Provide a **separate config snippet** showing how to integrate with `evolve()` -- but this snippet is illustrative, not runnable standalone
- Do NOT write full evolution-run examples that require API credentials

### Contract Test Skeleton Approach (Party Mode Consensus)

- **Inline** the skeleton directly in the guide page (not via `pymdownx.snippets`)
- **Reference the living exemplar** explicitly: "This skeleton follows the pattern in `tests/contracts/test_component_handler_protocol.py` -- always check the latest exemplar before starting"
- Do NOT add version notes or "last verified" annotations -- the exemplar reference is the safety net

### Extension Points Inventory

**ComponentHandler** (`src/gepa_adk/ports/component_handler.py`):
- Protocol: `serialize(agent) -> str`, `apply(agent, value) -> Any`, `restore(agent, original) -> None`
- Contract: Never raise exceptions -- return empty string or default on failure, log warning
- Built-in handlers: `InstructionHandler`, `OutputSchemaHandler`, `GenerateContentConfigHandler`
- Registry: `ComponentHandlerRegistry` in `adapters/components/component_handlers.py`
  - `register(component_name, handler)`, `get(component_name)`, `list_handlers()`
  - Module-level convenience: `component_handlers` (default registry), `get_handler()`, `register_handler()`

**AgentProvider** (`src/gepa_adk/ports/agent_provider.py`):
- Protocol: `get_agent(name) -> LlmAgent`, `save_instruction(name, instruction) -> None`, `list_agents() -> list[str]`
- Contract: `KeyError` for unknown name, `ValueError` for empty/invalid name, `IOError` for persistence failures
- No built-in implementations shipped (examples use in-memory implementations inline)
- Injected via constructor/config, not via registry

### Contract Test Skeleton Template

Use three-class template established in Story 3.2 as exemplar:
```
TestXxxProtocolRuntimeCheckable  -- isinstance checks
TestXxxProtocolBehavior          -- return types, state transitions, error contracts
TestXxxProtocolNonCompliance     -- missing methods -> not isinstance
```
- Mark with `pytestmark = pytest.mark.contract`
- Import Protocol from `gepa_adk.ports` (public path)
- Reference exemplars: `tests/contracts/test_component_handler_protocol.py`, `tests/contracts/test_agent_provider_protocol.py`

### Hexagonal Architecture Compliance (ADR-000)

- Guide examples must NOT import from `gepa_adk.adapters.*` internal modules for Protocol definitions
- Protocol imports: `from gepa_adk import ComponentHandler, AgentProvider` (top-level re-export -- Task 1 ensures these are added)
- Built-in adapter imports (for reference only): `from gepa_adk.adapters.components import ...`
- New contributor implementations go in their own project, not in gepa-adk's adapters/

### Previous Story Learnings (from 3-1 and 3-2)

**Story 3.1 (Critic Preset Factory):**
- `create_critic()` factory pattern used for MVP -- simple dict-based preset registry
- All presets use `CriticOutput` schema (not `SimpleCriticOutput`) to maximize ASI quality
- Public API exports via `gepa_adk.__init__` -- follow same pattern for any new exports

**Story 3.2 (Contract Test Gaps):**
- Three-class template is the established standard for protocol contract tests
- 453 contract tests across 12 protocols -- all green
- `scripts/check_protocol_coverage.py` enforces Protocol-to-test mapping in CI
- Non-compliance tests verify `@runtime_checkable` limitation: only checks method existence, not signatures

### Git Intelligence (from recent commits)

- `ac59411` (Story 3-1): Added `create_critic()` factory, 3 presets, 7 unit tests, public API exports
- `30d7deb` (Story 3-2): Upgraded 3 contract test files to three-class template, added non-compliance to 3 more, 36 files touched, docstrings enriched with See Also and Examples sections
- Story 3-2 enriched port docstrings with `Examples:` sections showing compliance verification -- these are good starting material for guide content

### Documentation Impact

This IS the documentation story. Impact:
- **New files**: `docs/contributing/extending.md` (index), `docs/contributing/extending-surfaces.md`, `docs/contributing/extending-providers.md`
- **Modified files**: `mkdocs.yml` (nav update), `src/gepa_adk/__init__.py` (`__all__` exports)
- **No API docs impact**: mkdocstrings auto-generates API reference from docstrings (already enriched in Story 3-2)
- **No ADR impact**: ADR-002 (Protocol Interfaces) already covers the design decisions

### Project Structure Notes

- New docs go in `docs/contributing/` alongside existing `docstring-templates.md` and `releasing.md`
- MkDocs nav uses `Contributing > Extending > [index, surfaces, providers]` with `navigation.indexes`
- `src/gepa_adk/__init__.py` updated to re-export `ComponentHandler` and `AgentProvider` (Task 1)
- No changes to `tests/` -- contract test skeletons are documentation content, not runnable test files

### References

- [Source: src/gepa_adk/ports/component_handler.py -- ComponentHandler Protocol definition]
- [Source: src/gepa_adk/ports/agent_provider.py -- AgentProvider Protocol definition]
- [Source: src/gepa_adk/adapters/components/component_handlers.py -- ComponentHandlerRegistry, built-in handlers]
- [Source: tests/contracts/test_component_handler_protocol.py -- ComponentHandler contract tests exemplar]
- [Source: tests/contracts/test_agent_provider_protocol.py -- AgentProvider contract tests exemplar]
- [Source: docs/guides/stoppers.md -- Guide style exemplar for extension point docs]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3, Story 3.3]
- [Source: _bmad-output/planning-artifacts/architecture.md -- Pattern 1: New Adapter Implementation Recipe]
- [Source: _bmad-output/implementation-artifacts/3-1-implement-critic-preset-factory.md -- Previous story learnings]
- [Source: _bmad-output/implementation-artifacts/3-2-fill-contract-test-gaps.md -- Previous story learnings]
- [Source: mkdocs.yml -- Current nav structure for placement]

## AC-to-Test Mapping

| AC | Verification | Status |
|----|-------------|--------|
| AC1 (dedicated guide pages) | Manual: `docs/contributing/extending-surfaces.md` and `extending-providers.md` contain Protocol definition, implementation recipe, registration, runnable example, common pitfalls | PASS |
| AC2 (contract test skeletons) | Manual: Both guides contain inline three-class template skeletons (RuntimeCheckable, Behavior, NonCompliance) with exemplar references | PASS |
| AC3 (public API imports only) | `grep -r "from gepa_adk.ports import" docs/contributing/` returns 0 matches; all examples use `from gepa_adk import ComponentHandler/AgentProvider` | PASS |
| AC4 (MkDocs navigation) | `uv run mkdocs build` succeeds; nav includes `Contributing > Extending > [index, surfaces, providers]` | PASS |

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- mkdocs build --strict: 2 pre-existing cross-ref warnings (`structlog.dev.ConsoleRenderer` in encoding.py, `gepa_adk.engine.reflection` in state_guard.py) — not introduced by this story
- git-revision-date-localized warnings for new files are expected and resolve after commit

### Completion Notes List

- Task 1: Verified `ComponentHandler` and `AgentProvider` already exported from `gepa_adk.ports`. Added both to `gepa_adk.__init__.__all__` for top-level import. Confirmed `ComponentHandlerRegistry`, `get_handler`, `register_handler` accessible from `gepa_adk.adapters`. All 2124 tests pass.
- Task 2: Created `docs/contributing/extending-surfaces.md` with all required sections: tip admonition, protocol definition with contract notes, TemperatureHandler step-by-step recipe (plain class, structural subtyping), registration via ComponentHandlerRegistry, self-contained runnable example, evolve() integration snippet, warning admonition for pitfalls, inline three-class contract test skeleton with exemplar reference.
- Task 3: Created `docs/contributing/extending-providers.md` with all required sections: tip admonition, protocol definition with error contracts, JsonFileAgentProvider recipe (plain class), injection section, self-contained runnable example with tempfile, evolve() integration snippet, warning admonition for pitfalls, inline three-class contract test skeleton with exemplar reference.
- Task 4: Created `docs/contributing/extending.md` index page (11 lines). Updated `mkdocs.yml` nav with `Contributing > Extending` subsection using `navigation.indexes`.
- Task 5: Docs build succeeds (no new warnings). All 10 Python code blocks are syntactically valid. All imports use top-level `from gepa_adk import ...`. Contract test skeletons follow three-class template. 2124 tests pass.

### File List

- `src/gepa_adk/__init__.py` (modified) — added `AgentProvider` and `ComponentHandler` to imports and `__all__`
- `docs/contributing/extending.md` (new) — index/landing page for extension points
- `docs/contributing/extending-surfaces.md` (new) — ComponentHandler extension guide
- `docs/contributing/extending-providers.md` (new) — AgentProvider extension guide
- `mkdocs.yml` (modified) — added Extending subsection to Contributing nav

## Change Log

- 2026-03-08: Implemented Story 3.3 — created extension point documentation for ComponentHandler and AgentProvider protocols, added public API re-exports, updated MkDocs navigation

