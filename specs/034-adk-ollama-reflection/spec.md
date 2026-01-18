# Feature Specification: ADK Reflection Agents

**Feature Branch**: `034-adk-ollama-reflection`
**Created**: 2026-01-17
**Status**: Implemented
**Input**: GitHub Issue #84 - Support ADK reflection agents with Ollama/LiteLLM models

## Summary

Enable users to configure ADK LlmAgents as reflection agents for instruction evolution, providing an alternative to the default LiteLLM-based reflection.

## User Scenarios & Testing

### User Story 1 - ADK Reflection Agent Configuration (Priority: P1)

As a gepa-adk user, I want to configure an ADK LlmAgent as a reflection agent for instruction evolution, so that I can leverage ADK agent patterns consistently throughout the evolution pipeline.

**Acceptance Scenarios**:

1. **Given** I have an ADK LlmAgent configured as a reflection agent, **When** I pass it to `evolve()` as `reflection_agent`, **Then** the evolution loop uses this agent for instruction improvement
2. **Given** my reflection agent uses an Ollama model via LiteLLM, **When** evolution runs, **Then** the agent receives component text and trial data and returns improved instructions
3. **Given** the reflection agent returns text output, **When** extraction occurs, **Then** the `extract_final_output()` utility correctly extracts the instruction text

---

### User Story 2 - Trial Data Structure (Priority: P1)

As a gepa-adk user, I want the reflection agent to receive structured trial data, so that it can analyze performance and provide targeted improvements.

**Acceptance Scenarios**:

1. **Given** evolution has completed evaluation trials, **When** the reflection agent is invoked, **Then** it receives trials with `{feedback, trajectory}` structure
2. **Given** feedback contains critic scores and guidance, **When** passed to reflection, **Then** the agent can access `score`, `feedback_text`, and optional `feedback_guidance`
3. **Given** trajectory contains execution details, **When** passed to reflection, **Then** the agent can access `input`, `output`, and optional `trace`

---

### User Story 3 - Consistent Terminology (Priority: P2)

As a gepa-adk developer, I want consistent terminology across the codebase, so that the API is clear and self-documenting.

**Terminology**:
- **component_text**: The current text content being evolved (instruction, code, etc.)
- **trial**: A single performance record containing feedback and trajectory
- **trials**: Collection of trial records for reflection analysis
- **feedback**: Critic evaluation containing score, feedback_text, feedback_guidance, feedback_dimensions
- **trajectory**: The journey from input to output, containing input, output, and optional trace

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST support ADK LlmAgent as `reflection_agent` parameter in `evolve()`
- **FR-002**: System MUST pass component_text and trials data to the reflection agent
- **FR-003**: System MUST use `extract_final_output()` utility to extract text from ADK events
- **FR-004**: System MUST structure trials with `{feedback, trajectory}` format
- **FR-005**: Trajectory MUST contain `input`, `output`, and optional `trace`
- **FR-006**: Trace SHOULD include `tool_calls`, `tokens`, `error` when available

### Key Entities

- **Reflection Agent**: An ADK LlmAgent configured to propose improved component text
- **Component Text**: The current text being evolved (instruction, code block, etc.)
- **Trial**: A performance record with feedback and trajectory
- **Feedback**: Critic evaluation with score and textual feedback
- **Trajectory**: Execution journey with input, output, and optional trace

## Success Criteria

- **SC-001**: ADK reflection agents work with any LiteLLM-supported model
- **SC-002**: Trial data structure is consistent and well-documented
- **SC-003**: Example demonstrates ADK reflection agent usage with Ollama
- **SC-004**: All terminology is consistent across code, docs, and examples

## Implementation Notes

The implementation sends data directly in the user message rather than relying on ADK session state substitution:

```python
user_message = f"""## Component Text to Improve
{component_text}

## Trials
{json.dumps(trials, indent=2)}

Propose an improved version..."""
```

This approach works reliably with all models and avoids complexity around session state templating.
