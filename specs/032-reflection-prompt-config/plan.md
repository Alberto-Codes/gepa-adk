# Implementation Plan: Reflection Prompt Configuration

**Branch**: `032-reflection-prompt-config` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/032-reflection-prompt-config/spec.md`

## Summary

Add `reflection_prompt` field to `EvolutionConfig` to allow users to customize the reflection/mutation prompt template. The existing `prompt_template` parameter in `AsyncReflectiveMutationProposer` already supports custom templates; this feature wires that capability through the config → API → adapter chain and adds validation + documentation.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: google-adk>=1.22.0, litellm>=1.80.13, structlog>=25.5.0 (existing - no new deps)
**Storage**: N/A (in-memory configuration passthrough)
**Testing**: pytest with three-layer strategy (contract, unit, integration)
**Target Platform**: Linux/macOS/Windows (Python library)
**Project Type**: Single Python package
**Performance Goals**: N/A (configuration only, no runtime performance impact)
**Constraints**: Must maintain backward compatibility (reflection_prompt is optional)
**Scale/Scope**: Affects EvolutionConfig users, ~4 files to modify + 1 new docs file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Hexagonal Architecture | ✅ PASS | Config changes in domain/models.py (pure Python). Wiring through api.py, adapters/. No new external imports. |
| II. Async-First Design | ✅ PASS | Config passthrough only, no I/O operations added. |
| III. Protocol-Based Interfaces | ✅ PASS | No new protocols needed; existing ProposerProtocol unchanged. |
| IV. Three-Layer Testing | ✅ REQUIRED | Unit tests for config validation, integration test for end-to-end prompt usage. |
| V. Observability & Code Documentation | ✅ REQUIRED | Docstrings for new field, structured logging for validation warnings. |
| VI. Documentation Synchronization | ✅ REQUIRED | New guide at docs/guides/reflection-prompts.md, update getting-started.md. |

**Gate Status**: PASS - All principles satisfied or addressed in implementation plan.

## Project Structure

### Documentation (this feature)

```text
specs/032-reflection-prompt-config/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (config field schema)
├── quickstart.md        # Phase 1 output (usage examples)
└── contracts/           # N/A - no API contracts for config-only feature
```

### Source Code (repository root)

```text
src/gepa_adk/
├── domain/
│   └── models.py           # ADD: reflection_prompt field to EvolutionConfig
├── api.py                  # MODIFY: Pass reflection_prompt to adapters
├── adapters/
│   ├── adk_adapter.py      # MODIFY: Accept and pass reflection_prompt
│   └── multi_agent.py      # MODIFY: Accept and pass reflection_prompt
└── engine/
    └── proposer.py         # MODIFY: Export DEFAULT_PROMPT_TEMPLATE in __all__

tests/
├── unit/
│   └── test_config.py      # ADD: Tests for reflection_prompt validation
└── integration/
    └── test_reflection_prompt.py  # ADD: End-to-end custom prompt test

docs/
└── guides/
    └── reflection-prompts.md  # CREATE: Comprehensive prompt guide
```

**Structure Decision**: Single Python package following existing hexagonal architecture. Config changes propagate from domain → api → adapters following established patterns.

## Complexity Tracking

> No constitution violations - table not required.

## Config Wiring Path

```text
EvolutionConfig.reflection_prompt (domain/models.py)
         │
         ▼
api.evolve() extracts resolved_config.reflection_prompt (api.py:~990)
         │
         ▼
ADKAdapter.__init__(reflection_prompt=...) (adapters/adk_adapter.py)
         │
         ▼
AsyncReflectiveMutationProposer(prompt_template=reflection_prompt) (engine/proposer.py)
         │
         ▼
proposer._build_messages() → uses self.prompt_template
```

## Implementation Phases

### Phase 0: Research (Complete)

Research completed via codebase exploration. Key findings:
- `AsyncReflectiveMutationProposer` already supports `prompt_template` parameter
- Validation pattern exists in proposer.py (warns on missing placeholders)
- `EvolutionConfig.__post_init__()` pattern used for validation
- `reflection_model` wiring path exists and can be replicated for `reflection_prompt`

### Phase 1: Design & Implementation

**Files to Modify:**

1. `src/gepa_adk/domain/models.py`
   - Add `reflection_prompt: str | None = None` field
   - Add `__post_init__` validation for placeholder presence (warning)

2. `src/gepa_adk/api.py`
   - Pass `resolved_config.reflection_prompt` to ADKAdapter in `evolve()`
   - Pass `resolved_config.reflection_prompt` to MultiAgentAdapter in `evolve_group()`

3. `src/gepa_adk/adapters/adk_adapter.py`
   - Add `reflection_prompt: str | None = None` parameter to `__init__()`
   - Pass to `AsyncReflectiveMutationProposer(prompt_template=reflection_prompt)`

4. `src/gepa_adk/adapters/multi_agent.py`
   - Add `reflection_prompt: str | None = None` parameter to `__init__()`
   - Pass to `AsyncReflectiveMutationProposer(prompt_template=reflection_prompt)`

5. `src/gepa_adk/engine/proposer.py`
   - Add `DEFAULT_PROMPT_TEMPLATE` to `__all__` for public export

**Files to Create:**

1. `docs/guides/reflection-prompts.md` - Prompt customization guide with:
   - Available placeholders documentation
   - Prompt design guidelines
   - Example prompts for different use cases
   - Model selection guidance

**Tests to Add:**

1. `tests/unit/test_config.py` - Unit tests for validation
   - Test prompt with both placeholders passes
   - Test prompt missing `{current_instruction}` warns
   - Test prompt missing `{feedback_examples}` warns
   - Test empty string treated as None (use default)

2. `tests/integration/test_reflection_prompt.py` - Integration test
   - Test custom prompt is actually used during evolution

**Contract Tests**: N/A for this feature. No new protocols are defined; `EvolutionConfig` is a dataclass (not a protocol), and the existing `ProposerProtocol` contract is unchanged. Unit tests verify the config field behavior.
