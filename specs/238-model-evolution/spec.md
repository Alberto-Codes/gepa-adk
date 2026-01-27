# Feature Specification: Model Evolution Support

**Feature Branch**: `238-model-evolution`
**Created**: 2026-01-27
**Status**: Draft
**GitHub Issue**: [#238](https://github.com/Alberto-Codes/gepa-adk/issues/238)
**Input**: User description: "Add model evolution support - allow evolving the model name used by agents, preserving wrapper configurations"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Opt-in Model Evolution (Priority: P1)

As a gepa-adk user, I want to evolve the model used by my agents by providing a list of allowed model choices, so that I can discover which model performs best for my specific task through the same evolutionary optimization process used for instructions and schemas.

**Why this priority**: This is the core functionality - without opt-in model evolution with explicit choices, the feature has no value. Users must be able to specify which models to try.

**Independent Test**: Can be fully tested by calling `evolve()` with a `model_choices` parameter containing 2+ models and verifying that the evolution process considers different models and returns the best-performing one.

**Acceptance Scenarios**:

1. **Given** an agent with a model and a list of allowed model choices, **When** I call the evolution function with those choices, **Then** the system explores different models from the list and returns the best-performing configuration.

2. **Given** an agent with a model, **When** I call the evolution function without specifying model choices, **Then** the model is NOT evolved (opt-in behavior preserved).

3. **Given** a list of model choices that doesn't include my current model, **When** the evolution process starts, **Then** my current model is automatically added to the allowed list as a baseline.

---

### User Story 2 - Wrapper Preservation (Priority: P2)

As a user with custom model wrappers (e.g., LiteLLM with custom headers, authentication, or other configuration), I want model evolution to preserve my wrapper configuration while only changing the model name, so that I don't lose my custom integration setup during evolution.

**Why this priority**: Many production users have custom wrappers with authentication, headers, or other configuration. Breaking this would make model evolution unusable in real deployments.

**Independent Test**: Can be tested by creating an agent with a wrapped model object containing custom configuration, running evolution, and verifying the wrapper and its configuration remain intact while only the model name changes.

**Acceptance Scenarios**:

1. **Given** an agent using a wrapped model with custom configuration (headers, auth, etc.), **When** model evolution changes the model, **Then** only the model name attribute is modified and all wrapper configuration is preserved.

2. **Given** an agent using a plain string model identifier, **When** model evolution changes the model, **Then** the string is directly replaced with the new model name.

---

### User Story 3 - Invalid Model Rejection (Priority: P3)

As a user, I want the system to reject model proposals that aren't in my allowed list, so that evolution stays within my specified constraints and doesn't try models I haven't approved.

**Why this priority**: This is a safety/constraint feature that ensures the system respects user-defined boundaries. Important but builds on the core functionality.

**Independent Test**: Can be tested by configuring a restricted model list and verifying that proposals outside this list are rejected and the original model is retained.

**Acceptance Scenarios**:

1. **Given** a configured list of allowed models, **When** the reflection system proposes a model not in the list, **Then** the proposal is rejected and the original model is preserved.

2. **Given** a configured list of allowed models, **When** the reflection system proposes a model from the list, **Then** the proposal is accepted and applied for evaluation.

---

### Edge Cases

- What happens when the model choices list is empty? System should treat this as opt-out (no model evolution).
- What happens when model choices contains only one model? System should skip model evolution since there are no alternatives.
- How does the system handle an agent with no model set (inherits from parent/default)? System should serialize the resolved model name and include it in allowed choices.
- What happens if the wrapper object doesn't have a `.model` attribute? System should log a warning and skip model evolution for that agent.
- How does the system behave when model evolution is combined with other component evolution (instruction, schema)? All components should be evolved independently per the existing multi-component architecture.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST only evolve the model when a non-empty list of model choices is explicitly provided (opt-in behavior).
- **FR-002**: System MUST automatically include the agent's current model in the allowed choices list if not already present.
- **FR-003**: System MUST reject model proposals that are not in the allowed choices list and preserve the original model.
- **FR-004**: System MUST preserve all wrapper configuration (headers, authentication, custom settings) when evolving wrapped model objects, modifying only the model name.
- **FR-005**: System MUST support both string model identifiers and wrapped model objects. Wrapped models are detected via duck-typing: any object with a `.model` attribute that is a string. If `.model` exists but is not a string, log a warning and skip model evolution for that agent.
- **FR-006**: System MUST provide the allowed model choices to the reflection system so it can make informed proposals.
- **FR-007**: System MUST restore the original model after evaluation (same as other evolved components).
- **FR-008**: System MUST be able to evolve the model component independently or alongside other components (instruction, schema, config).

### Key Entities

- **ModelConstraints**: Represents the allowed model choices for evolution. Contains a collection of valid model name strings.
- **ModelHandler**: Component handler responsible for serializing, applying, and restoring model values during evolution. Must handle both string and wrapped model types.
- **Model Reflection Agent**: Specialized agent that proposes model changes based on trial results, constrained to the allowed choices.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully evolve agent models by providing a list of 2 or more model choices.
- **SC-002**: Model evolution respects the opt-in constraint - agents evolved without model_choices parameter retain their original model 100% of the time.
- **SC-003**: Wrapper configurations (headers, auth, custom settings) are preserved in 100% of model evolution operations on wrapped model objects.
- **SC-004**: Invalid model proposals (outside allowed list) are rejected and logged, with the original model preserved.
- **SC-005**: Model evolution integrates seamlessly with existing component evolution, allowing users to evolve model alongside instruction, schema, or config in a single evolution run.
- **SC-006**: The feature adds no new external dependencies to the project.

## Assumptions

- Users provide valid, accessible model names in their choices list (the system doesn't validate model accessibility at configuration time).
- All wrapped model objects follow the pattern of having a `.model` attribute containing the model name string.
- The reflection system can make meaningful model recommendations based on trial performance data.
- Model switching mid-evolution doesn't require session/state reset (handled by existing evaluation architecture).
