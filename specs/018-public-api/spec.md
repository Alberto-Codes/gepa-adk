# Feature Specification: Public API (evolve, evolve_sync)

**Feature Branch**: `018-public-api`  
**Created**: 2026-01-12  
**Status**: Draft  
**Input**: User description: "Implement public API (evolve, evolve_sync) - A simple public API for evolving ADK agents with one line of code. As a gepa-adk user, I want a simple public API so that I can evolve agents with one line of code."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simple Async Evolution (Priority: P1)

As a developer building async applications, I want to evolve my ADK agent's instruction using a single async function call, so that I can integrate agent evolution into my async workflow without complex setup.

**Why this priority**: This is the core functionality that enables the primary use case - evolving agents programmatically. Without this, the library provides no value. It's the foundational capability all other features build upon.

**Independent Test**: Can be fully tested by calling `await evolve(agent, trainset)` with a mock agent and sample training data, verifying that an evolution result is returned with the expected structure.

**Acceptance Scenarios**:

1. **Given** an ADK agent and a training dataset, **When** I call `await evolve(agent, trainset)`, **Then** the function returns an EvolutionResult containing the evolved instruction and metrics.
2. **Given** an ADK agent and training data, **When** evolution completes successfully, **Then** the result includes original score, final score, evolved instruction, and iteration history.
3. **Given** an ADK agent and empty training data, **When** I call `await evolve(agent, [])`, **Then** the system handles this gracefully with an appropriate error or default behavior.

---

### User Story 2 - Synchronous Wrapper for Scripts (Priority: P1)

As a developer writing scripts or Jupyter notebooks, I want a synchronous version of the evolve function, so that I can use agent evolution without managing async contexts manually.

**Why this priority**: Equal priority to async because many users work in sync contexts (scripts, notebooks, quick prototypes). This removes the barrier of async complexity for simpler use cases.

**Independent Test**: Can be fully tested by calling `evolve_sync(agent, trainset)` from a regular Python script and verifying it returns the same EvolutionResult as the async version.

**Acceptance Scenarios**:

1. **Given** a non-async context (script or notebook), **When** I call `evolve_sync(agent, trainset)`, **Then** the function runs the async evolution internally and returns the result synchronously.
2. **Given** a sync context with an agent and training data, **When** I call `evolve_sync()`, **Then** it produces identical results to calling `await evolve()` with the same inputs.

---

### User Story 3 - Progressive Configuration Disclosure (Priority: P2)

As a power user needing fine-grained control, I want to override default settings by passing optional configuration parameters, so that I can customize the evolution process without modifying library code.

**Why this priority**: Important for advanced users but not required for basic functionality. The library should work with sensible defaults first, then allow customization.

**Independent Test**: Can be tested by calling evolve with custom config parameters and verifying the custom settings are applied to the evolution process.

**Acceptance Scenarios**:

1. **Given** I need custom evolution settings, **When** I pass a config parameter to evolve(), **Then** the custom configuration overrides the defaults.
2. **Given** I want to use a custom critic agent for scoring, **When** I pass a critic parameter, **Then** the critic agent is used instead of the default mechanical scorer.
3. **Given** I want to use a custom reflection agent, **When** I pass a reflection_agent parameter, **Then** a warning is logged (MVP uses default LiteLLM proposer; full ADK reflection agent support planned for future release).
4. **Given** I need trajectory capture, **When** I pass trajectory_config, **Then** agent execution traces are captured according to my settings.
5. **Given** I need to preserve certain tokens in instructions, **When** I pass state_guard settings, **Then** specified tokens are protected during evolution.

---

### User Story 4 - Validation Dataset Support (Priority: P3)

As a machine learning practitioner, I want to provide a separate validation dataset, so that I can evaluate evolution quality on held-out data and prevent overfitting.

**Why this priority**: Good practice for ML workflows but optional - users can achieve basic evolution without validation data.

**Independent Test**: Can be tested by passing both trainset and valset, then verifying that validation metrics are included in the result.

**Acceptance Scenarios**:

1. **Given** training and validation datasets, **When** I call evolve with both, **Then** the system uses trainset for evolution and evaluates final instruction on valset (valset does not affect iteration decisions in MVP; future: early stopping support).
2. **Given** only a training dataset (no valset), **When** I call evolve, **Then** the system uses training data for both evolution and final evaluation.

---

### Edge Cases

- What happens when the agent is None or invalid?
- How does the system handle an empty training dataset?
- What happens when evolution produces no improvement over the original?
- How does the system handle network/API failures during evolution?
- What happens when the user passes incompatible configuration combinations?
- How does the sync wrapper handle being called from an already-running event loop?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an async `evolve()` function that accepts an ADK agent and training dataset as required parameters.
- **FR-002**: System MUST provide a sync `evolve_sync()` function that wraps the async version for non-async contexts.
- **FR-003**: System MUST return an EvolutionResult containing: original score, final score, evolved instruction, iteration history, and total iterations.
- **FR-004**: System MUST use sensible defaults when optional parameters are not provided (default config, default scorer, default proposer).
- **FR-005**: System MUST allow users to override defaults by passing optional parameters: config, critic, reflection_agent, trajectory_config, state_guard.
- **FR-006**: System MUST support an optional validation dataset (valset) for held-out evaluation.
- **FR-007**: System MUST export the public API functions and related types from the package's main entry point (`__init__.py`).
- **FR-008**: System MUST validate input parameters and provide clear error messages for invalid inputs.
- **FR-009**: The sync wrapper MUST handle cases where it's called from within an existing event loop gracefully.

### Key Entities

- **EvolutionResult**: The output of evolution - contains original score, final score, evolved instruction, iteration history, and total iteration count.
- **EvolutionConfig**: Configuration settings for the evolution process (iterations, thresholds, model settings).
- **TrajectoryConfig**: Settings for capturing agent execution traces during evaluation.
- **StateGuard**: Configuration for preserving specific tokens/patterns in the instruction during evolution. *(Forward-compatible placeholder; full implementation in 015-state-guard-tokens)*
- **Trainset/Valset**: Lists of example dictionaries with "input" and "expected" fields representing training and validation data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can evolve an agent with a single function call (`await evolve(agent, trainset)` or `evolve_sync(agent, trainset)`).
- **SC-002**: The API requires only 2 mandatory parameters (agent and trainset) for basic operation.
- **SC-003**: All optional parameters have sensible defaults that produce reasonable evolution results without user configuration.
- **SC-004**: Evolution results contain all information needed to understand the evolution process (scores, instruction, history).
- **SC-005**: The sync wrapper works correctly in scripts and Jupyter notebooks without async boilerplate.
- **SC-006**: Users can progressively add configuration options without modifying their basic usage pattern.

## Assumptions

- The ADK agent type (`LlmAgent` from `google.adk.agents`) is available and users have it configured.
- Training data follows the format `[{"input": "...", "expected": "..."}]`.
- The underlying components (AsyncGEPAEngine, ADKAdapter, scorers, proposers) exist and are functional.
- Default model configurations are available for LiteLLM-based reflection when no custom agent is provided.
