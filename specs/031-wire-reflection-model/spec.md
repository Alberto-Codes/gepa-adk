# Feature Specification: Wire Reflection Model Config to Proposer

**Feature Branch**: `031-wire-reflection-model`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User description: "Wire reflection_model config to proposer - Pass EvolutionConfig.reflection_model through the adapter chain to AsyncReflectiveMutationProposer so users can configure which LLM model is used for reflection/mutation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Custom Reflection Model (Priority: P1)

As a gepa-adk user, I want to specify which LLM model is used for reflection/mutation via `EvolutionConfig.reflection_model`, so that I can use different models (Gemini, GPT, Claude, Ollama variants) based on my needs and available API keys.

**Why this priority**: This is the core value proposition of the feature. Without this, users cannot customize which model performs reflection operations, forcing them to use a hardcoded default that may not match their environment or preferences.

**Independent Test**: Can be fully tested by creating an `EvolutionConfig` with a custom `reflection_model` value, running evolution, and verifying the proposer uses that model for LLM calls.

**Acceptance Scenarios**:

1. **Given** I create `EvolutionConfig` with `reflection_model="gemini/gemini-2.0-flash"`, **When** I call `evolve()` or `evolve_sync()`, **Then** the proposer uses `"gemini/gemini-2.0-flash"` for all reflection LLM calls.

2. **Given** I create `EvolutionConfig` with `reflection_model="ollama_chat/llama3:8b"`, **When** I call `evolve()` or `evolve_sync()`, **Then** the proposer uses `"ollama_chat/llama3:8b"` for all reflection LLM calls.

3. **Given** I create `EvolutionConfig` with a valid `reflection_model`, **When** evolution runs and the proposer initializes, **Then** I can verify through logs or inspection that the configured model is being used.

---

### User Story 2 - Default Reflection Model Behavior (Priority: P2)

As a gepa-adk user, I want the default reflection model to work without requiring explicit configuration, so that I can get started quickly without needing to specify every parameter.

**Why this priority**: Sensible defaults enable quick onboarding and reduce configuration burden for users who don't have specific model preferences.

**Independent Test**: Can be fully tested by creating an `EvolutionConfig` without specifying `reflection_model` and verifying the proposer uses the documented default model.

**Acceptance Scenarios**:

1. **Given** I create `EvolutionConfig` without specifying `reflection_model`, **When** I call `evolve()` or `evolve_sync()`, **Then** the proposer uses the default model (the value specified in `EvolutionConfig.reflection_model` default).

2. **Given** I use the default `reflection_model`, **When** I inspect logs or proposer state, **Then** the default model value is visible and matches documentation.

---

### User Story 3 - Transparency Through Logging (Priority: P3)

As a gepa-adk developer debugging evolution runs, I want the chosen reflection model to be logged when the proposer initializes, so that I can verify which model is being used without inspecting code.

**Why this priority**: Logging is essential for debugging and operational transparency, but the feature functions correctly without it. It enhances usability rather than enabling core functionality.

**Independent Test**: Can be fully tested by running evolution and checking that an INFO-level log message shows the reflection model being used.

**Acceptance Scenarios**:

1. **Given** I run evolution with any `reflection_model` setting, **When** the proposer is initialized, **Then** an INFO-level log message displays the chosen model.

2. **Given** I run evolution with a custom `reflection_model`, **When** I review logs, **Then** I can identify which model was configured without ambiguity.

---

### Edge Cases

- What happens when `reflection_model` is set to an invalid/unsupported model string?
  - The proposer passes the string to LiteLLM as-is; validation happens at the LiteLLM layer when the first call is made. Invalid models raise an error from LiteLLM, not from gepa-adk.

- What happens when `reflection_model` is set to an empty string?
  - `EvolutionConfig` already validates this and raises `ConfigurationError` with message "reflection_model must be a non-empty string".

- How does the system handle when the configured model is unavailable at runtime (e.g., API key missing)?
  - The error surfaces during the first LLM call from the proposer. This is expected LiteLLM behavior and propagates naturally without special handling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST pass `EvolutionConfig.reflection_model` value through the adapter chain to the `AsyncReflectiveMutationProposer` constructor.

- **FR-002**: System MUST use the configured `reflection_model` for all reflection/mutation LLM calls during evolution.

- **FR-003**: System MUST log the chosen reflection model at INFO level when the proposer is initialized.

- **FR-004**: System MUST use a consistent default value for `reflection_model` across all code paths (config, proposer, adapters).

- **FR-005**: System MUST support both single-agent (`ADKAdapter`) and multi-agent (`MultiAgentAdapter`) evolution paths with the same `reflection_model` configuration behavior.

### Key Entities

- **EvolutionConfig**: Configuration object containing `reflection_model` parameter that users set to control which LLM model is used for reflection operations.

- **AsyncReflectiveMutationProposer**: The component that performs reflection/mutation operations using an LLM. Receives the `reflection_model` via its `model` constructor parameter.

- **ADKAdapter / MultiAgentAdapter**: Adapter components that bridge the public API to the engine. Responsible for passing `reflection_model` from config to proposer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can override the reflection model via `EvolutionConfig.reflection_model` and verify the configured model is used in 100% of reflection calls.

- **SC-002**: Default behavior works without explicit configuration - users can run evolution without specifying `reflection_model` and evolution completes successfully.

- **SC-003**: Reflection model choice is visible in logs - developers can identify which model is being used within the first 10 lines of evolution log output.

- **SC-004**: Configuration flows correctly through both adapter paths - single-agent and multi-agent evolution both respect the `reflection_model` setting.

## Assumptions

- The `reflection_model` string format follows LiteLLM conventions (e.g., `"provider/model-name"` or `"model-name"`).
- Users are responsible for ensuring the configured model is accessible (valid API keys, network connectivity, etc.).
- The proposer's `model` parameter already accepts and uses the model string correctly; this feature is purely about wiring the config value through.
- Changing the default in `EvolutionConfig` from `"gemini-2.0-flash"` to `"ollama/gpt-oss:20b"` is acceptable for backward compatibility with current runtime behavior.

## Out of Scope

- Smart model defaults or auto-detection (covered by issue #80)
- Model validation beyond empty string check
- Model availability checking at configuration time
- Performance benchmarking of different models
