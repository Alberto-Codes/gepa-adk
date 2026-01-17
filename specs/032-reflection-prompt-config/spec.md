# Feature Specification: Reflection Prompt Configuration

**Feature Branch**: `032-reflection-prompt-config`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User description: "gh issue 90"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Custom Reflection Prompt Configuration (Priority: P1)

As a gepa-adk user, I want to customize the reflection/mutation prompt via `EvolutionConfig.reflection_prompt`, so that I can tailor the prompt to my specific use case, model capabilities, and output format requirements.

**Why this priority**: This is the core functionality that enables all other customization scenarios. Without the ability to configure a custom prompt, users cannot adapt the reflection behavior to their specific needs.

**Independent Test**: Can be fully tested by creating an `EvolutionConfig` with a custom `reflection_prompt` value and verifying the proposer uses it during evolution.

**Acceptance Scenarios**:

1. **Given** I create an `EvolutionConfig` with `reflection_prompt="<custom prompt with {current_instruction}>"`, **When** I call `evolve()` or `evolve_sync()`, **Then** the proposer uses my custom prompt template instead of the default.

2. **Given** I create an `EvolutionConfig` without specifying `reflection_prompt`, **When** I call `evolve()`, **Then** the proposer uses the default prompt template and functions normally.

3. **Given** I access the default prompt template programmatically, **When** I extend or modify it, **Then** I can use my modified version as the `reflection_prompt` value.

---

### User Story 2 - Placeholder Validation Warnings (Priority: P2)

As a gepa-adk user, I want the system to warn me when my custom reflection prompt is missing required placeholders, so that I can avoid runtime errors and ensure my prompt functions correctly.

**Why this priority**: Validation prevents common configuration mistakes that would cause silent failures or unexpected behavior, but the core functionality works without it.

**Independent Test**: Can be tested by creating an `EvolutionConfig` with a prompt missing `{current_instruction}` or `{feedback_examples}` and verifying a warning is logged.

**Acceptance Scenarios**:

1. **Given** I create an `EvolutionConfig` with `reflection_prompt` missing the `{current_instruction}` placeholder, **When** the config is validated, **Then** a warning is logged indicating the missing placeholder.

2. **Given** I create an `EvolutionConfig` with `reflection_prompt` missing the `{feedback_examples}` placeholder, **When** the config is validated, **Then** a warning is logged indicating the missing placeholder.

3. **Given** I create an `EvolutionConfig` with `reflection_prompt` containing both required placeholders, **When** the config is validated, **Then** no placeholder warnings are logged.

---

### User Story 3 - Prompt Customization Documentation (Priority: P2)

As a gepa-adk user, I want comprehensive documentation explaining how to create effective reflection prompts, so that I can make informed decisions about prompt customization.

**Why this priority**: Documentation is essential for users to effectively use the feature, tied with validation in importance.

**Independent Test**: Can be verified by reviewing documentation for completeness: placeholder documentation, prompt guidelines, and example prompts.

**Acceptance Scenarios**:

1. **Given** I read the reflection prompt documentation, **When** I look for placeholder information, **Then** I find documentation for `{current_instruction}` and `{feedback_examples}` placeholders including what data they contain.

2. **Given** I read the reflection prompt documentation, **When** I look for prompt design guidance, **Then** I find guidelines on what makes an effective reflection prompt and what the prompt should accomplish.

3. **Given** I read the reflection prompt documentation, **When** I look for examples, **Then** I find example prompts for different use cases (JSON output, minimal/fast, chain-of-thought).

---

### User Story 4 - Model Selection Guidance (Priority: P3)

As a gepa-adk user choosing a reflection model, I want documentation on model selection criteria (token limits, task complexity, cost), so that I can make informed decisions about which model to use for different scenarios.

**Why this priority**: Useful for informed decision-making but not required for basic feature functionality.

**Independent Test**: Can be verified by reviewing documentation for model selection criteria covering token considerations, complexity guidance, and cost tradeoffs.

**Acceptance Scenarios**:

1. **Given** I read the model selection documentation, **When** I look for token budget guidance, **Then** I find information about estimating prompt size and required model context.

2. **Given** I read the model selection documentation, **When** I look for complexity guidance, **Then** I find recommendations for matching model capability to task complexity.

3. **Given** I read the model selection documentation, **When** I look for cost guidance, **Then** I find a comparison of cost vs quality tradeoffs for different model tiers.

---

### Edge Cases

- What happens when user provides an empty string as `reflection_prompt`? System should treat it as "use default" and log a warning.
- What happens when placeholder names have typos (e.g., `{current_instructions}` instead of `{current_instruction}`)? Validation should detect and warn about unrecognized placeholders that look similar to required ones.
- How does the system handle prompts that are extremely long (approaching model context limits)? The system should not fail, but documentation should guide users on prompt size considerations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional `reflection_prompt` configuration field in `EvolutionConfig`.
- **FR-002**: System MUST use the default prompt template when `reflection_prompt` is not specified or is `None`.
- **FR-003**: System MUST pass the configured `reflection_prompt` through the API layer to the proposer component.
- **FR-004**: System MUST validate configured prompts and log warnings when required placeholders (`{current_instruction}`, `{feedback_examples}`) are missing.
- **FR-005**: System MUST make the default prompt template (`DEFAULT_PROMPT_TEMPLATE`) importable from the proposer module so users can reference or extend it.
- **FR-006**: System MUST treat empty string `reflection_prompt` values as "use default" and log an informational message.
- **FR-007**: Documentation MUST explain all available placeholders and their contents.
- **FR-008**: Documentation MUST provide guidance on creating effective reflection prompts.
- **FR-009**: Documentation MUST include example prompts for common use cases.
- **FR-010**: Documentation MUST include model selection guidance covering token limits, complexity, and cost considerations.

### Key Entities

- **EvolutionConfig**: The configuration object for evolution runs. Gains a new optional `reflection_prompt` field.
- **Reflection Prompt**: A text template containing placeholders that gets populated with runtime data and sent to the reflection model.
- **Placeholder**: A token within the prompt template (e.g., `{current_instruction}`) that gets replaced with actual values at runtime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully configure and use a custom reflection prompt in a single evolution run.
- **SC-002**: 100% of prompts missing required placeholders generate visible warnings in the log output.
- **SC-003**: Documentation covers all three documentation areas: placeholders, prompt design, and examples.
- **SC-004**: Users can import `DEFAULT_PROMPT_TEMPLATE` from the proposer module without errors.
- **SC-005**: Model selection guidance covers token budget, complexity, and cost considerations for at least 3 model categories (local, cloud-cheap, cloud-premium).

## Assumptions

- Users have basic familiarity with prompt engineering concepts.
- The existing `prompt_template` parameter in `AsyncReflectiveMutationProposer` is functioning correctly and can be wired through.
- Warning logs are visible to users in standard logging configurations.
- Documentation will be added to the existing `docs/` directory structure.
