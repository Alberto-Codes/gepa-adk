# Research: Reflection Prompt Configuration

**Feature**: 032-reflection-prompt-config
**Date**: 2026-01-17

## Overview

Research findings for implementing `reflection_prompt` configuration in `EvolutionConfig`.

## Key Findings

### 1. Existing Infrastructure

**Decision**: Wire through existing `prompt_template` parameter in `AsyncReflectiveMutationProposer`
**Rationale**: The proposer already supports custom templates with placeholder validation
**Alternatives Considered**: Creating a new template mechanism - rejected because infrastructure exists

### 2. Validation Approach

**Decision**: Warn on missing placeholders (not error)
**Rationale**: Matches existing validation pattern in proposer.py lines 445-454; allows experimentation
**Alternatives Considered**: Hard error on missing placeholders - rejected to maintain flexibility

### 3. Required Placeholders

**Decision**: Two required placeholders: `{current_instruction}` and `{feedback_examples}`
**Rationale**: These are the runtime values available from the evolution process
**Alternatives Considered**: None - these are the only values available for substitution

### 4. Config Wiring Pattern

**Decision**: Follow `reflection_model` pattern: EvolutionConfig → api.evolve() → Adapter → Proposer
**Rationale**: Consistent with existing patterns; minimal code changes
**Alternatives Considered**: Direct proposer access - rejected to maintain encapsulation

### 5. Empty String Handling

**Decision**: Treat empty string as "use default" with informational log
**Rationale**: Common user mistake to pass empty string; graceful fallback improves UX
**Alternatives Considered**: Error on empty string - rejected as too strict

### 6. DEFAULT_PROMPT_TEMPLATE Export

**Decision**: Add to `__all__` in proposer.py for public import
**Rationale**: Allows users to extend the default rather than replace entirely
**Alternatives Considered**: Keep private - rejected per spec requirement FR-005

## Code Locations

| Component | File | Lines |
|-----------|------|-------|
| EvolutionConfig | src/gepa_adk/domain/models.py | 25-156 |
| evolve() | src/gepa_adk/api.py | 820-1077 |
| evolve_group() | src/gepa_adk/api.py | 395-610 |
| ADKAdapter | src/gepa_adk/adapters/adk_adapter.py | 84-218 |
| MultiAgentAdapter | src/gepa_adk/adapters/multi_agent.py | 100-250 |
| AsyncReflectiveMutationProposer | src/gepa_adk/engine/proposer.py | 398-610 |
| DEFAULT_PROMPT_TEMPLATE | src/gepa_adk/engine/proposer.py | 57-74 |

## Dependencies

This feature depends on:
- #89 (Wire reflection_model config) - MERGED (prerequisite satisfied)

This feature is related to:
- #78 (JSON extraction) - custom prompts can request specific output formats
- #80 (Smart model defaults) - model selection guidance overlaps
