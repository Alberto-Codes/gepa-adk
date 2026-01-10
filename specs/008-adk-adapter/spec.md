# Feature Specification: ADKAdapter (AsyncGEPAAdapter for ADK)

**Feature Branch**: `008-adk-adapter`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: User description: "Implement ADKAdapter (AsyncGEPAAdapter for ADK) - An ADK-native adapter that allows evolving Google ADK agents with full session and event support. The adapter should execute agents with instruction overrides, capture ADK events and traces, and build reflective datasets for training."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evaluate Agent with Instruction Override (Priority: P1)

As a gepa-adk user, I want to evaluate a Google ADK agent with a candidate instruction, so that I can test how different instructions affect agent performance without modifying the original agent configuration.

**Why this priority**: This is the core functionality that enables agent evolution. Without the ability to evaluate agents with different instructions, no optimization can occur. This is the minimum viable product for the adapter.

**Independent Test**: Can be fully tested by creating an ADK agent, calling `evaluate()` with a candidate that contains an instruction override, and verifying the agent executes with the new instruction and returns scored results.

**Acceptance Scenarios**:

1. **Given** an ADK LlmAgent and a candidate with an instruction component, **When** I call `evaluate()` with a batch of input examples, **Then** the agent executes using the candidate's instruction instead of its original instruction.

2. **Given** an ADK LlmAgent and evaluation batch, **When** I call `evaluate()`, **Then** the adapter returns an EvaluationBatch containing output text, scores, and optional trajectories for each input example.

3. **Given** an ADK LlmAgent and a candidate without an instruction component, **When** I call `evaluate()`, **Then** the adapter uses the agent's original instruction unchanged.

4. **Given** an ADK LlmAgent and a scorer implementation, **When** I call `evaluate()` with expected outputs in the batch, **Then** each output is scored against the expected value using the configured scorer.

---

### User Story 2 - Capture Execution Traces (Priority: P2)

As a gepa-adk developer, I want to capture detailed traces during agent evaluation, so that I can analyze tool calls, state changes, and token usage for debugging and optimization.

**Why this priority**: Trace capture enables debugging and detailed analysis of agent behavior. While not required for basic evaluation, it provides valuable insights for understanding why certain instructions perform better than others.

**Independent Test**: Can be fully tested by calling `evaluate()` with `capture_traces=True` and verifying the returned trajectories contain tool call information, state deltas, and token usage metrics.

**Acceptance Scenarios**:

1. **Given** `capture_traces=True`, **When** I call `evaluate()`, **Then** the returned trajectories include a record of all tool calls made by the agent during execution.

2. **Given** `capture_traces=True`, **When** I call `evaluate()`, **Then** the returned trajectories include state deltas showing how the session state changed during execution.

3. **Given** `capture_traces=True`, **When** I call `evaluate()`, **Then** the returned trajectories include token usage statistics for the evaluation.

4. **Given** `capture_traces=False` (default), **When** I call `evaluate()`, **Then** trajectories are minimal or empty to optimize performance.

---

### User Story 3 - Build Reflective Dataset (Priority: P2)

As a gepa-adk user, I want to create a reflective dataset from evaluation results, so that I can use the scored examples to generate improved instruction candidates.

**Why this priority**: Reflective datasets are essential for the GEPA algorithm to propose improvements. This completes the evaluation-reflection cycle that enables iterative agent optimization.

**Independent Test**: Can be fully tested by running an evaluation, calling `make_reflective_dataset()` with the results, and verifying the returned structure contains properly formatted examples for reflection.

**Acceptance Scenarios**:

1. **Given** an EvaluationBatch with scores and feedback, **When** I call `make_reflective_dataset()`, **Then** it returns structured data mapping component names to sequences of reflection examples.

2. **Given** an EvaluationBatch, **When** I call `make_reflective_dataset()` specifying components to update, **Then** only those components are included in the reflective dataset.

3. **Given** high-scoring and low-scoring evaluation results, **When** I call `make_reflective_dataset()`, **Then** the reflection examples include both successful and unsuccessful cases for balanced learning.

---

### User Story 4 - Session Management Integration (Priority: P3)

As a gepa-adk user, I want the adapter to manage ADK sessions properly, so that evaluation runs are isolated and don't interfere with each other.

**Why this priority**: Proper session management ensures evaluation runs are independent and reproducible. While not required for basic functionality, it's essential for production use cases.

**Independent Test**: Can be fully tested by running multiple concurrent evaluations and verifying each uses its own isolated session state.

**Acceptance Scenarios**:

1. **Given** a SessionService is provided, **When** I call `evaluate()`, **Then** the adapter uses the session service to manage agent sessions.

2. **Given** no SessionService is provided, **When** I create an ADKAdapter, **Then** it uses a default in-memory session service.

3. **Given** a batch evaluation, **When** evaluating multiple examples, **Then** each example evaluation starts with a fresh session state (no cross-contamination).

---

### Edge Cases

- **Empty batch**: What happens when `evaluate()` is called with an empty batch? Should return an empty EvaluationBatch.
- **Agent execution failure**: How does the system handle an agent that raises an exception during execution? Should capture the error, assign a score of 0.0, and include error details in metadata.
- **Missing expected output**: What happens when scoring an example without an expected output? Scorer should handle `expected=None` per Scorer protocol.
- **Instruction component missing from candidate**: When `candidate.components` doesn't contain "instruction", use agent's original instruction.
- **Session service unavailable**: If the session service fails, should raise a clear error indicating the session issue.
- **Large batch evaluation**: How does the system handle very large batches? Should process efficiently without memory issues.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: ADKAdapter MUST implement the AsyncGEPAAdapter protocol from `gepa_adk.ports.adapter`.
- **FR-002**: ADKAdapter MUST accept an ADK LlmAgent, a Scorer, and an optional SessionService during initialization.
- **FR-003**: The `evaluate()` method MUST accept a batch of data instances, a Candidate, and an optional `capture_traces` flag.
- **FR-004**: The `evaluate()` method MUST override the agent's instruction with `candidate.components["instruction"]` when that key is present.
- **FR-005**: The `evaluate()` method MUST restore the agent's original instruction after evaluation completes.
- **FR-006**: The `evaluate()` method MUST execute the agent using the ADK Runner pattern for each input in the batch.
- **FR-007**: The `evaluate()` method MUST score each output using the configured Scorer and include scores in the result.
- **FR-008**: The `evaluate()` method MUST return an EvaluationBatch containing outputs, scores, and trajectories.
- **FR-009**: The `make_reflective_dataset()` method MUST create reflection data from evaluation results.
- **FR-010**: The `make_reflective_dataset()` method MUST accept a list of component names to update.
- **FR-011**: When `capture_traces=True`, trajectories MUST include tool calls, state deltas, and token usage.
- **FR-012**: All adapter methods MUST be async (coroutine functions).
- **FR-013**: ADKAdapter MUST handle agent execution errors gracefully by assigning a score of 0.0 and capturing error details.
- **FR-014**: ADKAdapter MUST ensure session isolation between batch examples to prevent state contamination.

### Key Entities

- **ADKAdapter**: The concrete implementation of AsyncGEPAAdapter for Google ADK agents. Bridges between GEPA evaluation patterns and ADK's agent/runner architecture.
- **EvaluationBatch**: Container returned by `evaluate()` holding trajectories, outputs, and scores for all evaluated examples. Defined in AsyncGEPAAdapter protocol.
- **Trajectory**: Record of agent execution including tool calls, state changes, and metrics. Populated when `capture_traces=True`.
- **Candidate**: Input containing the instruction and other components to test. Uses `candidate.components["instruction"]` for agent instruction override.
- **Scorer**: Protocol for scoring agent outputs. ADKAdapter uses this to evaluate each output against expected results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can evaluate an ADK agent with a candidate instruction and receive scored results within reasonable time bounds for the agent's complexity.
- **SC-002**: 100% of AsyncGEPAAdapter protocol methods are implemented and pass protocol compliance tests.
- **SC-003**: Trace capture provides complete visibility into agent execution when enabled, including all tool calls and state changes.
- **SC-004**: Reflective datasets generated by `make_reflective_dataset()` are compatible with the MutationProposer for generating improved candidates.
- **SC-005**: Multiple concurrent evaluations complete without session state interference.
- **SC-006**: Agent execution errors are gracefully handled with clear error information available in results.

## Dependencies

- **Depends on**: 
  - Issue #4 (AsyncGEPAAdapter protocol) - Defines the protocol this adapter implements
  - Issue #5 (Scorer protocol) - Defines the scoring interface used by the adapter
  - Domain models from 002-domain-models (`Candidate`, `Score`)
- **Blocks**: Issue #6 (AsyncGEPAEngine) - Engine needs at least one adapter implementation

## Assumptions

- Google ADK is installed and provides the `google.adk.agents.LlmAgent` and `google.adk.runners.Runner` classes.
- ADK Runner supports async execution via `run_async()` method.
- ADK provides event capture mechanisms for traces (tool calls, state deltas, token usage).
- The LlmAgent instruction can be modified at runtime before execution.
- Session management follows ADK's SessionService patterns.
- Batch evaluation processes examples sequentially within the async context (parallel batch processing is a future enhancement).
