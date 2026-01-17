# Feature Specification: ADK Reflection Agents with Ollama/LiteLLM Support

**Feature Branch**: `034-adk-ollama-reflection`
**Created**: 2026-01-17
**Status**: Draft
**Input**: GitHub Issue #84 - Support ADK reflection agents with Ollama/LiteLLM models

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Instruction Extraction from ADK Reflection Agents (Priority: P1)

As a gepa-adk user, I want to configure an ADK LlmAgent as a reflection agent for instruction mutation, so that the evolution pipeline extracts clean, usable instructions rather than reasoning text or garbage data.

**Why this priority**: This is the core problem - when using ADK reflection agents with Ollama models, the system extracts reasoning text instead of the actual improved instruction, making the evolved instructions unusable. Without solving this, ADK reflection agents cannot be used at all with non-compliant models.

**Independent Test**: Can be fully tested by configuring an ADK LlmAgent with an Ollama model as a reflection agent, running an evolution cycle, and verifying the extracted instruction is clean and usable (not reasoning text).

**Acceptance Scenarios**:

1. **Given** I have configured an ADK LlmAgent as reflection_agent with an Ollama model via LiteLLM, **When** the evolution loop calls propose_new_texts, **Then** the proposer extracts a clean instruction that is directly usable by the target agent
2. **Given** the reflection agent returns free-form text with reasoning and instructions mixed together, **When** the extraction logic processes the response, **Then** it identifies and extracts only the improved instruction portion, not the reasoning text
3. **Given** the reflection agent response contains text like "We need to infer what issues were in negative feedback...", **When** the extraction logic processes this, **Then** it does NOT extract this reasoning text as the instruction

---

### User Story 2 - Schema-in-Prompt Fallback for Non-Compliant Models (Priority: P2)

As a gepa-adk user, I want the system to automatically inject JSON schema guidance into prompts when my model doesn't support native structured output, so that I can still use custom ADK reflection agents with models like Ollama that don't enforce output schemas.

**Why this priority**: This provides a robust fallback mechanism when native structured output isn't supported, enabling a wider range of models to work with ADK reflection agents.

**Independent Test**: Can be tested by configuring an ADK reflection agent with output_schema on a model that doesn't support native JSON mode, running evolution, and verifying the prompt contains schema guidance and the response is correctly extracted.

**Acceptance Scenarios**:

1. **Given** I have an ADK reflection agent with output_schema configured, **And** the underlying model does not support native structured output, **When** the reflection agent is invoked, **Then** the system includes the schema as guidance in the prompt
2. **Given** the schema specifies an "improved_instruction" field, **When** the model returns a response following the schema guidance, **Then** the system extracts the value from that field
3. **Given** the model returns a response that partially follows the schema guidance, **When** extraction is attempted, **Then** the system uses fallback patterns to extract the instruction field

---

### User Story 3 - Consistent ADK Patterns Throughout Evolution Pipeline (Priority: P3)

As a gepa-adk user, I want to use ADK agent patterns consistently throughout the evolution pipeline including reflection, so that I'm not forced to fall back to direct LiteLLM calls when using certain models.

**Why this priority**: This aligns with the project's thesis of ADK + GEPA interoperability. Users should be able to leverage ADK patterns consistently, not just for some parts of the pipeline.

**Independent Test**: Can be tested by running a complete evolution cycle with an ADK reflection agent using Ollama, verifying no fallback to direct LiteLLM is required, and confirming all agents use ADK patterns.

**Acceptance Scenarios**:

1. **Given** I configure an ADK LlmAgent as my reflection_agent, **When** the evolution pipeline runs, **Then** the reflection uses ADK patterns without falling back to direct LiteLLM calls
2. **Given** I want consistent logging and observability across all agents, **When** using ADK reflection agents, **Then** the logs show ADK-style agent execution patterns

---

### Edge Cases

- What happens when the reflection agent returns an empty response?
- How does the system handle when the model completely ignores schema guidance and returns unstructured prose?
- What happens when the instruction field exists but contains empty or whitespace-only content?
- How does the system handle very long responses where the instruction is buried deep in reasoning text?
- What happens when multiple potential instruction candidates are found in the response?
- How does the system behave when the model returns valid JSON but with unexpected field names?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract clean, usable instructions from ADK reflection agent responses regardless of whether the model supports native structured output
- **FR-002**: System MUST NOT extract reasoning text (e.g., "We need to infer...", "Let me think about...") as the improved instruction
- **FR-003**: System MUST include JSON schema guidance in the prompt when the reflection agent has output_schema configured and the model doesn't support native structured output
- **FR-004**: System MUST support extraction of instruction content from JSON-formatted responses that follow the schema guidance
- **FR-005**: System MUST provide fallback extraction patterns when the model response doesn't perfectly match the expected schema format
- **FR-006**: System MUST log extraction method used (schema-based, regex pattern, fallback) for debugging and observability
- **FR-007**: System MUST gracefully handle empty or invalid responses by returning an appropriate error or empty result rather than crashing
- **FR-008**: System MUST prioritize instruction extraction in this order: (1) structured JSON field, (2) code block content, (3) quoted content, (4) paragraph analysis with reasoning filtering

### Key Entities

- **Reflection Agent**: An ADK LlmAgent configured to mutate/improve instructions based on feedback. May have output_schema defined for structured responses.
- **Model Response**: The raw text returned by the LLM, which may contain structured JSON, semi-structured text, or free-form prose with mixed reasoning and instructions.
- **Extracted Instruction**: The clean, usable instruction text extracted from a model response, suitable for use by the target agent.
- **Schema Guidance**: JSON schema information injected into prompts to guide models that don't support native structured output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ADK reflection agents with Ollama models produce clean, usable instructions in 95% or more of evolution cycles
- **SC-002**: Extracted instructions contain zero reasoning preambles (e.g., "We need to...", "Let me think...") when reasoning and instruction content are mixed in responses
- **SC-003**: Users can configure ADK LlmAgents as reflection agents without requiring any workarounds or fallback to direct LiteLLM calls
- **SC-004**: Extraction success rate for models without native structured output is comparable to models with native support (within 10% accuracy)
- **SC-005**: All extraction attempts are logged with the method used, enabling users to debug and tune their reflection agent configurations

## Assumptions

- Models that don't support native structured output will generally follow schema guidance when it's included in the prompt, producing semi-structured responses that can be parsed
- The instruction content in reflection responses is typically distinguishable from reasoning text through patterns like JSON fields, code blocks, quoted sections, or imperative language
- Users who configure ADK reflection agents with output_schema expect the system to handle non-compliant models gracefully rather than failing silently
- The existing extraction patterns in proposer.py can be enhanced to filter reasoning text without requiring a complete rewrite
- LiteLLM's model capability detection (or manual configuration) can indicate whether a model supports native structured output
